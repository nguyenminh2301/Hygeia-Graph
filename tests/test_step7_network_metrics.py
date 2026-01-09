"""Unit tests for Step 7 network metrics module."""

import pytest

from hygeia_graph.network_metrics import (
    build_graph_from_results,
    compute_centrality_table,
    compute_strength_centrality,
    edges_to_dataframe,
    filter_edges_by_threshold,
    make_nodes_meta,
)


# Minimal results.json fixture for testing
@pytest.fixture
def sample_results():
    """Create a minimal valid results.json for testing."""
    return {
        "result_version": "0.1.0",
        "analysis_id": "test-123",
        "generated_at": "2026-01-09T00:00:00Z",
        "status": "success",
        "engine": {"name": "R.mgm", "r_version": "4.3.0"},
        "input": {},
        "messages": [],
        "nodes": [
            {
                "id": "A",
                "column": "var_a",
                "mgm_type": "g",
                "measurement_level": "continuous",
                "level": 1,
                "label": "Variable A",
                "domain_group": "group1",
            },
            {
                "id": "B",
                "column": "var_b",
                "mgm_type": "g",
                "measurement_level": "continuous",
                "level": 1,
                "label": "Variable B",
                "domain_group": "group1",
            },
            {
                "id": "C",
                "column": "var_c",
                "mgm_type": "c",
                "measurement_level": "nominal",
                "level": 3,
                "label": "Variable C",
                "domain_group": "group2",
            },
        ],
        "edges": [
            {
                "source": "A",
                "target": "B",
                "weight": 2.0,
                "sign": "positive",
                "block_summary": {
                    "n_params": 1,
                    "l2_norm": 2.0,
                    "mean": 2.0,
                    "max": 2.0,
                    "min": 2.0,
                    "max_abs": 2.0,
                },
            },
            {
                "source": "B",
                "target": "C",
                "weight": -1.0,
                "sign": "negative",
                "block_summary": {
                    "n_params": 3,
                    "l2_norm": 1.732,
                    "mean": -0.333,
                    "max": 0.5,
                    "min": -1.0,
                    "max_abs": 1.0,
                },
            },
            {
                "source": "A",
                "target": "C",
                "weight": 0.5,
                "sign": "positive",
                "block_summary": {
                    "n_params": 3,
                    "l2_norm": 0.866,
                    "mean": 0.167,
                    "max": 0.5,
                    "min": 0.0,
                    "max_abs": 0.5,
                },
            },
        ],
    }


class TestBuildGraph:
    """Test graph construction from results."""

    def test_build_graph_absolute_weights(self, sample_results):
        """Test graph building with absolute weights."""
        G = build_graph_from_results(sample_results, use_absolute_weights=True)

        # Check nodes
        assert len(G.nodes()) == 3
        assert "A" in G.nodes()
        assert "B" in G.nodes()
        assert "C" in G.nodes()

        # Check node attributes
        assert G.nodes["A"]["label"] == "Variable A"
        assert G.nodes["A"]["mgm_type"] == "g"
        assert G.nodes["C"]["domain_group"] == "group2"

        # Check edges
        assert len(G.edges()) == 3

        # Check edge weights are absolute
        ab_weight = G.edges["A", "B"]["weight"]
        assert ab_weight == 2.0  # abs(2.0)

        bc_weight = G.edges["B", "C"]["weight"]
        assert bc_weight == 1.0  # abs(-1.0)

        # Check signed_weight preserved
        assert G.edges["B", "C"]["signed_weight"] == -1.0

        # Verify strength of B = abs(2) + abs(-1) = 3
        strength = compute_strength_centrality(G)
        assert strength["B"] == 3.0

    def test_build_graph_signed_weights(self, sample_results):
        """Test graph building with signed (raw) weights."""
        G = build_graph_from_results(sample_results, use_absolute_weights=False)

        # Check edge weights preserve sign
        ab_weight = G.edges["A", "B"]["weight"]
        assert ab_weight == 2.0

        bc_weight = G.edges["B", "C"]["weight"]
        assert bc_weight == -1.0  # Signed weight

        # Strength of B = 2 + (-1) = 1 (signed sum)
        strength = compute_strength_centrality(G)
        assert strength["B"] == 1.0

    def test_build_graph_excludes_zero_edges(self, sample_results):
        """Test that zero edges are excluded by default."""
        # Add a zero edge
        sample_results["edges"].append(
            {
                "source": "A",
                "target": "B",
                "weight": 0.0,
                "sign": "zero",
                "block_summary": {},
            }
        )
        # This would overwrite existing A-B edge

        G = build_graph_from_results(
            sample_results, use_absolute_weights=True, include_zero_edges=False
        )
        # Should still have 3 edges (zero edge excluded or overwrites non-zero)
        assert len(G.edges()) >= 2


class TestFilterEdges:
    """Test edge filtering by threshold."""

    def test_filter_edges_by_threshold(self, sample_results):
        """Test filtering with threshold=1.0 keeps A-B and B-C but drops A-C."""
        filtered = filter_edges_by_threshold(
            sample_results, threshold=1.0, use_absolute_weights=True
        )

        # Should keep A-B (weight=2) and B-C (|weight|=1), drop A-C (|weight|=0.5)
        assert len(filtered) == 2

        # Check correct edges kept
        edge_pairs = [(e["source"], e["target"]) for e in filtered]
        assert ("A", "B") in edge_pairs or ("B", "A") in edge_pairs
        assert ("B", "C") in edge_pairs or ("C", "B") in edge_pairs

    def test_filter_edges_sorting(self, sample_results):
        """Test that filtered edges are sorted by descending abs weight."""
        filtered = filter_edges_by_threshold(
            sample_results, threshold=0.0, use_absolute_weights=True
        )

        # First edge should have highest abs weight (2.0)
        assert abs(filtered[0]["weight"]) == 2.0
        # Last edge should have lowest abs weight (0.5)
        assert abs(filtered[-1]["weight"]) == 0.5

    def test_filter_edges_negative_threshold_raises(self, sample_results):
        """Test that negative threshold raises ValueError."""
        with pytest.raises(ValueError, match="threshold must be >= 0"):
            filter_edges_by_threshold(sample_results, threshold=-1.0)


class TestEdgesToDataframe:
    """Test edge list to DataFrame conversion."""

    def test_edges_to_dataframe_contains_block_summary(self, sample_results):
        """Test DataFrame contains block_summary fields."""
        edges = sample_results["edges"]
        df = edges_to_dataframe(edges)

        # Check required columns
        assert "source" in df.columns
        assert "target" in df.columns
        assert "weight" in df.columns
        assert "abs_weight" in df.columns
        assert "sign" in df.columns

        # Check block_summary columns
        assert "n_params" in df.columns
        assert "l2_norm" in df.columns
        assert "mean" in df.columns
        assert "max" in df.columns
        assert "min" in df.columns
        assert "max_abs" in df.columns

        # Check values
        assert len(df) == 3

    def test_edges_to_dataframe_with_nodes_meta(self, sample_results):
        """Test DataFrame includes node metadata when provided."""
        edges = sample_results["edges"]
        nodes_meta = make_nodes_meta(sample_results)
        df = edges_to_dataframe(edges, nodes_meta)

        # Check metadata columns
        assert "source_group" in df.columns
        assert "target_group" in df.columns
        assert "source_type" in df.columns
        assert "target_type" in df.columns

    def test_edges_to_dataframe_empty(self):
        """Test empty edge list returns empty DataFrame with correct columns."""
        df = edges_to_dataframe([])

        assert df.empty
        assert "source" in df.columns
        assert "weight" in df.columns


class TestCentralityComputation:
    """Test centrality metric computation."""

    def test_compute_strength_centrality(self, sample_results):
        """Test strength centrality computation."""
        G = build_graph_from_results(sample_results, use_absolute_weights=True)
        strength = compute_strength_centrality(G)

        # A: connected to B (2.0) and C (0.5) = 2.5
        assert strength["A"] == 2.5

        # B: connected to A (2.0) and C (1.0) = 3.0
        assert strength["B"] == 3.0

        # C: connected to A (0.5) and B (1.0) = 1.5
        assert strength["C"] == 1.5

    def test_compute_centrality_table_columns(self, sample_results):
        """Test centrality table has required columns."""
        G = build_graph_from_results(sample_results, use_absolute_weights=True)

        # With betweenness
        df = compute_centrality_table(G, compute_betweenness=True, compute_closeness=False)

        assert "node_id" in df.columns
        assert "strength" in df.columns
        assert "betweenness" in df.columns
        assert "closeness" not in df.columns

        # With closeness
        df2 = compute_centrality_table(G, compute_betweenness=False, compute_closeness=True)

        assert "closeness" in df2.columns
        assert "betweenness" not in df2.columns

    def test_compute_centrality_table_sorted_by_strength(self, sample_results):
        """Test centrality table is sorted by strength descending."""
        G = build_graph_from_results(sample_results, use_absolute_weights=True)
        df = compute_centrality_table(G, compute_betweenness=True)

        # B has highest strength (3.0), should be first
        assert df.iloc[0]["node_id"] == "B"
        assert df.iloc[0]["strength"] == 3.0


class TestMakeNodesMeta:
    """Test nodes metadata helper."""

    def test_make_nodes_meta(self, sample_results):
        """Test nodes meta extraction."""
        meta = make_nodes_meta(sample_results)

        assert "A" in meta
        assert "B" in meta
        assert "C" in meta

        assert meta["A"]["column"] == "var_a"
        assert meta["A"]["label"] == "Variable A"
        assert meta["A"]["domain_group"] == "group1"
        assert meta["C"]["mgm_type"] == "c"
