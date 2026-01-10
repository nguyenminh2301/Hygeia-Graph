"""Unit tests for merge_r_posthoc_into_derived."""

import json

from hygeia_graph.posthoc_merge import merge_r_posthoc_into_derived


def test_merge_r_posthoc_none():
    """If r_posthoc is None, return derived unchanged."""
    derived = {"node_metrics": {"strength": {}}}
    result = merge_r_posthoc_into_derived(derived, None)
    assert result == derived
    assert result is not derived  # Should be a copy


def test_merge_predictability_and_communities():
    """Merge valid r_posthoc into derived."""
    derived = {"node_metrics": {"strength": {"A": 1.0}}}
    posthoc = {
        "analysis_id": "123",
        "predictability": {
            "enabled": True,
            "by_node": {"A": 0.5},
            "metric_by_node": {"A": "R2"},
            "details": {},
        },
        "communities": {"enabled": True, "membership": {"A": "1"}, "algorithm": "walktrap"},
        "messages": [{"level": "info", "code": "OK", "message": "msg"}],
    }

    result = merge_r_posthoc_into_derived(derived, posthoc)

    # Check predictability injection
    assert result["node_metrics"]["predictability"]["A"] == 0.5
    assert result["node_metrics"]["predictability_metric"]["A"] == "R2"

    # Check communities injection
    assert result["communities"]["membership"]["A"] == "1"
    assert result["communities"]["algorithm"] == "walktrap"

    # Check messages append
    assert len(result["messages"]) == 1
    assert result["messages"][0]["code"] == "OK"


def test_merge_serializable():
    """Ensure result is JSON serializable."""
    derived = {"node_metrics": {}}
    posthoc = {
        "predictability": {"enabled": True, "by_node": {"A": 0.1}, "metric_by_node": {"A": "nCC"}}
    }
    result = merge_r_posthoc_into_derived(derived, posthoc)
    assert json.dumps(result)
