"""Unit tests for Insights Report generator."""

from hygeia_graph.insights_report import build_report_payload, render_report_markdown
from hygeia_graph.insights_report_utils import report_settings_hash


def test_payload_minimal_required_keys():
    """Test payload generation with minimal inputs."""
    results = {
        "analysis_id": "test-123",
        "nodes": [{"id": "A"}, {"id": "B"}],
        "edges": [{"source": "A", "target": "B", "weight": 0.5}],
    }

    # Minimal derived structure (usually Agent B provides this)
    derived = {
        "node_metrics": {
            "strength_abs": {"A": 0.5, "B": 0.5},
            "expected_influence": {"A": 0.5, "B": 0.5},
        }
    }

    settings = {"top_n": 5, "style": "paper"}

    payload = build_report_payload(
        results_json=results, derived_metrics_json=derived, settings=settings
    )

    assert payload["analysis_id"] == "test-123"
    assert payload["inputs_present"]["predictability"] is False
    assert payload["inputs_present"]["communities"] is False

    # Check rankings info
    ranks = payload["rankings"]
    assert len(ranks["top_strength_abs"]) == 2
    assert ranks["top_strength_abs"][0]["node"] in ["A", "B"]


def test_markdown_contains_disclaimer_and_sections():
    """Test markdown rendering integrity."""
    payload = {
        "analysis_id": "test",
        "generated_at": "2025-01-01",
        "inputs_present": {
            "predictability": False,
            "communities": False,
            "bootnet": False,
            "nct": False,
        },
        "key_numbers": {"n_nodes": 10, "n_edges_total": 5, "threshold": 0.0},
        "rankings": {
            "top_strength_abs": [],
            "top_expected_influence": [],
            "top_predictability": [],
        },
        "communities": {},
        "robustness": {},
        "comparison": {},
        "settings": {},
        "messages": [],
    }

    md = render_report_markdown(payload, style="paper")

    assert "Disclaimer (Research Tool Only)" in md
    assert "Network Structure Overview" in md
    assert "Key Centrality Metrics" in md

    # Optional sections should be absent
    assert "Community Detection" not in md
    assert "Stability & Robustness" not in md


def test_settings_hash_deterministic():
    """Ensure settings hashing is stable."""
    s1 = {"style": "paper", "top_n": 10}
    id1 = "ana-1"

    h1 = report_settings_hash(s1, id1)
    h2 = report_settings_hash(s1, id1)

    assert h1 == h2

    # Change order shouldn't matter due to sort_keys=True
    # But json.dumps keys sort handles that.
    # Just ensure ID change = diff hash
    h3 = report_settings_hash(s1, "ana-2")
    assert h1 != h3
