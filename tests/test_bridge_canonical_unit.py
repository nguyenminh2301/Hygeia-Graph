"""Unit tests for bridge canonical metrics."""

import pytest
from unittest.mock import patch, MagicMock

from hygeia_graph.bridge_merge import merge_bridge_into_derived


class TestBridgeMerge:
    """Tests for bridge merge logic."""

    def test_merge_bridge_success(self):
        """Test merging bridge results into derived."""
        derived = {"node_metrics": {"strength": {"A": 1.0, "B": 2.0}}}

        bridge_result = {
            "status": "success",
            "method": "networktools::bridge",
            "n_communities": 2,
            "community_source": "derived",
            "computed_at": "2024-01-01T00:00:00Z",
            "metrics": {
                "bridge_strength": {"A": 0.5, "B": 0.3},
                "bridge_expected_influence": {"A": 0.2, "B": -0.1},
            },
        }

        result = merge_bridge_into_derived(derived, bridge_result)

        assert "bridge_strength_networktools" in result["node_metrics"]
        assert result["node_metrics"]["bridge_strength_networktools"]["A"] == 0.5
        assert "bridge_expected_influence_networktools" in result["node_metrics"]
        assert result["bridge"]["canonical_enabled"] is True
        assert result["bridge"]["method"] == "networktools::bridge"

    def test_merge_bridge_empty_derived(self):
        """Test merging when derived is empty."""
        bridge_result = {
            "status": "success",
            "metrics": {
                "bridge_strength": {"A": 0.5},
            },
        }

        result = merge_bridge_into_derived({}, bridge_result)

        assert "node_metrics" in result
        assert "bridge_strength_networktools" in result["node_metrics"]

    def test_merge_bridge_failed_status(self):
        """Test that failed bridge results are not merged."""
        derived = {"node_metrics": {}}

        bridge_result = {
            "status": "failed",
            "message": "No groups",
        }

        result = merge_bridge_into_derived(derived, bridge_result)

        assert "bridge_strength_networktools" not in result.get("node_metrics", {})

    def test_merge_bridge_preserves_existing(self):
        """Test that existing metrics are preserved."""
        derived = {
            "node_metrics": {
                "strength": {"A": 1.0},
                "bridge_strength": {"A": 0.8},  # Python v1 bridge
            }
        }

        bridge_result = {
            "status": "success",
            "metrics": {
                "bridge_strength": {"A": 0.5},
            },
        }

        result = merge_bridge_into_derived(derived, bridge_result)

        # Both should exist
        assert result["node_metrics"]["bridge_strength"]["A"] == 0.8  # Original
        assert result["node_metrics"]["bridge_strength_networktools"]["A"] == 0.5  # Canonical


class TestBridgeInterface:
    """Tests for bridge interface (with mocks)."""

    def test_bridge_error_attributes(self):
        """Test BridgeError exception attributes."""
        from hygeia_graph.bridge_interface import BridgeError

        err = BridgeError("Test error", code="TEST_CODE", stdout="out", stderr="err")

        assert err.message == "Test error"
        assert err.code == "TEST_CODE"
        assert err.stdout == "out"
        assert err.stderr == "err"

    def test_run_bridge_validates_input(self):
        """Test that run_bridge validates input."""
        from hygeia_graph.bridge_interface import run_bridge_subprocess

        with pytest.raises(ValueError, match="required"):
            run_bridge_subprocess(None)

        with pytest.raises(ValueError, match="status=success"):
            run_bridge_subprocess({"status": "failed"})
