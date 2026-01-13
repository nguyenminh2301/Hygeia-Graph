"""Intervention Simulation (Associational Propagation) for Hygeia-Graph.

This module implements a heuristic propagation simulation based on the estimated
signed adjacency matrix from MGM. It is NOT causal inference.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def build_signed_adjacency(
    results_json: Dict[str, Any], *, threshold: float = 0.0, top_edges: Optional[int] = None
) -> Tuple[List[str], np.ndarray]:
    """Build signed adjacency matrix from MGM results.

    Args:
        results_json: Validated MGM results.
        threshold: Absolute weight threshold (edges below are 0).
        top_edges: Keep only top N edges by absolute weight.

    Returns:
        tuple (node_ids, adjacency_matrix_NxN)
    """
    nodes = results_json.get("nodes", [])
    # Use alphabetical order or original order?
    # Constraint: "results_json['nodes'] order by node_id (alphabetical) OR stable order"
    # results_json usually preserves input order. Let's trust results_json["nodes"] list order.
    # But ensure robustness by strictly defining index.

    node_ids = [n["id"] for n in nodes]
    node_idx = {nid: i for i, nid in enumerate(node_ids)}
    n = len(node_ids)

    A = np.zeros((n, n), dtype=float)

    edges = results_json.get("edges", [])

    # Filter
    filtered = []
    for edge in edges:
        w = edge.get("weight", 0.0)
        if abs(w) >= threshold:
            filtered.append(edge)

    # Sort for top_edges cap
    if top_edges is not None and top_edges > 0:
        filtered.sort(key=lambda e: (-abs(e.get("weight", 0.0)), e["source"], e["target"]))
        filtered = filtered[:top_edges]

    # Populate Matrix
    for edge in filtered:
        u, v = edge["source"], edge["target"]
        w = edge.get("weight", 0.0)

        if u in node_idx and v in node_idx:
            i, j = node_idx[u], node_idx[v]
            A[i, j] = w
            A[j, i] = w  # Undirected / symmetric

    return node_ids, A


def normalize_adjacency(A: np.ndarray, method: str = "max_abs") -> np.ndarray:
    """Normalize adjacency matrix to prevent explosion."""
    if method == "max_abs":
        max_val = np.abs(A).max()
        if max_val > 0:
            return A / max_val
    return A


def simulate_intervention(
    node_ids: List[str],
    A_signed: np.ndarray,
    *,
    intervene_node: str,
    delta: float,
    steps: int = 1,
    damping: float = 0.6,
    normalize_weights: bool = True,
) -> Dict[str, Any]:
    """Compute propagation effects.

    Args:
        node_ids: List of node IDs corresponding to A rows/cols.
        A_signed: Signed weighted adjacency matrix.
        intervene_node: ID of node to perturb.
        delta: Magnitude of perturbation.
        steps: Number of propagation steps (1 = neighbors only).
        damping: Damping factor per step (0 < d <= 1).
        normalize_weights: Whether to normalize A before prop.

    Returns:
        Dict with simulation metadata and 'effects' map.
    """
    if intervene_node not in node_ids:
        raise ValueError(f"Node {intervene_node} not found in graph.")

    target_idx = node_ids.index(intervene_node)

    A = A_signed.copy()
    if normalize_weights:
        A = normalize_adjacency(A)

    n = len(node_ids)

    # Propagation:
    # Effect at step k = delta * (damping^(k-1)) * (A^k)[target, :]
    # A^k means matrix power?
    # Actually prompt says: "sum_{k=1..steps} (damping^(k-1)) * (A^k)[i, :]"
    # It implies paths of length k.
    # Note: A is symmetric (undirected).

    # Iterative computation:
    # State vector x. x_0 = one-hot (only target=delta)? NO.
    # We want "impact ON other nodes".
    # Interpretation: Change in X propagates to neighbors Y ~ w_xy * delta.
    # Then Y propagates to Z ~ w_yz * (w_xy * delta).
    # This is effectively matrix multiplication.

    current_vec = np.zeros(n, dtype=float)
    current_vec[target_idx] = delta

    # Accumulate effects
    # DO NOT count self-effect in result

    # Step 1: Immediate neighbors
    # vec_1 = A @ vec_0

    # Represents effect arriving at step 0 (intervention)
    current_vec_copy = current_vec.copy()
    # Actually, the prompt formula is sum of (A^k)[i,:].
    # So we want row i of A^1, A^2...

    # Or vector-matrix mult: v_0 @ A, v_0 @ A^2 ...
    # Since A is symmetric, row i == col i.

    # Let's use vector iteration for efficiency
    vec = np.zeros(n, dtype=float)
    vec[target_idx] = 1.0  # unit perturbation

    accumulated = np.zeros(n, dtype=float)

    curr = vec
    for k in range(1, steps + 1):
        # Next step vector
        next_v = A @ curr

        # Log: effect at distance k
        # Apply damping: damping^(k-1)
        # k=1: damping^0 = 1. Effect = delta * A[i]
        scale = delta * (damping ** (k - 1))

        accumulated += next_v * scale

        curr = next_v

    # Zero out self
    accumulated[target_idx] = 0.0

    effects = {node_ids[i]: float(accumulated[i]) for i in range(n) if i != target_idx}

    return {
        "intervene_node": intervene_node,
        "delta": delta,
        "steps": steps,
        "damping": damping,
        "normalize_weights": normalize_weights,
        "effects": effects,
    }


def build_intervention_table(
    df: Optional[pd.DataFrame],
    node_ids: List[str],
    effects: Dict[str, float],
    input_node: str,  # Required to know what caused it
    node_map: Optional[Dict[str, Any]] = None,  # Metadata
    top_n: int = 20,
) -> pd.DataFrame:
    """Build standardized result table."""
    rows = []

    # Compute baselines if df available
    baselines = {}
    if df is not None:
        # Check mapping: column name might differ from node_id
        for nid in node_ids:
            col = nid
            if node_map and nid in node_map:
                col = node_map[nid].get("column", nid)

            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                baselines[nid] = {"mean": df[col].mean(), "std": df[col].std(ddof=1)}

    for nid, eff in effects.items():
        if nid == input_node:
            continue

        row = {
            "node_id": nid,
            "effect": eff,
            "abs_effect": abs(eff),
            "direction": "increase" if eff > 0 else "decrease" if eff < 0 else "neutral",
        }

        # Add labels if available
        if node_map and nid in node_map:
            row["label"] = node_map[nid].get("label", nid)
        else:
            row["label"] = nid

        # Add baselines
        b = baselines.get(nid)
        if b:
            row["baseline_mean"] = b["mean"]
            row["baseline_sd"] = b["std"]
            # Percent change? (Effect / Mean * 100)
            # CAUTION: Effect units depend on input.
            # If input was SD units, output is SD units (roughly).
            # So % change isn't direct unless we convert back to raw.
            # Let's leave percent_change NaN or compute if appropriate.
            # If we assume effect is in RAW units (caller handled conversion)
            # But wait, simulate_intervention is unit-agnostic.
            # If user passed SD units, output is SD units.
            # Converting SD effect to % mean: (eff * std) / mean * 100 ?
            # Too many assumptions. Let's skip % change for v1 unless explicitly requested
            # Prompt says "percent_change: if baseline_mean != 0 ... 100*effect/baseline_mean"
            # This implies `effect` matches mean's units.
            # We will populate it, but UI should clarify units.
            if abs(b["mean"]) > 1e-9:
                row["percent_change_raw"] = (eff / b["mean"]) * 100

        rows.append(row)

    df_res = pd.DataFrame(rows)
    if not df_res.empty:
        df_res = df_res.sort_values("abs_effect", ascending=False).head(top_n)
    else:
        # Empty schema
        return pd.DataFrame(columns=["node_id", "effect", "abs_effect", "direction"])

    return df_res


def build_intervention_artifact(
    results_json: Dict[str, Any],
    simulation_output: Dict[str, Any],
    table_df: pd.DataFrame,
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Assemble final JSON artifact."""

    # Top nodes for quick JSON read
    top_nodes = []
    if not table_df.empty:
        # Convert first few rows
        sl = table_df.head(10).to_dict(orient="records")
        for r in sl:
            top_nodes.append({"node": r["node_id"], "effect": r["effect"]})

    return {
        "analysis_id": results_json.get("analysis_id", "unknown"),
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "simulation_version": "0.1.0",
        "disclaimer": [
            "Experimental simulation (associational propagation).",
            "Not causal inference.",
            "Research tool only; not medical advice.",
        ],
        "config": settings,
        "intervention": {
            "node": simulation_output["intervene_node"],
            "delta": simulation_output["delta"],
        },
        "effects": {"by_node": simulation_output["effects"], "top_nodes": top_nodes},
        # "table_preview" requested?
        "table_preview": table_df.head(5).to_dict(orient="records"),
    }
