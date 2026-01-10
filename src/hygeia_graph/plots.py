"""Plotting and visualization helpers for Hygeia-Graph.

This module generates Plotly charts and dataframes for the Explore and Report
pages. It relies on metric computation from posthoc_metrics.
"""

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Recycle the robust filtering logic from Agent B
from hygeia_graph.posthoc_metrics import filter_edges_for_explore


def build_node_metrics_df(derived_metrics_json: dict[str, Any]) -> pd.DataFrame:
    """Build a DataFrame of node metrics for display or export.

    Args:
        derived_metrics_json: The output from build_derived_metrics (Agent B).

    Returns:
        DataFrame with columns [node_id, strength_abs, expected_influence, ...],
        sorted by strength_abs descending.
    """
    nm = derived_metrics_json.get("node_metrics", {})
    strength_abs = nm.get("strength_abs", {})
    expected_influence = nm.get("expected_influence", {})
    bridge_strength = nm.get("bridge_strength_abs", {})
    bridge_ei = nm.get("bridge_expected_influence", {})

    all_nodes = set(strength_abs.keys()) | set(expected_influence.keys())
    if not all_nodes:
        return pd.DataFrame(columns=["node_id", "strength_abs", "expected_influence"])

    rows = []
    for node in all_nodes:
        row = {
            "node_id": node,
            "strength_abs": float(strength_abs.get(node, 0.0)),
            "expected_influence": float(expected_influence.get(node, 0.0)),
        }
        if bridge_strength:
            row["bridge_strength_abs"] = float(bridge_strength.get(node, 0.0))
        if bridge_ei:
            row["bridge_expected_influence"] = float(bridge_ei.get(node, 0.0))
        rows.append(row)

    df = pd.DataFrame(rows)
    # Sort by strength_abs descending
    df = df.sort_values("strength_abs", ascending=False).reset_index(drop=True)
    return df


def compute_edges_filtered_df(
    results_json: dict[str, Any],
    explore_cfg: dict[str, Any],
) -> pd.DataFrame:
    """Get the filtered edges as a DataFrame.

    Consistent with what is shown in the network graph.

    Args:
        results_json: Full results object.
        explore_cfg: Exploration config.

    Returns:
        DataFrame with columns [source, target, weight, sign, abs_weight].
    """
    edges_list = filter_edges_for_explore(results_json, explore_cfg)

    if not edges_list:
        return pd.DataFrame(columns=["source", "target", "weight", "sign", "abs_weight"])

    rows = []
    for e in edges_list:
        rows.append(
            {
                "source": e["source"],
                "target": e["target"],
                "weight": e.get("weight", 0.0),
                "sign": e.get("sign", "unsigned"),
                "abs_weight": abs(e.get("weight", 0.0)),
            }
        )

    # Already sorted by filter_edges_for_explore, but we return a DF
    return pd.DataFrame(rows)


def build_adjacency_matrix_df(
    results_json: dict[str, Any],
    explore_cfg: dict[str, Any],
    *,
    value_mode: str = "signed",
) -> pd.DataFrame:
    """Build an NxN adjacency matrix DataFrame from filtered edges.

    Args:
        results_json: Full results object.
        explore_cfg: Exploration config.
        value_mode: "signed" (default) or "abs".

    Returns:
        DataFrame indexed by node_id, columns are node_id.
        Symmetric for undirected graphs.
    """
    # 1. Get filtered edges
    edges_list = filter_edges_for_explore(results_json, explore_cfg)

    # 2. Identify all nodes (from results to preserve universe, or just edges?)
    # Usually adjacency matrix should include all nodes in the analysis,
    # even if isolated by filtering.
    nodes = results_json.get("nodes", [])
    node_ids = sorted([n["id"] for n in nodes])

    if not node_ids:
        # Fallback if nodes missing from results for some reason
        seen = set()
        for e in edges_list:
            seen.add(e["source"])
            seen.add(e["target"])
        node_ids = sorted(list(seen))

    # 3. Init DataFrame
    df = pd.DataFrame(0.0, index=node_ids, columns=node_ids)

    # 4. Fill values
    for e in edges_list:
        u, v = e["source"], e["target"]
        if u in df.index and v in df.columns:
            w = e.get("weight", 0.0)
            val = abs(w) if value_mode == "abs" else w

            df.at[u, v] = val
            df.at[v, u] = val

    return df


def make_centrality_bar_plot(
    node_metrics_df: pd.DataFrame,
    metric: str,
    *,
    top_n: int = 20,
    title: str | None = None,
) -> go.Figure:
    """Create a horizontal bar chart for a centrality metric.

    Args:
        node_metrics_df: DataFrame from build_node_metrics_df.
        metric: Column name to plot (e.g., "expected_influence").
        top_n: Number of nodes to show (ranked by abs value).
        title: Plot title.

    Returns:
        Plotly Figure.
    """
    if metric not in node_metrics_df.columns:
        return px.bar(title=f"Metric {metric} not found")

    # Select top N by absolute value
    # But for display, we want the actual sign if metric is signed
    df = node_metrics_df.copy()
    df["_sort_key"] = df[metric].abs()
    top_df = df.sort_values("_sort_key", ascending=False).head(top_n)

    # Sort for plot (barh plots bottom-to-top, so we want ascending sort)
    # Actually wait, usually we want biggest on top.
    # px.bar with orientation='h' puts first item at bottom unless we reverse?
    # Let's trust sort_values("_sort_key", ascending=True) puts smallest abs at top
    # so big ones are at bottom?
    # Better: sort by metric value itself or abs?
    # Let's stick to standard practice: biggest bar on top.
    top_df = top_df.sort_values("_sort_key", ascending=True)

    fig = px.bar(
        top_df,
        x=metric,
        y="node_id",
        orientation="h",
        title=title or f"Top {top_n} Nodes by {metric} (Abs)",
        text_auto=".2f",
    )

    # Optional: nicer layout
    fig.update_layout(
        xaxis_title=metric,
        yaxis_title="Node",
        height=max(400, top_n * 20),
    )

    return fig


def make_adjacency_heatmap(
    adjacency_df: pd.DataFrame,
    *,
    title: str | None = None,
) -> go.Figure:
    """Create a heatmap from the adjacency matrix.

    Args:
        adjacency_df: NxN DataFrame.
        title: Plot title.

    Returns:
        Plotly Figure.
    """
    # Simply heatmap
    # Check if signed or abs to determine colors
    # data values:
    vals = adjacency_df.values
    min_val = vals.min()

    # If we have negative values, use diverging colors (RdBu)
    # If all positive, use sequential (Blues or similar)
    colorscale = "RdBu" if min_val < 0 else "Blues"

    # If RdBu, zero should be white (middle).
    # Plotly handles zmid automatically if we set it?
    # Or simplified: just let plotly decide default for now.

    fig = px.imshow(
        adjacency_df,
        text_auto=".2f" if len(adjacency_df) < 20 else False,
        aspect="equal",
        color_continuous_scale=colorscale,
        origin="upper",  # Matrix convention (0,0 at top-left)
        title=title or "Adjacency Matrix",
    )

    fig.update_layout(
        xaxis_title="Node",
        yaxis_title="Node",
    )

    return fig
