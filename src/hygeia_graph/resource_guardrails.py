"""Resource safety guardrails for Hygeia-Graph.

Provides functions to recommend safe defaults and enforce limits
based on network size to prevent memory/performance issues.
"""

from typing import Any, Dict, List, Tuple

# Thresholds
NODES_HIDE_LABELS = 80
NODES_LIMIT_EDGES = 120
NODES_DISABLE_PYVIS = 200
EDGES_REQUIRE_THRESHOLD = 5000
MAX_EDGES_ALLOWED = 10000


def recommend_defaults(n_nodes: int, n_edges: int) -> Dict[str, Any]:
    """Recommend safe default configuration based on network size.

    Args:
        n_nodes: Number of nodes in the network.
        n_edges: Number of edges in the network.

    Returns:
        Dictionary with recommended settings and explanations.
    """
    recommendations = {
        "show_labels": True,
        "top_edges": None,
        "threshold": 0.0,
        "pyvis_enabled": True,
        "warnings": [],
    }

    # Large node count -> hide labels
    if n_nodes > NODES_HIDE_LABELS:
        recommendations["show_labels"] = False
        recommendations["warnings"].append(
            f"Labels hidden (>{NODES_HIDE_LABELS} nodes) for readability."
        )

    # Very large node count -> limit edges
    if n_nodes > NODES_LIMIT_EDGES:
        recommendations["top_edges"] = 1000
        recommendations["warnings"].append(
            f"Top edges limited to 1000 (>{NODES_LIMIT_EDGES} nodes)."
        )

    # Huge network -> disable PyVis by default
    if n_nodes > NODES_DISABLE_PYVIS:
        recommendations["pyvis_enabled"] = False
        recommendations["threshold"] = 0.1
        recommendations["warnings"].append(
            f"PyVis disabled by default (>{NODES_DISABLE_PYVIS} nodes). "
            "Increase threshold or reduce top_edges to enable."
        )

    # Many edges -> require threshold
    if n_edges > EDGES_REQUIRE_THRESHOLD:
        if recommendations["threshold"] < 0.05:
            recommendations["threshold"] = 0.05
        recommendations["warnings"].append(
            f"High edge count ({n_edges}). Threshold increased for performance."
        )

    return recommendations


def enforce_explore_config(
    cfg: Dict[str, Any], n_nodes: int, n_edges: int
) -> Tuple[Dict[str, Any], List[str]]:
    """Enforce resource limits on explore configuration.

    Args:
        cfg: User-provided explore configuration.
        n_nodes: Number of nodes.
        n_edges: Number of edges.

    Returns:
        Tuple of (clamped_config, list_of_warning_messages).
    """
    cfg2 = cfg.copy()
    messages = []

    # Enforce top_edges limit for very large networks
    if n_nodes > NODES_DISABLE_PYVIS:
        user_top = cfg2.get("top_edges")
        if user_top is None or user_top > MAX_EDGES_ALLOWED:
            cfg2["top_edges"] = min(user_top or MAX_EDGES_ALLOWED, MAX_EDGES_ALLOWED)
            messages.append(f"top_edges clamped to {cfg2['top_edges']} for large network.")

    # Enforce minimum threshold for huge edge counts
    if n_edges > EDGES_REQUIRE_THRESHOLD:
        user_thresh = cfg2.get("threshold", 0.0)
        min_thresh = 0.01
        if user_thresh < min_thresh:
            cfg2["threshold"] = min_thresh
            messages.append(
                f"Threshold increased to {min_thresh} (>{EDGES_REQUIRE_THRESHOLD} edges)."
            )

    # Disable PyVis for massive networks if not already filtered
    if n_nodes > NODES_DISABLE_PYVIS:
        filtered_edges = cfg2.get("top_edges", n_edges)
        if filtered_edges > 2000:
            cfg2["pyvis_enabled"] = False
            messages.append(
                "PyVis visualization disabled for this network size. "
                "Use Publication Pack for static figures."
            )

    return cfg2, messages


def estimate_memory(n_nodes: int) -> Dict[str, Any]:
    """Estimate memory usage for adjacency matrix operations.

    Args:
        n_nodes: Number of nodes.

    Returns:
        Dictionary with memory estimates.
    """
    # Dense adjacency matrix: n^2 * 8 bytes (float64)
    adjacency_bytes = n_nodes * n_nodes * 8
    adjacency_mb = adjacency_bytes / (1024 * 1024)

    # PyVis network object estimate (rough)
    pyvis_mb = adjacency_mb * 2  # Overhead for JS serialization

    # Warning level
    if adjacency_mb > 500:
        level = "critical"
        message = "Very large network. Consider filtering or using static exports."
    elif adjacency_mb > 100:
        level = "warning"
        message = "Large network. Filtering recommended for smooth interaction."
    elif adjacency_mb > 50:
        level = "info"
        message = "Moderate network size. Should work with reasonable filtering."
    else:
        level = "ok"
        message = "Network size is within normal range."

    return {
        "n_nodes": n_nodes,
        "adjacency_mb": round(adjacency_mb, 2),
        "pyvis_estimate_mb": round(pyvis_mb, 2),
        "level": level,
        "message": message,
    }


def check_network_health(n_nodes: int, n_edges: int) -> Dict[str, Any]:
    """Combined health check for network visualization.

    Returns a summary suitable for UI display.
    """
    mem = estimate_memory(n_nodes)
    rec = recommend_defaults(n_nodes, n_edges)

    return {
        "memory": mem,
        "recommendations": rec,
        "safe_to_render": mem["level"] in ("ok", "info") and rec["pyvis_enabled"],
    }
