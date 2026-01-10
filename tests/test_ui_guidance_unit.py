"""Unit tests for UI guidance module."""

import pytest

from hygeia_graph.ui_guidance import (
    DATA_FORMAT_SHORT,
    DATA_FORMAT_DETAILS,
    MODEL_SETTINGS_HINTS,
    EXPLORE_HINTS,
    PAGE_ORDER,
    get_next_page,
    get_prev_page,
    can_proceed_to_next,
    get_workflow_status,
    get_hint,
)


class TestGuidanceContent:
    """Tests for guidance content."""

    def test_data_format_short_non_empty(self):
        """Test that short format guidance exists."""
        assert len(DATA_FORMAT_SHORT) > 100
        assert "CSV" in DATA_FORMAT_SHORT
        assert "Missing" in DATA_FORMAT_SHORT

    def test_data_format_details_non_empty(self):
        """Test that detailed format guidance exists."""
        assert len(DATA_FORMAT_DETAILS) > 200
        assert "Gaussian" in DATA_FORMAT_DETAILS

    def test_model_hints_exist(self):
        """Test that model settings hints exist."""
        assert "ebic_gamma" in MODEL_SETTINGS_HINTS
        assert "alpha" in MODEL_SETTINGS_HINTS

    def test_explore_hints_exist(self):
        """Test that explore hints exist."""
        assert "threshold" in EXPLORE_HINTS
        assert "top_edges" in EXPLORE_HINTS


class TestNavigation:
    """Tests for navigation helpers."""

    def test_page_order_complete(self):
        """Test that page order has all pages."""
        assert len(PAGE_ORDER) == 5
        assert "Data & Schema" in PAGE_ORDER
        assert "Report & Export" in PAGE_ORDER

    def test_get_next_page(self):
        """Test getting next page."""
        assert get_next_page("Data & Schema") == "Model Settings"
        assert get_next_page("Run MGM") == "Explore"
        assert get_next_page("Report & Export") is None

    def test_get_prev_page(self):
        """Test getting previous page."""
        assert get_prev_page("Model Settings") == "Data & Schema"
        assert get_prev_page("Data & Schema") is None

    def test_get_next_page_invalid(self):
        """Test invalid page returns None."""
        assert get_next_page("Invalid Page") is None


class TestWorkflowStatus:
    """Tests for workflow status checks."""

    def test_can_proceed_data_schema(self):
        """Test Data & Schema can proceed check."""
        assert can_proceed_to_next("Data & Schema", {"schema_obj": {}})
        assert not can_proceed_to_next("Data & Schema", {})

    def test_can_proceed_model_settings(self):
        """Test Model Settings can proceed check."""
        assert can_proceed_to_next("Model Settings", {"model_spec_obj": {}})
        assert not can_proceed_to_next("Model Settings", {})

    def test_can_proceed_run_mgm(self):
        """Test Run MGM can proceed check."""
        assert can_proceed_to_next("Run MGM", {"results_json": {"status": "success"}})
        assert not can_proceed_to_next("Run MGM", {"results_json": {"status": "failed"}})

    def test_get_workflow_status(self):
        """Test workflow status dict."""
        status = get_workflow_status({
            "schema_obj": {},
            "model_spec_obj": None,
            "results_json": None,
        })

        assert status["Data & Schema"] is True
        assert status["Model Settings"] is False


class TestHints:
    """Tests for hint retrieval."""

    def test_get_valid_hint(self):
        """Test getting a valid hint."""
        hint = get_hint("model", "ebic_gamma")
        assert len(hint) > 0
        assert "0.5" in hint

    def test_get_invalid_hint(self):
        """Test getting invalid hint returns empty."""
        assert get_hint("invalid", "key") == ""
        assert get_hint("model", "invalid_key") == ""
