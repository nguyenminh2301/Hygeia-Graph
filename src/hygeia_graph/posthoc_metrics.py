"""Post-hoc network metrics computation for Hygeia-Graph.

This module implements fast, pure Python metrics derived from MGM results (results.json).
It supports:
- Expected Influence (signed)
- Bridge Centrality (based on domain_group)
- Minimum Spanning Tree (MST) Backbone
- derived_metrics.json artifact generation
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx

# Re-use existing helper if available, otherwise we could redefine.
# Import locally to avoid circular deps if any unique situation arises,
# but usually top-level is fine.
from hygeia_graph.network_metrics import make_nodes_meta


def filter_edges_for_explore(
    results_json: dict[str, Any],
    explore_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    """Filter edges based on exploration config (threshold, top_edges).

    Args:
        results_json: The full MGM results object.
        explore_cfg: Configuration dict containing:
            - threshold: float
            - use_absolute_weights: bool
            - top_edges: int | None

    Returns:
        List of filtered edge dictionaries.
    """
    edges = results_json.get("edges", [])
    threshold = explore_cfg.get("threshold", 0.0)
    use_abs = explore_cfg.get("use_absolute_weights", True)
    top_n = explore_cfg.get("top_edges")

    # 1. Filter by threshold
    filtered = []
    for edge in edges:
        w = edge.get("weight", 0.0)
        metric = abs(w) if use_abs else w
        if metric >= threshold:
            filtered.append(edge)

    # 2. Sort by descending abs(weight) then (source, target)
    # Note: we always sort by abs(weight) for top_cols logic usually,
    # or should we sort by 'metric'?
    # Requirement: "Sort edges by descending abs(edge["weight"]) then (source,target) lexicographic"
    filtered.sort(
        key=lambda e: (
            -abs(e.get("weight", 0.0)),
            e["source"],
            e["target"],
        )
    )

    # 3. Apply top_edges limit
    if top_n is not None and isinstance(top_n, int) and top_n > 0:
        filtered = filtered[:top_n]

    return filtered


def compute_node_strength_abs(edges: list[dict[str, Any]]) -> dict[str, float]:
    """Compute Node Strength (sum of absolute weights) for each node.

    Args:
        edges: List of edges to consider.

    Returns:
        Dict mapping node_id -> strength_abs.
    """
    scores: dict[str, float] = {}

    for edge in edges:
        u, v = edge["source"], edge["target"]
        w = abs(edge.get("weight", 0.0))

        scores[u] = scores.get(u, 0.0) + w
        scores[v] = scores.get(v, 0.0) + w

    return scores


def compute_expected_influence(edges: list[dict[str, Any]]) -> dict[str, float]:
    """Compute Expected Influence (sum of signed weights) for each node.

    Args:
        edges: List of edges to consider.

    Returns:
        Dict mapping node_id -> expected_influence.
    """
    scores: dict[str, float] = {}

    for edge in edges:
        u, v = edge["source"], edge["target"]
        w = edge.get("weight", 0.0)  # Signed weight

        scores[u] = scores.get(u, 0.0) + w
        scores[v] = scores.get(v, 0.0) + w

    return scores


def compute_bridge_metrics(
    edges: list[dict[str, Any]],
    nodes_meta: dict[str, dict[str, Any]],
    *,
    group_key: str = "domain_group",
) -> dict[str, Any]:
    """Compute Bridge Centrality metrics (Strength, EI).

    Args:
        edges: List of filtered edges.
        nodes_meta: Metadata for nodes (must contain group_key).
        group_key: Key in nodes_meta to use for grouping.

    Returns:
        Dict containing enabled status, metrics, and warnings.
    """
    # 1. Analyze groups
    groups_seen = set()
    node_groups = {}
    nodes_with_group = 0
    total_nodes_in_meta = len(nodes_meta)

    for nid, meta in nodes_meta.items():
        g = meta.get(group_key)
        # Treat empty string or None as "no group"
        if g:
            groups_seen.add(g)
            node_groups[nid] = g
            nodes_with_group += 1
        else:
            node_groups[nid] = None

    # Check conditions:
    # - At least 2 distinct non-empty groups
    # - At least 80% of nodes have a group (heuristic from prompt)
    if total_nodes_in_meta > 0:
        coverage = nodes_with_group / total_nodes_in_meta
    else:
        coverage = 0.0

    sufficient_groups = len(groups_seen) >= 2
    sufficient_coverage = coverage >= 0.8

    if not (sufficient_groups and sufficient_coverage):
        warning = (
            f"Bridge metrics disabled: Need >=2 groups (found {len(groups_seen)}) "
            f"and >=80% coverage (found {coverage:.1%})."
        )
        return {
            "enabled": False,
            "group_key": group_key,
            "groups": sorted(list(groups_seen)),
            "warning": warning,
            "bridge_strength_abs": {},
            "bridge_expected_influence": {},
        }

    # 2. Compute Bridge Metrics
    # Bridge Strength: sum of abs(weight) for edges connecting DIFFERENT groups
    # Bridge EI: sum of signed weight for edges connecting DIFFERENT groups
    b_strength: dict[str, float] = {}
    b_ei: dict[str, float] = {}

    # Initialize all grouped nodes to 0.0 (optional, but good for completeness)
    for nid, g in node_groups.items():
        if g:
            b_strength[nid] = 0.0
            b_ei[nid] = 0.0

    for edge in edges:
        u, v = edge["source"], edge["target"]
        g_u = node_groups.get(u)
        g_v = node_groups.get(v)

        # Only count if BOTH nodes have groups and they are DIFFERENT
        if g_u and g_v and g_u != g_v:
            w = edge.get("weight", 0.0)
            w_abs = abs(w)

            # Update u
            b_strength[u] = b_strength.get(u, 0.0) + w_abs
            b_ei[u] = b_ei.get(u, 0.0) + w

            # Update v
            b_strength[v] = b_strength.get(v, 0.0) + w_abs
            b_ei[v] = b_ei.get(v, 0.0) + w

    return {
        "enabled": True,
        "group_key": group_key,
        "groups": sorted(list(groups_seen)),
        "bridge_strength_abs": b_strength,
        "bridge_expected_influence": b_ei,
    }


def compute_mst_backbone(
    edges: list[dict[str, Any]],
    *,
    eps: float = 1e-9,
) -> dict[str, Any]:
    """Compute Minimum Spanning Tree (or Forest) backbone.

    Uses distance = 1 / (abs(weight) + eps).

    Args:
        edges: List of edges to consider.
        eps: Small epsilon to avoid division by zero (though w=0 handled).

    Returns:
        Dict with enabled status, edge count, and list of backbone edges.
    """
    G = nx.Graph()

    # Build graph with distance attributes
    for edge in edges:
        u, v = edge["source"], edge["target"]
        w = edge.get("weight", 0.0)
        w_abs = abs(w)

        # Skip edges with <= 0 absolute weight for distance calc (cannot span)
        if w_abs <= 0:
            continue

        dist = 1.0 / (w_abs + eps)
        G.add_edge(
            u,
            v,
            weight=w,  # Original signed
            distance=dist,
            abs_weight=w_abs,
            sign=edge.get("sign", "unsigned"),
        )

    if len(G.edges) == 0:
        return {
            "enabled": True,
            "edge_count": 0,
            "edges": [],
            "notes": ["No edges with >0 weight available for MST."],
        }

    # Compute MST (handles forest if disconnected)
    # minimize 'distance' => maximize 'weight' basically
    T = nx.minimum_spanning_tree(G, weight="distance")

    mst_edges = []
    for u, v, data in T.edges(data=True):
        mst_edges.append(
            {
                "source": u,
                "target": v,
                "signed_weight": data["weight"],
                "abs_weight": data["abs_weight"],
                "sign": data["sign"],
                "distance": data["distance"],
            }
        )

    # Sort consistency: desc abs weight
    mst_edges.sort(key=lambda e: (-e["abs_weight"], e["source"], e["target"]))

    return {
        "enabled": True,
        "edge_count": len(mst_edges),
        "edges": mst_edges,
        "notes": ["MST computed on filtered network; disconnected graphs yield a forest."],
    }


def build_derived_metrics(
    results_json: dict[str, Any],
    explore_cfg: dict[str, Any],
    *,
    derived_version: str = "0.1.0",
) -> dict[str, Any]:
    """Compute all derived metrics and bundle into a results dict.

    Args:
        results_json: MGM results.
        explore_cfg: Exploration settings.
        derived_version: Version string for contract.

    Returns:
        Dictionary conforming to derived_metrics.json structure.
    """
    # 1. Prep
    analysis_id = results_json.get("analysis_id", "")
    nodes_meta = make_nodes_meta(results_json)
    edges_filtered = filter_edges_for_explore(results_json, explore_cfg)
    messages = []

    # 2. Base Metrics
    strength_abs = compute_node_strength_abs(edges_filtered)
    expected_influence = compute_expected_influence(edges_filtered)

    # 3. Bridge Metrics
    bridge_res = compute_bridge_metrics(edges_filtered, nodes_meta)
    if not bridge_res["enabled"]:
        # Requirement: "If disabled: write a warning message into messages[]"
        if bridge_res.get("warning"):
            messages.append(
                {
                    "level": "warning",
                    "code": "BRIDGE_DISABLED",
                    "message": bridge_res["warning"],
                }
            )

    # 4. MST
    mst_res = compute_mst_backbone(edges_filtered)
    if mst_res["edge_count"] < 1:
        messages.append(
            {
                "level": "warning",
                "code": "MST_EMPTY",
                "message": (
                    "MST computation yielded 0 edges. Graph might be empty or all weights zero."
                ),
            }
        )

    # 5. Assemble
    # Fill in missing nodes with 0? The requirement says "strength_abs(i) = sum...".
    # If a node has no edges in 'edges_filtered', its score should be 0.
    # The current implementations only return entries for nodes touching edges.
    # We should ensure ALL nodes in results_json have an entry?
    # "Return dict node_id -> float".
    # Usually better to be explicit.
    all_node_ids = set(n["id"] for n in results_json.get("nodes", []))
    for nid in all_node_ids:
        if nid not in strength_abs:
            strength_abs[nid] = 0.0
        if nid not in expected_influence:
            expected_influence[nid] = 0.0

    # Clean bridge output structure for final JSON
    bridge_out = {
        "enabled": bridge_res["enabled"],
        "group_key": bridge_res["group_key"],
        "groups": bridge_res.get("groups", []),
        "warning": bridge_res.get("warning", ""),
    }

    output = {
        "analysis_id": analysis_id,
        "derived_version": derived_version,
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": {
            "threshold": explore_cfg.get("threshold"),
            "use_absolute_weights": explore_cfg.get("use_absolute_weights"),
            "top_edges": explore_cfg.get("top_edges"),
            "backbone_only": False,  # Not strictly in cfg schema yet, but good to have
        },
        "node_metrics": {
            "strength_abs": strength_abs,
            "expected_influence": expected_influence,
            # If valid, include bridge scores. If disabled, empty dicts.
            "bridge_strength_abs": bridge_res.get("bridge_strength_abs", {}),
            "bridge_expected_influence": bridge_res.get("bridge_expected_influence", {}),
        },
        "bridge": bridge_out,
        "mst": mst_res,
        "messages": messages,
    }

    return output


def write_derived_metrics_json(obj: dict[str, Any], out_path: Path) -> Path:
    """Write derived metrics object to JSON file.

    Args:
        obj: The derived metrics dict.
        out_path: Destination path.

    Returns:
        out_path
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
    return out_path
