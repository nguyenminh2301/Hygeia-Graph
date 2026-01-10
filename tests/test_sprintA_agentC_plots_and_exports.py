"""Tests for Sprint A / Agent C: Plots and Exports."""

import plotly.graph_objects as go
import pytest

from hygeia_graph.exports import (
    df_to_csv_bytes,
    df_to_csv_bytes_with_index,
    plot_to_html_bytes,
)
from hygeia_graph.plots import (
    build_adjacency_matrix_df,
    build_node_metrics_df,
    compute_edges_filtered_df,
    make_adjacency_heatmap,
    make_centrality_bar_plot,
)


@pytest.fixture
def sample_results():
    return {
        "analysis_id": "test-id",
        "nodes": [
            {"id": "A"},
            {"id": "B"},
            {"id": "C"},
        ],
        "edges": [
            {"source": "A", "target": "B", "weight": 0.8},
            {"source": "A", "target": "C", "weight": -0.5},
            {"source": "B", "target": "C", "weight": 0.1},
        ],
    }


@pytest.fixture
def sample_derived_metrics():
    return {
        "node_metrics": {
            "strength_abs": {"A": 1.3, "B": 0.9, "C": 0.6},
            "expected_influence": {"A": 0.3, "B": 0.9, "C": -0.4},
            "bridge_strength_abs": {"A": 0.5},
            "bridge_expected_influence": {"A": 0.5},
        }
    }


def test_build_node_metrics_df_basic(sample_derived_metrics):
    df = build_node_metrics_df(sample_derived_metrics)

    assert "node_id" in df.columns
    assert "strength_abs" in df.columns
    assert "expected_influence" in df.columns
    assert "bridge_strength_abs" in df.columns

    # Check values
    row_a = df[df["node_id"] == "A"].iloc[0]
    assert row_a["strength_abs"] == 1.3
    assert row_a["bridge_strength_abs"] == 0.5

    # Check sorting
    assert df.iloc[0]["strength_abs"] >= df.iloc[1]["strength_abs"]


def test_edges_filtered_df_threshold_and_topN(sample_results):
    # Threshold 0.6 => only A-B (0.8)
    cfg = {"threshold": 0.6, "use_absolute_weights": True}
    df = compute_edges_filtered_df(sample_results, cfg)
    assert len(df) == 1
    assert df.iloc[0]["source"] == "A"
    assert df.iloc[0]["target"] == "B"

    # Top 2 by abs weight => A-B (0.8), A-C (0.5), B-C (0.1) is excluded
    cfg2 = {"threshold": 0.0, "use_absolute_weights": True, "top_edges": 2}
    df2 = compute_edges_filtered_df(sample_results, cfg2)
    assert len(df2) == 2
    weights = sorted(df2["abs_weight"].tolist(), reverse=True)
    assert weights == [0.8, 0.5]


def test_adjacency_matrix_is_symmetric(sample_results):
    cfg = {"threshold": 0.0, "use_absolute_weights": True}
    df = build_adjacency_matrix_df(sample_results, cfg, value_mode="signed")

    # Check symmetry
    assert df.at["A", "B"] == df.at["B", "A"]
    assert df.at["A", "B"] == 0.8
    # Diagonal should be 0
    assert df.at["A", "A"] == 0.0

    # Check abs mode
    df_abs = build_adjacency_matrix_df(sample_results, cfg, value_mode="abs")
    assert df_abs.at["A", "C"] == 0.5  # |-0.5|


def test_plot_objects_created(sample_derived_metrics, sample_results):
    # Centrality
    nm_df = build_node_metrics_df(sample_derived_metrics)
    fig_bar = make_centrality_bar_plot(nm_df, "expected_influence")
    assert isinstance(fig_bar, go.Figure)

    # Heatmap
    cfg = {"threshold": 0.0, "use_absolute_weights": True}
    adj_df = build_adjacency_matrix_df(sample_results, cfg)
    fig_heat = make_adjacency_heatmap(adj_df)
    assert isinstance(fig_heat, go.Figure)


def test_dataframe_to_csv_bytes(sample_derived_metrics):
    df = build_node_metrics_df(sample_derived_metrics)
    csv_bytes = df_to_csv_bytes(df)
    assert isinstance(csv_bytes, bytes)
    # Check content roughly
    assert b"node_id,strength_abs" in csv_bytes
    assert b"A,1.3" in csv_bytes


def test_adjacency_to_csv_bytes_with_index(sample_results):
    cfg = {"threshold": 0.0, "use_absolute_weights": True}
    df = build_adjacency_matrix_df(sample_results, cfg)
    csv_bytes = df_to_csv_bytes_with_index(df)
    # Header should have column names (A,B,C)
    # First line usually: ,A,B,C if index name is empty, or index_name,A,B,C
    assert b"A,B,C" in csv_bytes
    # Row start
    assert b"A,0.0,0.8,-0.5" in csv_bytes


def test_plot_to_html_export(sample_derived_metrics):
    nm_df = build_node_metrics_df(sample_derived_metrics)
    fig = make_centrality_bar_plot(nm_df, "strength_abs")
    html_bytes = plot_to_html_bytes(fig)
    assert html_bytes.startswith(b"<!DOCTYPE html>") or b"plotly" in html_bytes
