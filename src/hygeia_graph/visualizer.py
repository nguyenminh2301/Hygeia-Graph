"""PyVis network visualization for MGM results.

This module provides functions to build interactive PyVis network
visualizations from NetworkX graphs.
"""

import tempfile
from pathlib import Path
from typing import Any

import networkx as nx
from pyvis.network import Network

# Color palettes for node types
NODE_COLORS = {
    "g": "#4A90D9",  # Blue for Gaussian
    "c": "#E67E22",  # Orange for Categorical
    "p": "#27AE60",  # Green for Poisson
}

# Color palettes for edge signs
EDGE_COLORS = {
    "positive": "#27AE60",  # Green
    "negative": "#E74C3C",  # Red
    "zero": "#95A5A6",  # Gray
    "unsigned": "#7F8C8D",  # Dark gray
}


def get_node_style(node_attrs: dict[str, Any]) -> dict[str, Any]:
    """Generate PyVis node styling from node attributes.

    Args:
        node_attrs: Node metadata (id, column, mgm_type, etc.)

    Returns:
        Dict with PyVis node properties: color, shape, title, label
    """
    node_id = node_attrs.get("id", "unknown")
    mgm_type = node_attrs.get("mgm_type", "g")
    column = node_attrs.get("column", node_id)
    label = node_attrs.get("label", node_id)
    measurement_level = node_attrs.get("measurement_level", "unknown")
    level = node_attrs.get("level", 1)
    domain_group = node_attrs.get("domain_group")

    # Color by mgm_type
    color = NODE_COLORS.get(mgm_type, "#4A90D9")

    # Build tooltip HTML
    tooltip_parts = [
        f"<b>{label}</b>",
        f"ID: {node_id}",
        f"Column: {column}",
        f"Type: {mgm_type} ({measurement_level})",
        f"Level: {level}",
    ]
    if domain_group:
        tooltip_parts.append(f"Group: {domain_group}")

    tooltip = "<br>".join(tooltip_parts)

    return {
        "color": color,
        "shape": "dot",
        "title": tooltip,
        "label": label,
        "size": 20,
    }


def get_edge_style(
    edge_attrs: dict[str, Any],
    *,
    use_absolute_weights: bool = True,
) -> dict[str, Any]:
    """Generate PyVis edge styling from edge attributes.

    Args:
        edge_attrs: Edge data (weight, signed_weight, sign, block_summary)
        use_absolute_weights: Whether to show absolute weights in tooltip

    Returns:
        Dict with PyVis edge properties: value, color, title
    """
    signed_weight = edge_attrs.get("signed_weight", edge_attrs.get("weight", 0))
    sign = edge_attrs.get("sign", "unsigned")
    block_summary = edge_attrs.get("block_summary", {})
    source = edge_attrs.get("source", "?")
    target = edge_attrs.get("target", "?")

    # Width based on absolute weight
    abs_weight = abs(signed_weight)

    # Color by sign
    color = EDGE_COLORS.get(sign, EDGE_COLORS["unsigned"])

    # Build tooltip
    tooltip_parts = [
        f"<b>{source} — {target}</b>",
        f"Weight: {signed_weight:.4f}",
        f"|Weight|: {abs_weight:.4f}",
        f"Sign: {sign}",
    ]

    # Add block summary if available
    if block_summary:
        tooltip_parts.append("---")
        if "n_params" in block_summary:
            tooltip_parts.append(f"Parameters: {block_summary['n_params']}")
        if "l2_norm" in block_summary:
            tooltip_parts.append(f"L2 Norm: {block_summary['l2_norm']:.4f}")
        if "max_abs" in block_summary:
            tooltip_parts.append(f"Max |param|: {block_summary['max_abs']:.4f}")

    tooltip = "<br>".join(tooltip_parts)

    return {
        "value": abs_weight,  # For thickness scaling
        "color": color,
        "title": tooltip,
    }


def build_pyvis_network(
    G: nx.Graph,
    *,
    nodes_meta: dict[str, dict[str, Any]],
    height: str = "650px",
    width: str = "100%",
    notebook: bool = False,
    show_labels: bool = True,
    physics: bool = True,
) -> Network:
    """Build a PyVis Network from a NetworkX graph.

    Args:
        G: NetworkX graph with nodes and weighted edges
        nodes_meta: Mapping of node ID to metadata
        height: Network height (CSS value)
        width: Network width (CSS value)
        notebook: Whether running in Jupyter notebook
        show_labels: Whether to show node labels
        physics: Whether to enable physics simulation

    Returns:
        PyVis Network object
    """
    net = Network(
        height=height,
        width=width,
        directed=False,
        notebook=notebook,
        cdn_resources="remote",
    )

    # Add nodes
    for node_id in G.nodes():
        # Get node metadata
        node_data = nodes_meta.get(node_id, {"id": node_id})
        if "id" not in node_data:
            node_data["id"] = node_id

        # Get styling
        style = get_node_style(node_data)

        # Optionally hide labels
        if not show_labels:
            style["label"] = ""

        net.add_node(
            node_id,
            label=style["label"],
            color=style["color"],
            shape=style["shape"],
            title=style["title"],
            size=style["size"],
        )

    # Add edges
    for u, v, data in G.edges(data=True):
        # Add source/target to data for tooltip
        edge_data = dict(data)
        edge_data["source"] = u
        edge_data["target"] = v

        # Get styling
        style = get_edge_style(edge_data)

        net.add_edge(
            u,
            v,
            value=style["value"],
            color=style["color"],
            title=style["title"],
        )

    # Configure physics
    if physics:
        net.barnes_hut(
            gravity=-8000,
            central_gravity=0.3,
            spring_length=200,
            spring_strength=0.01,
            damping=0.09,
        )
    else:
        net.toggle_physics(False)

    return net


def network_to_html(net: Network) -> str:
    """Generate HTML string from PyVis Network.

    Args:
        net: PyVis Network object

    Returns:
        HTML string containing the network visualization
    """
    # Write to temporary file and read back
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        tmp_path = Path(f.name)

    try:
        net.save_graph(str(tmp_path))
        html = tmp_path.read_text(encoding="utf-8")
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass

    return html


def save_network_html(net: Network, out_path: Path) -> Path:
    """Save PyVis network to HTML file.

    Args:
        net: PyVis Network object
        out_path: Output file path

    Returns:
        Path to saved file
    """
    # Ensure parent directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    net.save_graph(str(out_path))

    return out_path


def prepare_legend_html() -> str:
    """Generate HTML legend for node types and edge colors.

    Returns:
        HTML string for legend display
    """
    legend = """
    <div style="padding: 10px; background: #f8f9fa; border-radius: 5px; font-size: 14px;">
        <b>Node Types:</b><br>
        <span style="color: #4A90D9;">●</span> Gaussian (g)<br>
        <span style="color: #E67E22;">●</span> Categorical (c)<br>
        <span style="color: #27AE60;">●</span> Poisson (p)<br>
        <br>
        <b>Edge Signs:</b><br>
        <span style="color: #27AE60;">━</span> Positive<br>
        <span style="color: #E74C3C;">━</span> Negative<br>
        <span style="color: #95A5A6;">━</span> Zero/Unsigned
    </div>
    """
    return legend.strip()
