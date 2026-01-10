"""Unit tests for intervention v2 module."""

import pytest
from unittest.mock import patch

from hygeia_graph.intervention_v2_interface import (
    InterventionV2Error,
)


class TestInterventionV2Interface:
    """Tests for intervention v2 interface."""

    def test_error_attributes(self):
        """Test InterventionV2Error exception attributes."""
        err = InterventionV2Error(
            "Test error", code="TEST_CODE", stdout="out", stderr="err"
        )

        assert err.message == "Test error"
        assert err.code == "TEST_CODE"
        assert err.stdout == "out"
        assert err.stderr == "err"

    def test_validates_model_rds_path_empty(self):
        """Test that empty model_rds_path raises ValueError."""
        from hygeia_graph.intervention_v2_interface import run_intervention_v2_subprocess

        with pytest.raises(ValueError, match="model_rds_path"):
            run_intervention_v2_subprocess(
                model_rds_path="",
                data_path="/tmp/data.csv",
                schema_json={"variables": []},
                intervene_node="A",
            )

    @patch("pathlib.Path.exists")
    def test_validates_data_path_empty(self, mock_exists):
        """Test that empty data_path raises ValueError."""
        from hygeia_graph.intervention_v2_interface import run_intervention_v2_subprocess

        # Make model_rds exist, data not exist
        mock_exists.side_effect = lambda: True

        with pytest.raises(ValueError, match="data_path"):
            run_intervention_v2_subprocess(
                model_rds_path="/tmp/model.rds",
                data_path="",
                schema_json={"variables": []},
                intervene_node="A",
            )

    @patch("pathlib.Path.exists")
    def test_validates_schema_json(self, mock_exists):
        """Test that None schema_json raises ValueError."""
        from hygeia_graph.intervention_v2_interface import run_intervention_v2_subprocess

        mock_exists.return_value = True

        with pytest.raises(ValueError, match="schema_json"):
            run_intervention_v2_subprocess(
                model_rds_path="/tmp/model.rds",
                data_path="/tmp/data.csv",
                schema_json=None,
                intervene_node="A",
            )

    @patch("pathlib.Path.exists")
    def test_validates_intervene_node(self, mock_exists):
        """Test that empty intervene_node raises ValueError."""
        from hygeia_graph.intervention_v2_interface import run_intervention_v2_subprocess

        mock_exists.return_value = True

        with pytest.raises(ValueError, match="intervene_node"):
            run_intervention_v2_subprocess(
                model_rds_path="/tmp/model.rds",
                data_path="/tmp/data.csv",
                schema_json={"variables": []},
                intervene_node="",
            )
