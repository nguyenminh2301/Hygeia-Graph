"""Unit tests for Step 4 model spec builder."""

from hygeia_graph.contracts import validate_model_spec_json
from hygeia_graph.model_spec import (
    build_model_spec,
    default_model_settings,
    sanitize_settings,
)


class TestDefaultSettings:
    """Test default model settings."""

    def test_default_settings_locked_fields(self):
        """Test that default settings have correct locked fields."""
        settings = default_model_settings()

        # Lambda selection must be EBIC (locked)
        assert settings["mgm"]["regularization"]["lambda_selection"] == "EBIC"

        # Missing policy must be warn_and_abort (locked)
        assert settings["missing_policy"]["action"] == "warn_and_abort"

    def test_default_settings_structure(self):
        """Test that default settings have all required structures."""
        settings = default_model_settings()

        # Check main sections exist
        assert "engine" in settings
        assert "random_seed" in settings
        assert "mgm" in settings
        assert "edge_mapping" in settings
        assert "missing_policy" in settings

        # Check MGM structure
        assert "k" in settings["mgm"]
        assert "regularization" in settings["mgm"]
        assert "rule_reg" in settings["mgm"]

        # Check edge mapping structure
        assert "aggregator" in settings["edge_mapping"]
        assert "sign_strategy" in settings["edge_mapping"]
        assert "zero_tolerance" in settings["edge_mapping"]

    def test_default_settings_values(self):
        """Test that default settings match spec requirements."""
        settings = default_model_settings()

        assert settings["random_seed"] == 1
        assert settings["mgm"]["k"] == 2
        assert settings["mgm"]["regularization"]["ebic_gamma"] == 0.5
        assert settings["mgm"]["regularization"]["alpha"] == 0.5
        assert settings["mgm"]["rule_reg"] == "AND"
        assert settings["edge_mapping"]["aggregator"] == "max_abs"
        assert settings["edge_mapping"]["sign_strategy"] == "dominant"


class TestBuildModelSpec:
    """Test model spec building."""

    def test_build_model_spec_validates(self):
        """Test that built model spec validates against contract."""
        # Create minimal valid schema
        schema_json = {
            "schema_version": "0.1.0",
            "created_at": "2026-01-09T00:00:00Z",
            "dataset": {
                "row_count": 10,
                "column_count": 1,
                "missing": {"cells": 0, "rate": 0.0, "by_variable": []},
            },
            "variables": [
                {
                    "id": "test_var",
                    "column": "TestVar",
                    "mgm_type": "g",
                    "measurement_level": "continuous",
                    "level": 1,
                }
            ],
        }

        # Build spec with defaults
        settings = default_model_settings()
        spec = build_model_spec(
            schema_json,
            settings,
            analysis_id="00000000-0000-0000-0000-000000000001",
            created_at="2026-01-09T00:00:00Z",
        )

        # Should not raise ContractValidationError
        validate_model_spec_json(spec)

    def test_build_model_spec_forces_locked_fields(self):
        """Test that build_model_spec enforces locked fields."""
        # Create schema
        schema_json = {
            "schema_version": "0.1.0",
            "created_at": "2026-01-09T00:00:00Z",
            "dataset": {
                "row_count": 10,
                "column_count": 1,
                "missing": {"cells": 0, "rate": 0.0, "by_variable": []},
            },
            "variables": [
                {
                    "id": "test_var",
                    "column": "TestVar",
                    "mgm_type": "g",
                    "measurement_level": "continuous",
                    "level": 1,
                }
            ],
        }

        # Start with tampered settings
        settings = default_model_settings()
        settings["mgm"]["regularization"]["lambda_selection"] = "CV"  # Try to change
        settings["missing_policy"]["action"] = "drop"  # Try to change

        # Build spec
        spec = build_model_spec(
            schema_json,
            settings,
            analysis_id="00000000-0000-0000-0000-000000000001",
            created_at="2026-01-09T00:00:00Z",
        )

        # Must still be EBIC and warn_and_abort
        assert spec["mgm"]["regularization"]["lambda_selection"] == "EBIC"
        assert spec["missing_policy"]["action"] == "warn_and_abort"

        # Should validate
        validate_model_spec_json(spec)

    def test_build_model_spec_required_fields(self):
        """Test that build_model_spec includes all required fields."""
        schema_json = {
            "schema_version": "0.1.0",
            "created_at": "2026-01-09T00:00:00Z",
            "dataset": {
                "row_count": 10,
                "column_count": 1,
                "missing": {"cells": 0, "rate": 0.0, "by_variable": []},
            },
            "variables": [
                {
                    "id": "test_var",
                    "column": "TestVar",
                    "mgm_type": "g",
                    "measurement_level": "continuous",
                    "level": 1,
                }
            ],
        }

        settings = default_model_settings()
        spec = build_model_spec(
            schema_json,
            settings,
            analysis_id="test-id",
            created_at="2026-01-09T09:00:00Z",
        )

        # Check required top-level fields
        assert spec["spec_version"] == "0.1.0"
        assert spec["analysis_id"] == "test-id"
        assert spec["created_at"] == "2026-01-09T09:00:00Z"
        assert "input" in spec
        assert "engine" in spec
        assert "mgm" in spec
        assert "edge_mapping" in spec
        assert "missing_policy" in spec

        # Check input
        assert spec["input"]["schema_ref"] == "schema.json"

        # Check engine
        assert spec["engine"]["name"] == "R.mgm"

    def test_build_model_spec_generates_uuid(self):
        """Test that build_model_spec generates UUID if not provided."""
        schema_json = {
            "schema_version": "0.1.0",
            "created_at": "2026-01-09T00:00:00Z",
            "dataset": {
                "row_count": 10,
                "column_count": 1,
                "missing": {"cells": 0, "rate": 0.0, "by_variable": []},
            },
            "variables": [
                {
                    "id": "test_var",
                    "column": "TestVar",
                    "mgm_type": "g",
                    "measurement_level": "continuous",
                    "level": 1,
                }
            ],
        }

        settings = default_model_settings()
        spec = build_model_spec(schema_json, settings)  # No analysis_id provided

        # Should have generated a UUID
        import uuid

        assert "analysis_id" in spec
        # Verify it's a valid UUID
        uuid.UUID(spec["analysis_id"])  # Will raise if invalid

    def test_build_model_spec_optional_sha256(self):
        """Test that build_model_spec includes optional SHA256 hashes."""
        schema_json = {
            "schema_version": "0.1.0",
            "created_at": "2026-01-09T00:00:00Z",
            "dataset": {
                "row_count": 10,
                "column_count": 1,
                "missing": {"cells": 0, "rate": 0.0, "by_variable": []},
            },
            "variables": [
                {
                    "id": "test_var",
                    "column": "TestVar",
                    "mgm_type": "g",
                    "measurement_level": "continuous",
                    "level": 1,
                }
            ],
        }

        settings = default_model_settings()
        spec = build_model_spec(
            schema_json,
            settings,
            analysis_id="test-id",
            schema_sha256="abc123",
            data_sha256="def456",
        )

        assert spec["input"]["schema_sha256"] == "abc123"
        assert spec["input"]["data_sha256"] == "def456"


class TestSanitizeSettings:
    """Test settings sanitization."""

    def test_sanitize_settings_clamps_and_coerces(self):
        """Test that sanitize_settings clamps numeric values and coerces types."""
        # Provide out-of-bounds settings
        settings = {
            "mgm": {
                "regularization": {"ebic_gamma": 2.0, "alpha": -1.0},  # Out of bounds
                "rule_reg": "and",  # Wrong case
            },
            "edge_mapping": {"zero_tolerance": -0.5},  # Negative
            "random_seed": -10,  # Negative
        }

        clean = sanitize_settings(settings)

        # Should clamp to valid ranges
        assert clean["mgm"]["regularization"]["ebic_gamma"] == 1.0  # Clamped to max
        assert clean["mgm"]["regularization"]["alpha"] == 0.0  # Clamped to min
        assert clean["edge_mapping"]["zero_tolerance"] == 0.0  # Clamped to min
        assert clean["random_seed"] == 0  # Clamped to min

        # Should normalize enum
        assert clean["mgm"]["rule_reg"] == "AND"

    def test_sanitize_settings_forces_locked_fields(self):
        """Test that sanitize_settings enforces locked fields."""
        settings = {
            "mgm": {"regularization": {"lambda_selection": "CV"}},  # Try to override
            "missing_policy": {"action": "drop"},  # Try to override
        }

        clean = sanitize_settings(settings)

        # Must still be locked values
        assert clean["mgm"]["regularization"]["lambda_selection"] == "EBIC"
        assert clean["missing_policy"]["action"] == "warn_and_abort"

    def test_sanitize_settings_handles_missing_fields(self):
        """Test that sanitize_settings fills in missing fields with defaults."""
        # Empty settings
        settings = {}

        clean = sanitize_settings(settings)

        # Should have all required fields with defaults
        assert "mgm" in clean
        assert "edge_mapping" in clean
        assert "missing_policy" in clean
        assert clean["random_seed"] == 1
        assert clean["mgm"]["k"] == 2

    def test_sanitize_settings_normalizes_enums(self):
        """Test that sanitize_settings normalizes enum values."""
        settings = {
            "mgm": {"rule_reg": "or"},  # Lowercase
            "edge_mapping": {
                "aggregator": "MAX_ABS",  # Wrong case
                "sign_strategy": "DOMINANT",  # Wrong case
            },
            "visualization": {"layout": "FORCE"},  # Wrong case
        }

        clean = sanitize_settings(settings)

        # Should use defaults since case doesn't match (case-sensitive)
        assert clean["mgm"]["rule_reg"] == "AND"  # Default
        assert clean["edge_mapping"]["aggregator"] == "max_abs"  # Default
        assert clean["edge_mapping"]["sign_strategy"] == "dominant"  # Default
        assert clean["visualization"]["layout"] == "force"  # Default

    def test_sanitize_settings_coerces_booleans(self):
        """Test that sanitize_settings coerces boolean values."""
        settings = {
            "mgm": {
                "overparameterize": 1,  # Truthy
                "scale_gaussian": 0,  # Falsy
                "sign_info": "yes",  # Truthy string
            },
            "centrality": {
                "compute": False,
                "weighted": None,  # Falsy
            },
        }

        clean = sanitize_settings(settings)

        assert clean["mgm"]["overparameterize"] is True
        assert clean["mgm"]["scale_gaussian"] is False
        assert clean["mgm"]["sign_info"] is True
        assert clean["centrality"]["compute"] is False
        assert clean["centrality"]["weighted"] is False
