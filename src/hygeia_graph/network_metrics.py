"""Network metrics and graph construction from MGM results.

This module provides functions to build NetworkX graphs from validated
results.json and compute centrality metrics.
"""

from typing import Any

import networkx as nx
import pandas as pd


def make_nodes_meta(results_json: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Create a mapping of node ID to node metadata.

    Args:
        results_json: Validated results.json object

    Returns:
        Dictionary mapping node ID to node attributes
    """
    nodes_meta = {}
    for node in results_json.get("nodes", []):
        node_id = node["id"]
        nodes_meta[node_id] = {
            "column": node.get("column", node_id),
            "label": node.get("label", node_id),
            "domain_group": node.get("domain_group"),
            "mgm_type": node.get("mgm_type"),
            "measurement_level": node.get("measurement_level"),
            "level": node.get("level"),
        }
    return nodes_meta


def build_graph_from_results(
    results_json: dict[str, Any],
    *,
    use_absolute_weights: bool = True,
    include_zero_edges: bool = False,
) -> nx.Graph:
    """Build a NetworkX graph from results.json.

    Args:
        results_json: Validated results.json object
        use_absolute_weights: If True, store abs(weight) as edge weight
        include_zero_edges: If True, include edges with weight=0

    Returns:
        Undirected NetworkX graph with nodes and weighted edges
    """
    G = nx.Graph()

    # Add nodes with attributes
    for node in results_json.get("nodes", []):
        node_id = node["id"]
        G.add_node(
            node_id,
            column=node.get("column", node_id),
            label=node.get("label", node_id),
            domain_group=node.get("domain_group"),
            mgm_type=node.get("mgm_type"),
            measurement_level=node.get("measurement_level"),
            level=node.get("level"),
        )

    # Add edges with attributes
    for edge in results_json.get("edges", []):
        source = edge["source"]
        target = edge["target"]
        weight = edge.get("weight", 0)
        sign = edge.get("sign", "unsigned")
        block_summary = edge.get("block_summary", {})

        # Skip zero edges if not including them
        if not include_zero_edges and weight == 0:
            continue

        # Compute display weight
        w = abs(weight) if use_absolute_weights else weight

        # Ensure consistent edge ordering (lexicographic)
        if source > target:
            source, target = target, source

        # Add edge with attributes
        G.add_edge(
            source,
            target,
            weight=w,
            signed_weight=edge.get("weight", 0),
            sign=sign,
            block_summary=block_summary,
        )

    return G


def filter_edges_by_threshold(
    results_json: dict[str, Any],
    threshold: float,
    *,
    use_absolute_weights: bool = True,
) -> list[dict[str, Any]]:
    """Filter edges by weight threshold.

    Args:
        results_json: Validated results.json object
        threshold: Minimum weight to include (must be >= 0)
        use_absolute_weights: If True, filter by abs(weight)

    Returns:
        List of edge dicts that meet the threshold, sorted by
        descending abs(weight), then lexicographic (source, target)

    Raises:
        ValueError: If threshold < 0
    """
    if threshold < 0:
        raise ValueError("threshold must be >= 0")

    filtered = []
    for edge in results_json.get("edges", []):
        weight = edge.get("weight", 0)
        metric = abs(weight) if use_absolute_weights else weight

        if metric >= threshold:
            filtered.append(edge.copy())

    # Sort by descending abs(weight), then lexicographic (source, target)
    filtered.sort(
        key=lambda e: (
            -abs(e.get("weight", 0)),
            min(e["source"], e["target"]),
            max(e["source"], e["target"]),
        )
    )

    return filtered


def edges_to_dataframe(
    edges: list[dict[str, Any]],
    nodes_meta: dict[str, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """Convert edges list to a DataFrame.

    Args:
        edges: List of edge dicts
        nodes_meta: Optional mapping of node ID to metadata

    Returns:
        DataFrame with edge information including block_summary fields
    """
    if not edges:
        return pd.DataFrame(
            columns=[
                "source",
                "target",
                "weight",
                "abs_weight",
                "sign",
                "n_params",
                "l2_norm",
                "mean",
                "max",
                "min",
                "max_abs",
            ]
        )

    rows = []
    for edge in edges:
        block = edge.get("block_summary", {})
        row = {
            "source": edge["source"],
            "target": edge["target"],
            "weight": edge.get("weight", 0),
            "abs_weight": abs(edge.get("weight", 0)),
            "sign": edge.get("sign", "unsigned"),
            "n_params": block.get("n_params"),
            "l2_norm": block.get("l2_norm"),
            "mean": block.get("mean"),
            "max": block.get("max"),
            "min": block.get("min"),
            "max_abs": block.get("max_abs"),
        }

        # Add node metadata if available
        if nodes_meta:
            source_meta = nodes_meta.get(edge["source"], {})
            target_meta = nodes_meta.get(edge["target"], {})
            row["source_group"] = source_meta.get("domain_group")
            row["target_group"] = target_meta.get("domain_group")
            row["source_type"] = source_meta.get("mgm_type")
            row["target_type"] = target_meta.get("mgm_type")

        rows.append(row)

    return pd.DataFrame(rows)


def compute_strength_centrality(G: nx.Graph) -> dict[str, float]:
    """Compute strength centrality for all nodes.

    Strength is the sum of edge weights incident to each node.

    Args:
        G: NetworkX graph with edge weights

    Returns:
        Dictionary mapping node ID to strength value
    """
    strength = {}
    for node in G.nodes():
        total = sum(data.get("weight", 0) for _, _, data in G.edges(node, data=True))
        strength[node] = total
    return strength


def compute_centrality_table(
    G: nx.Graph,
    *,
    compute_betweenness: bool = True,
    compute_closeness: bool = False,
) -> pd.DataFrame:
    """Compute centrality metrics for all nodes.

    Args:
        G: NetworkX graph with edge weights
        compute_betweenness: Include betweenness centrality
        compute_closeness: Include closeness centrality

    Returns:
        DataFrame with node_id, strength, and optional centrality columns,
        sorted by strength descending
    """
    # Always compute strength
    strength = compute_strength_centrality(G)

    # Get node attributes for enrichment
    data = []
    for node in G.nodes():
        row = {
            "node_id": node,
            "strength": strength.get(node, 0),
        }
        # Add node attributes
        node_data = G.nodes[node]
        row["label"] = node_data.get("label", node)
        row["mgm_type"] = node_data.get("mgm_type")
        row["domain_group"] = node_data.get("domain_group")
        data.append(row)

    df = pd.DataFrame(data)

    # Compute betweenness if requested
    if compute_betweenness and len(G.edges()) > 0:
        try:
            betweenness = nx.betweenness_centrality(G, weight="weight", normalized=True)
            df["betweenness"] = df["node_id"].map(betweenness)
        except Exception:
            df["betweenness"] = 0.0
    elif compute_betweenness:
        df["betweenness"] = 0.0

    # Compute closeness if requested
    if compute_closeness and len(G.edges()) > 0:
        try:
            # Create a copy with distance = 1/weight
            G_dist = G.copy()
            for u, v, d in G_dist.edges(data=True):
                w = d.get("weight", 1)
                G_dist[u][v]["distance"] = 1 / w if w > 0 else 1e10

            closeness = nx.closeness_centrality(G_dist, distance="distance")
            df["closeness"] = df["node_id"].map(closeness)
        except Exception:
            df["closeness"] = 0.0
    elif compute_closeness:
        df["closeness"] = 0.0

    # Sort by strength descending
    df = df.sort_values("strength", ascending=False).reset_index(drop=True)

    return df
