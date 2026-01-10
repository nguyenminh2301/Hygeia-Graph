"""Unit tests for heavy module guardrails."""

import pytest

from hygeia_graph.heavy_guardrails import (
    clamp_int,
    clamp_float,
    normalize_bootnet_settings,
    normalize_nct_settings,
    normalize_lasso_settings,
    should_require_advanced_unlock,
    render_messages_to_markdown,
    BOOTNET_SAFE_MAX_BOOTS,
    BOOTNET_HARD_MAX_BOOTS,
    NCT_SAFE_MAX_PERMS,
    NCT_HARD_MAX_PERMS,
    LASSO_SAFE_MAX_NFOLDS,
    LASSO_SAFE_MAX_FEATURES,
    LASSO_HARD_MAX_NFOLDS,
    LASSO_HARD_MAX_FEATURES,
)


class TestClampFunctions:
    """Tests for clamp utilities."""

    def test_clamp_int_within_range(self):
        assert clamp_int(5, 0, 10) == 5

    def test_clamp_int_below(self):
        assert clamp_int(-5, 0, 10) == 0

    def test_clamp_int_above(self):
        assert clamp_int(15, 0, 10) == 10

    def test_clamp_float_within_range(self):
        assert clamp_float(0.5, 0.0, 1.0) == 0.5

    def test_clamp_float_above(self):
        assert clamp_float(1.5, 0.0, 1.0) == 1.0


class TestBootnetNormalization:
    """Tests for bootnet guardrails."""

    def test_clamp_without_unlock(self):
        """Test clamping to safe limits without unlock."""
        raw = {"n_boots_np": 2000, "n_boots_case": 900, "n_cores": 2}
        norm, msgs = normalize_bootnet_settings(raw, advanced_unlocked=False)

        assert norm["n_boots_np"] == BOOTNET_SAFE_MAX_BOOTS  # 500
        assert norm["n_boots_case"] == BOOTNET_SAFE_MAX_BOOTS  # 500
        assert norm["n_cores"] == 1
        assert len(msgs) >= 1
        assert any("CLAMPED" in m["code"] for m in msgs)

    def test_advanced_allows_higher_but_hard_clamped(self):
        """Test advanced mode allows higher values but respects hard max."""
        raw = {"n_boots_np": 3000, "n_boots_case": 900, "n_cores": 5}
        norm, msgs = normalize_bootnet_settings(raw, advanced_unlocked=True)

        assert norm["n_boots_np"] == BOOTNET_HARD_MAX_BOOTS  # 2000
        assert norm["n_boots_case"] == 900  # Within hard max
        assert norm["n_cores"] == 2  # Hard max

    def test_case_range_validation(self):
        """Test caseMin/caseMax validation."""
        raw = {"n_boots_np": 100, "caseMin": 0.8, "caseMax": 0.3}
        norm, msgs = normalize_bootnet_settings(raw, advanced_unlocked=False)

        # Should reset to defaults
        assert norm["caseMin"] == 0.25
        assert norm["caseMax"] == 0.75
        assert any("CASE_RANGE" in m["code"] for m in msgs)


class TestNCTNormalization:
    """Tests for NCT guardrails."""

    def test_edge_tests_auto_disable(self):
        """Test edge tests auto-disabled when expensive."""
        raw = {"permutations": 500, "edge_tests": True, "n_cores": 1}
        norm, msgs = normalize_nct_settings(raw, advanced_unlocked=False)

        assert norm["edge_tests"] is False
        assert any("EDGE_TESTS_DISABLED" in m["code"] for m in msgs)

    def test_clamp_permutations_without_unlock(self):
        """Test permutations clamped to safe max."""
        raw = {"permutations": 5000, "n_cores": 1}
        norm, msgs = normalize_nct_settings(raw, advanced_unlocked=False)

        assert norm["permutations"] == NCT_SAFE_MAX_PERMS  # 500

    def test_advanced_allows_hard_max(self):
        """Test advanced mode allows up to hard max."""
        raw = {"permutations": 5000, "n_cores": 1}
        norm, msgs = normalize_nct_settings(raw, advanced_unlocked=True)

        assert norm["permutations"] == NCT_HARD_MAX_PERMS  # 5000

    def test_invalid_mode_reset(self):
        """Test invalid mode reset to auto."""
        raw = {"permutations": 100, "mode": "invalid_mode"}
        norm, msgs = normalize_nct_settings(raw)

        assert norm["mode"] == "auto"
        assert any("MODE_INVALID" in m["code"] for m in msgs)


class TestLASSONormalization:
    """Tests for LASSO guardrails."""

    def test_clamp_without_unlock(self):
        """Test clamping to safe limits."""
        raw = {"nfolds": 50, "max_features": 1000}
        norm, msgs = normalize_lasso_settings(raw, advanced_unlocked=False)

        assert norm["nfolds"] == LASSO_SAFE_MAX_NFOLDS  # 10
        assert norm["max_features"] == LASSO_SAFE_MAX_FEATURES  # 100

    def test_advanced_allows_hard_max(self):
        """Test advanced mode allows hard max."""
        raw = {"nfolds": 50, "max_features": 1000}
        norm, msgs = normalize_lasso_settings(raw, advanced_unlocked=True)

        assert norm["nfolds"] == LASSO_HARD_MAX_NFOLDS  # 20
        assert norm["max_features"] == LASSO_HARD_MAX_FEATURES  # 300

    def test_high_dimension_warning(self):
        """Test warning for high dimensionality."""
        raw = {"nfolds": 5, "max_features": 30}
        norm, msgs = normalize_lasso_settings(raw, advanced_unlocked=False, n_rows=120, n_cols=800)

        assert any("HIGH_DIMENSION" in m["code"] for m in msgs)


class TestShouldRequireAdvanced:
    """Tests for advanced unlock detection."""

    def test_bootnet_needs_unlock(self):
        assert should_require_advanced_unlock("bootnet", {"n_boots_np": 600, "n_boots_case": 100})

    def test_bootnet_no_unlock_needed(self):
        assert not should_require_advanced_unlock(
            "bootnet", {"n_boots_np": 200, "n_boots_case": 200}
        )

    def test_nct_edge_tests_needs_unlock(self):
        assert should_require_advanced_unlock("nct", {"permutations": 300, "edge_tests": True})

    def test_lasso_high_features_needs_unlock(self):
        assert should_require_advanced_unlock("lasso", {"max_features": 150})


class TestRenderMessages:
    """Tests for message rendering."""

    def test_empty_messages(self):
        assert render_messages_to_markdown([]) == ""

    def test_warning_message(self):
        msgs = [{"level": "warning", "code": "TEST", "message": "Test warning"}]
        md = render_messages_to_markdown(msgs)
        assert "⚠️" in md
        assert "TEST" in md

    def test_info_message(self):
        msgs = [{"level": "info", "code": "INFO", "message": "Info message"}]
        md = render_messages_to_markdown(msgs)
        assert "ℹ️" in md
