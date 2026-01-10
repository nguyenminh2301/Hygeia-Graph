"""Unit tests for Robustness module (no R required)."""

from hygeia_graph.robustness_utils import robustness_settings_hash


def test_robustness_settings_hash_determinism():
    """Test hash function is deterministic and sensitive to changes."""
    s1 = {
        "n_boots_np": 200,
        "n_boots_case": 200,
        "n_cores": 1,
        "case_min": 0.05,
        "case_max": 0.75,
        "case_n": 10,
        "cor_level": 0.7,
    }

    h1 = robustness_settings_hash(s1, "ana-123")
    h2 = robustness_settings_hash(s1, "ana-123")
    assert h1 == h2

    # Change analysis ID
    h3 = robustness_settings_hash(s1, "ana-456")
    assert h1 != h3

    # Change specific setting
    s2 = s1.copy()
    s2["n_boots_np"] = 300
    h4 = robustness_settings_hash(s2, "ana-123")
    assert h1 != h4


def test_robustness_settings_hash_ignore_extra():
    """Test hash ignores extra/UI-only keys."""
    s1 = {"n_boots_np": 100}
    s2 = {"n_boots_np": 100, "ui_toggle": True}

    # We only assume robustness_utils uses known keys
    # If the util function explicitly filters (which it does), this should pass.

    h1 = robustness_settings_hash(s1, "id")
    h2 = robustness_settings_hash(s2, "id")
    assert h1 == h2
