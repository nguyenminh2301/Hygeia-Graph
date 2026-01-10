"""Tests for Sprint A / Agent B: Posthoc Metrics."""

import json

import pytest

from hygeia_graph.posthoc_metrics import (
    build_derived_metrics,
    compute_bridge_metrics,
    compute_expected_influence,
    compute_mst_backbone,
    compute_node_strength_abs,
    filter_edges_for_explore,
)


@pytest.fixture
def basic_results():
    """Minimal results object."""
    return {
        "analysis_id": "uuid-1234",
        "nodes": [
            {"id": "A", "domain_group": "G1"},
            {"id": "B", "domain_group": "G2"},
            {"id": "C", "domain_group": "G1"},
        ],
        "edges": [
            {"source": "A", "target": "B", "weight": 0.8, "sign": "positive"},
            {"source": "A", "target": "C", "weight": -0.2, "sign": "negative"},
        ],
    }


def test_expected_influence_signed(basic_results):
    """EI(A) should be sum of signed weights."""
    edges = basic_results["edges"]
    ei = compute_expected_influence(edges)

    # A connects to B (0.8) and C (-0.2) => 0.6
    assert ei["A"] == pytest.approx(0.6)
    # B connects to A (0.8) => 0.8
    assert ei["B"] == pytest.approx(0.8)
    # C connects to A (-0.2) => -0.2
    assert ei["C"] == pytest.approx(-0.2)


def test_strength_abs(basic_results):
    """Strength(A) should be sum of absolute weights."""
    edges = basic_results["edges"]
    strength = compute_node_strength_abs(edges)

    # A connects to B (0.8) and C (|-0.2|=0.2) => 1.0
    assert strength["A"] == pytest.approx(1.0)
    assert strength["B"] == pytest.approx(0.8)
    assert strength["C"] == pytest.approx(0.2)


def test_filter_edges_for_explore(basic_results):
    """Test filtering logic."""
    # 1. Filter by threshold 0.5, abs=True
    cfg = {"threshold": 0.5, "use_absolute_weights": True, "top_edges": None}
    filtered = filter_edges_for_explore(basic_results, cfg)
    # Should keep A-B (0.8), drop A-C (0.2 < 0.5)
    assert len(filtered) == 1
    assert filtered[0]["target"] == "B"

    # 2. Filter by threshold 0.1, top_edges=1
    cfg2 = {"threshold": 0.0, "use_absolute_weights": True, "top_edges": 1}
    filtered2 = filter_edges_for_explore(basic_results, cfg2)
    # Should keep both eligible, but top 1 is A-B (0.8 > 0.2)
    assert len(filtered2) == 1
    assert filtered2[0]["weight"] == 0.8


def test_bridge_metrics_enabled(basic_results):
    """Test bridge metrics calculation when valid groups exist."""
    # Setup nodes meta
    nodes_meta = {
        "A": {"domain_group": "G1"},
        "B": {"domain_group": "G2"},
        "C": {"domain_group": "G1"},
    }
    edges = basic_results["edges"]  # A-B (0.8), A-C (-0.2)

    bridge = compute_bridge_metrics(edges, nodes_meta)

    assert bridge["enabled"] is True
    assert "G1" in bridge["groups"]
    assert "G2" in bridge["groups"]

    # Calculate expected bridge values
    # Node A (G1):
    # - edge A-B (to G2) is cross-group. Weight 0.8.
    # - edge A-C (to G1) is within-group. Ignore.
    # Bridge Strength A = 0.8
    # Bridge EI A = 0.8
    assert bridge["bridge_strength_abs"]["A"] == pytest.approx(0.8)
    assert bridge["bridge_expected_influence"]["A"] == pytest.approx(0.8)

    # Node B (G2):
    # - edge B-A (to G1) is cross-group. Weight 0.8.
    # Bridge Strength B = 0.8
    assert bridge["bridge_strength_abs"]["B"] == pytest.approx(0.8)

    # Node C (G1):
    # - edge C-A (to G1) is within-group. Ignore.
    # Bridge Strength C = 0.0
    # Note: Depending on implementation, it might be missing or 0.0.
    # My implementation initializes all grouped nodes to 0.0.
    assert bridge["bridge_strength_abs"]["C"] == 0.0


def test_bridge_metrics_disabled_when_groups_missing():
    """Test disabling bridge metrics when groups are insufficient."""
    # Only one group
    nodes_meta = {
        "A": {"domain_group": "G1"},
        "B": {"domain_group": "G1"},
    }
    edges = []
    bridge = compute_bridge_metrics(edges, nodes_meta)
    assert bridge["enabled"] is False
    assert "Need >=2 groups" in bridge["warning"]

    # Missing groups (coverage < 80%)
    nodes_meta2 = {
        "A": {"domain_group": "G1"},
        "B": {"domain_group": None},  # Missing
        "C": {"domain_group": ""},  # Missing
    }
    bridge2 = compute_bridge_metrics(edges, nodes_meta2)
    assert bridge2["enabled"] is False
    assert "coverage" in bridge2["warning"]


def test_mst_backbone_edges():
    """Test MST backbone computation."""
    # 4 Nodes: A, B, C, D
    # Edges:
    # A-B: 0.9
    # B-C: 0.5
    # C-D: 0.2
    # A-D: 0.1
    # MST based on distance (1/abs_weight) should prefer HIGH weights.
    # Expected MST edges: A-B (0.9), B-C (0.5), C-D (0.2).
    # A-D (0.1) is weak, should be redundant if cycle A-B-C-D exists.
    # A-B-C-D path connects all.
    edges = [
        {"source": "A", "target": "B", "weight": 0.9},
        {"source": "B", "target": "C", "weight": 0.5},
        {"source": "C", "target": "D", "weight": 0.2},
        {"source": "A", "target": "D", "weight": 0.1},
    ]

    mst = compute_mst_backbone(edges)
    assert mst["enabled"] is True
    assert mst["edge_count"] == 3

    # Verify contents
    mst_weights = sorted([e["abs_weight"] for e in mst["edges"]], reverse=True)
    assert mst_weights == [0.9, 0.5, 0.2]

    # Verify connectivity (A-D shouldn't be direct if it wasn't picked)
    pairs = sorted([tuple(sorted((e["source"], e["target"]))) for e in mst["edges"]])
    assert ("A", "D") not in pairs
    assert ("C", "D") in pairs


def test_build_derived_metrics_structure(basic_results, tmp_path):
    """Test strict structure of derived metrics."""
    cfg = {"threshold": 0.0, "use_absolute_weights": True, "top_edges": None}

    derived = build_derived_metrics(basic_results, cfg)

    # Check top-level keys
    required_keys = {
        "analysis_id",
        "derived_version",
        "computed_at",
        "config",
        "node_metrics",
        "bridge",
        "mst",
        "messages",
    }
    assert required_keys.issubset(derived.keys())

    # Check config echo
    assert derived["config"]["threshold"] == 0.0

    # Check node metrics
    nm = derived["node_metrics"]
    assert "strength_abs" in nm
    assert "expected_influence" in nm
    # Should include all nodes A, B, C
    assert "A" in nm["strength_abs"]
    assert nm["strength_abs"]["A"] == 1.0

    # Serialization check
    json_str = json.dumps(derived)
    assert len(json_str) > 0
    assert "uuid-1234" in json_str
