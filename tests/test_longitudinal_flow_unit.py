"""Unit tests for longitudinal flow module."""

import pandas as pd

from hygeia_graph.longitudinal_flow import (
    build_sankey_nodes_links,
    build_transition_table,
    detect_longitudinal_pairs,
    figure_to_html,
    make_sankey_figure,
    validate_pair_data,
)


class TestDetectLongitudinalPairs:
    """Tests for pair detection."""

    def test_detect_t1_t2_suffix(self):
        """Test detection of _T1/_T2 suffix pairs."""
        df = pd.DataFrame(
            {
                "Age": [30, 40],
                "Symptom_T1": ["Mild", "Severe"],
                "Symptom_T2": ["Severe", "Mild"],
                "Other": [1, 2],
            }
        )

        pairs = detect_longitudinal_pairs(df)

        assert len(pairs) == 1
        assert pairs[0]["base"] == "Symptom"
        assert pairs[0]["t1"] == "Symptom_T1"
        assert pairs[0]["t2"] == "Symptom_T2"

    def test_detect_multiple_pairs(self):
        """Test detection of multiple pairs."""
        df = pd.DataFrame(
            {
                "A_T1": [1, 2],
                "A_T2": [2, 3],
                "B_T1": [3, 4],
                "B_T2": [4, 5],
            }
        )

        pairs = detect_longitudinal_pairs(df)

        assert len(pairs) == 2
        bases = [p["base"] for p in pairs]
        assert "A" in bases
        assert "B" in bases

    def test_detect_no_pairs(self):
        """Test when no pairs exist."""
        df = pd.DataFrame(
            {
                "A": [1, 2],
                "B": [3, 4],
            }
        )

        pairs = detect_longitudinal_pairs(df)

        assert len(pairs) == 0


class TestValidatePairData:
    """Tests for pair validation."""

    def test_valid_pair(self):
        """Test validation of valid pair."""
        df = pd.DataFrame(
            {
                "Symptom_T1": ["Mild", "Severe", "Mild"],
                "Symptom_T2": ["Severe", "Mild", "Severe"],
            }
        )

        result = validate_pair_data(df, {"base": "Symptom", "t1": "Symptom_T1", "t2": "Symptom_T2"})

        assert result["ok"] is True
        assert len(result["warnings"]) == 0

    def test_too_many_unique_values(self):
        """Test warning for high cardinality."""
        df = pd.DataFrame(
            {
                "Score_T1": list(range(50)),
                "Score_T2": list(range(50)),
            }
        )

        result = validate_pair_data(
            df,
            {"base": "Score", "t1": "Score_T1", "t2": "Score_T2"},
            max_unique=30,
        )

        assert result["ok"] is False
        assert len(result["warnings"]) >= 1


class TestBuildTransitionTable:
    """Tests for transition table building."""

    def test_counts_correct(self):
        """Test transition counts are correct."""
        df = pd.DataFrame(
            {
                "T1": ["A", "A", "B", "A"],
                "T2": ["B", "B", "A", "A"],
            }
        )

        result = build_transition_table(df, "T1", "T2")

        assert "source" in result.columns
        assert "target" in result.columns
        assert "count" in result.columns

        # A -> B appears twice
        ab_row = result[(result["source"] == "A") & (result["target"] == "B")]
        assert len(ab_row) == 1
        assert ab_row["count"].values[0] == 2

        # A -> A appears once
        aa_row = result[(result["source"] == "A") & (result["target"] == "A")]
        assert len(aa_row) == 1
        assert aa_row["count"].values[0] == 1


class TestBuildSankeyNodesLinks:
    """Tests for Sankey data structure."""

    def test_nodes_links_structure(self):
        """Test nodes and links have correct structure."""
        transitions_df = pd.DataFrame(
            {
                "source": ["A", "A", "B"],
                "target": ["B", "A", "B"],
                "count": [5, 3, 2],
            }
        )

        result = build_sankey_nodes_links(transitions_df)

        assert "nodes" in result
        assert "links" in result
        assert "label" in result["nodes"]
        assert "source" in result["links"]
        assert "target" in result["links"]
        assert "value" in result["links"]

        # Check indices are valid
        n_nodes = len(result["nodes"]["label"])
        for idx in result["links"]["source"]:
            assert 0 <= idx < n_nodes
        for idx in result["links"]["target"]:
            assert 0 <= idx < n_nodes


class TestMakeSankeyFigure:
    """Tests for Sankey figure creation."""

    def test_figure_created(self):
        """Test that figure is created successfully."""
        nodes_links = {
            "nodes": {"label": ["T1: A", "T1: B", "T2: A", "T2: B"]},
            "links": {
                "source": [0, 1],
                "target": [2, 3],
                "value": [5, 3],
            },
        }

        fig = make_sankey_figure(nodes_links, title="Test Flow")

        assert fig is not None
        assert hasattr(fig, "to_html")


class TestFigureToHtml:
    """Tests for HTML export."""

    def test_html_contains_required_elements(self):
        """Test that HTML contains plotly elements."""
        nodes_links = {
            "nodes": {"label": ["T1: A", "T2: B"]},
            "links": {"source": [0], "target": [1], "value": [10]},
        }
        fig = make_sankey_figure(nodes_links)

        html = figure_to_html(fig)

        assert "<html" in html.lower()
        assert "plotly" in html.lower()
