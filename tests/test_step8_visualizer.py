"""Unit tests for Step 8 PyVis visualizer module."""

import networkx as nx
import pytest

from hygeia_graph.visualizer import (
    EDGE_COLORS,
    NODE_COLORS,
    build_pyvis_network,
    get_edge_style,
    get_node_style,
    network_to_html,
    prepare_legend_html,
    save_network_html,
)


@pytest.fixture
def sample_nodes_meta():
    """Create sample node metadata for testing."""
    return {
        "A": {
            "id": "A",
            "column": "var_a",
            "label": "Variable A",
            "mgm_type": "g",
            "measurement_level": "continuous",
            "level": 1,
            "domain_group": "group1",
        },
        "B": {
            "id": "B",
            "column": "var_b",
            "label": "Variable B",
            "mgm_type": "c",
            "measurement_level": "nominal",
            "level": 3,
            "domain_group": "group1",
        },
        "C": {
            "id": "C",
            "column": "var_c",
            "label": "Variable C",
            "mgm_type": "p",
            "measurement_level": "count",
            "level": 1,
            "domain_group": "group2",
        },
    }


@pytest.fixture
def sample_graph(sample_nodes_meta):
    """Create a sample NetworkX graph for testing."""
    G = nx.Graph()

    # Add nodes
    for node_id, meta in sample_nodes_meta.items():
        G.add_node(node_id, **meta)

    # Add edges with signed weights
    G.add_edge(
        "A",
        "B",
        weight=0.8,
        signed_weight=0.8,
        sign="positive",
        block_summary={"n_params": 1, "l2_norm": 0.8, "max_abs": 0.8},
    )
    G.add_edge(
        "B",
        "C",
        weight=0.4,
        signed_weight=-0.4,
        sign="negative",
        block_summary={"n_params": 3, "l2_norm": 0.69, "max_abs": 0.4},
    )

    return G


class TestNodeStyle:
    """Test node styling functions."""

    def test_node_style_contains_tooltip_and_color(self, sample_nodes_meta):
        """Test that get_node_style returns required keys."""
        node_attrs = sample_nodes_meta["A"]
        style = get_node_style(node_attrs)

        # Check required keys
        assert "color" in style
        assert "title" in style
        assert "label" in style
        assert "shape" in style

        # Check tooltip contains expected info
        assert "Variable A" in style["title"]
        assert "var_a" in style["title"] or "A" in style["title"]
        assert "g" in style["title"]

    def test_node_color_by_mgm_type(self, sample_nodes_meta):
        """Test that node color is determined by mgm_type."""
        # Gaussian node
        style_g = get_node_style(sample_nodes_meta["A"])
        assert style_g["color"] == NODE_COLORS["g"]

        # Categorical node
        style_c = get_node_style(sample_nodes_meta["B"])
        assert style_c["color"] == NODE_COLORS["c"]

        # Poisson node
        style_p = get_node_style(sample_nodes_meta["C"])
        assert style_p["color"] == NODE_COLORS["p"]

    def test_node_label_matches_metadata(self, sample_nodes_meta):
        """Test that node label comes from metadata."""
        style = get_node_style(sample_nodes_meta["A"])
        assert style["label"] == "Variable A"


class TestEdgeStyle:
    """Test edge styling functions."""

    def test_edge_style_value_is_abs(self):
        """Test that edge value is absolute weight."""
        # Positive edge
        edge_pos = {
            "weight": 0.8,
            "signed_weight": 0.8,
            "sign": "positive",
            "source": "A",
            "target": "B",
        }
        style_pos = get_edge_style(edge_pos)
        assert style_pos["value"] == 0.8

        # Negative edge
        edge_neg = {
            "weight": 0.4,
            "signed_weight": -0.4,
            "sign": "negative",
            "source": "B",
            "target": "C",
        }
        style_neg = get_edge_style(edge_neg)
        assert style_neg["value"] == 0.4  # abs(-0.4)

    def test_edge_color_differs_by_sign(self):
        """Test that edge color differs for positive vs negative."""
        edge_pos = {"signed_weight": 0.5, "sign": "positive", "source": "A", "target": "B"}
        edge_neg = {"signed_weight": -0.5, "sign": "negative", "source": "B", "target": "C"}

        style_pos = get_edge_style(edge_pos)
        style_neg = get_edge_style(edge_neg)

        assert style_pos["color"] == EDGE_COLORS["positive"]
        assert style_neg["color"] == EDGE_COLORS["negative"]
        assert style_pos["color"] != style_neg["color"]

    def test_edge_tooltip_contains_weight(self):
        """Test that edge tooltip contains weight information."""
        edge = {
            "signed_weight": 0.8,
            "sign": "positive",
            "source": "A",
            "target": "B",
            "block_summary": {"n_params": 1, "l2_norm": 0.8},
        }
        style = get_edge_style(edge)

        assert "0.8" in style["title"]
        assert "positive" in style["title"]


class TestBuildPyvisNetwork:
    """Test PyVis network building."""

    def test_build_pyvis_network_returns_network(self, sample_graph, sample_nodes_meta):
        """Test that build_pyvis_network returns a Network object."""
        from pyvis.network import Network

        net = build_pyvis_network(sample_graph, nodes_meta=sample_nodes_meta)

        assert isinstance(net, Network)

    def test_build_pyvis_network_has_nodes_and_edges(self, sample_graph, sample_nodes_meta):
        """Test that network contains expected nodes and edges."""
        net = build_pyvis_network(sample_graph, nodes_meta=sample_nodes_meta)

        # Check nodes (pyvis stores as list of dicts)
        assert len(net.nodes) == 3

        # Check edges
        assert len(net.edges) == 2

    def test_show_labels_toggle(self, sample_graph, sample_nodes_meta):
        """Test that show_labels=False produces empty or minimal labels."""
        net = build_pyvis_network(sample_graph, nodes_meta=sample_nodes_meta, show_labels=False)

        # When show_labels=False, labels should not be the full variable names
        for node in net.nodes:
            label = node.get("label", "")
            # Label should be empty string (not the full "Variable A" etc.)
            # PyVis may still use node ID internally, but we passed empty string
            assert label != sample_nodes_meta.get(node["id"], {}).get("label", "") or label == ""


class TestNetworkToHtml:
    """Test HTML generation."""

    def test_network_to_html_nonempty(self, sample_graph, sample_nodes_meta):
        """Test that network_to_html returns non-empty HTML."""
        net = build_pyvis_network(sample_graph, nodes_meta=sample_nodes_meta)
        html = network_to_html(net)

        assert html is not None
        assert len(html) > 0
        assert "<html" in html.lower() or "vis-network" in html.lower()

    def test_network_to_html_contains_vis(self, sample_graph, sample_nodes_meta):
        """Test that HTML contains vis.js network elements."""
        net = build_pyvis_network(sample_graph, nodes_meta=sample_nodes_meta)
        html = network_to_html(net)

        # Should contain vis.js related content
        assert "vis" in html.lower()


class TestSaveNetworkHtml:
    """Test HTML file saving."""

    def test_save_network_html_creates_file(self, tmp_path, sample_graph, sample_nodes_meta):
        """Test that save_network_html creates a file."""
        net = build_pyvis_network(sample_graph, nodes_meta=sample_nodes_meta)
        out_path = tmp_path / "network.html"

        result = save_network_html(net, out_path)

        assert result == out_path
        assert out_path.exists()
        assert out_path.stat().st_size > 0


class TestLegend:
    """Test legend generation."""

    def test_prepare_legend_html_nonempty(self):
        """Test that legend HTML is non-empty."""
        legend = prepare_legend_html()

        assert legend is not None
        assert len(legend) > 0
        assert "Gaussian" in legend
        assert "Categorical" in legend
        assert "Positive" in legend
        assert "Negative" in legend
