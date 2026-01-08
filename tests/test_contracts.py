"""Unit tests for contract validation."""

from pathlib import Path

import pytest

from hygeia_graph.contracts import (
    ContractValidationError,
    find_repo_root,
    load_json,
    load_schema,
    validate_file,
    validate_model_spec_json,
    validate_results_json,
    validate_schema_json,
)

# Get fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestSchemaValidation:
    """Test schema.json validation."""

    def test_valid_minimal_schema(self):
        """Test that minimal valid schema passes validation."""
        schema_path = FIXTURES_DIR / "schema_min.json"
        obj = load_json(schema_path)
        validate_schema_json(obj)  # Should not raise

    def test_invalid_additional_property(self):
        """Test that additional properties are rejected."""
        obj = load_json(FIXTURES_DIR / "schema_min.json")
        obj["extra_field"] = "not allowed"

        with pytest.raises(ContractValidationError) as exc_info:
            validate_schema_json(obj)

        assert exc_info.value.kind == "schema"
        assert len(exc_info.value.errors) > 0

    def test_missing_required_field(self):
        """Test that missing required field is rejected."""
        obj = load_json(FIXTURES_DIR / "schema_min.json")
        del obj["variables"]

        with pytest.raises(ContractValidationError) as exc_info:
            validate_schema_json(obj)

        assert exc_info.value.kind == "schema"
        assert any("variables" in err["message"].lower() for err in exc_info.value.errors)

    def test_invalid_version_format(self):
        """Test that invalid version format is rejected."""
        obj = load_json(FIXTURES_DIR / "schema_min.json")
        obj["schema_version"] = "invalid-version"

        with pytest.raises(ContractValidationError) as exc_info:
            validate_schema_json(obj)

        assert exc_info.value.kind == "schema"


class TestModelSpecValidation:
    """Test model_spec.json validation."""

    def test_valid_minimal_model_spec(self):
        """Test that minimal valid model_spec passes validation."""
        spec_path = FIXTURES_DIR / "model_spec_min.json"
        obj = load_json(spec_path)
        validate_model_spec_json(obj)  # Should not raise

    def test_invalid_additional_property(self):
        """Test that additional properties are rejected."""
        obj = load_json(FIXTURES_DIR / "model_spec_min.json")
        obj["unexpected"] = "field"

        with pytest.raises(ContractValidationError) as exc_info:
            validate_model_spec_json(obj)

        assert exc_info.value.kind == "model_spec"

    def test_missing_missing_policy(self):
        """Test that missing missing_policy is rejected."""
        obj = load_json(FIXTURES_DIR / "model_spec_min.json")
        del obj["missing_policy"]

        with pytest.raises(ContractValidationError) as exc_info:
            validate_model_spec_json(obj)

        assert exc_info.value.kind == "model_spec"
        assert any("missing_policy" in err["message"].lower() for err in exc_info.value.errors)

    def test_invalid_lambda_selection(self):
        """Test that lambda_selection must be EBIC."""
        obj = load_json(FIXTURES_DIR / "model_spec_min.json")
        obj["mgm"]["regularization"]["lambda_selection"] = "CV"

        with pytest.raises(ContractValidationError) as exc_info:
            validate_model_spec_json(obj)

        assert exc_info.value.kind == "model_spec"

    def test_invalid_missing_policy_action(self):
        """Test that missing_policy.action must be warn_and_abort."""
        obj = load_json(FIXTURES_DIR / "model_spec_min.json")
        obj["missing_policy"]["action"] = "impute"

        with pytest.raises(ContractValidationError) as exc_info:
            validate_model_spec_json(obj)

        assert exc_info.value.kind == "model_spec"


class TestResultsValidation:
    """Test results.json validation."""

    def test_valid_minimal_results(self):
        """Test that minimal valid results passes validation."""
        results_path = FIXTURES_DIR / "results_min.json"
        obj = load_json(results_path)
        validate_results_json(obj)  # Should not raise

    def test_invalid_additional_property(self):
        """Test that additional properties are rejected."""
        obj = load_json(FIXTURES_DIR / "results_min.json")
        obj["unknown"] = {"field": "value"}

        with pytest.raises(ContractValidationError) as exc_info:
            validate_results_json(obj)

        assert exc_info.value.kind == "results"

    def test_missing_nodes(self):
        """Test that missing nodes field is rejected."""
        obj = load_json(FIXTURES_DIR / "results_min.json")
        del obj["nodes"]

        with pytest.raises(ContractValidationError) as exc_info:
            validate_results_json(obj)

        assert exc_info.value.kind == "results"
        assert any("nodes" in err["message"].lower() for err in exc_info.value.errors)

    def test_invalid_status(self):
        """Test that invalid status value is rejected."""
        obj = load_json(FIXTURES_DIR / "results_min.json")
        obj["status"] = "pending"

        with pytest.raises(ContractValidationError) as exc_info:
            validate_results_json(obj)

        assert exc_info.value.kind == "results"


class TestFileValidation:
    """Test file-based validation."""

    def test_validate_schema_file(self):
        """Test validating schema file."""
        schema_path = FIXTURES_DIR / "schema_min.json"
        validate_file("schema", schema_path)  # Should not raise

    def test_validate_model_spec_file(self):
        """Test validating model_spec file."""
        spec_path = FIXTURES_DIR / "model_spec_min.json"
        validate_file("model_spec", spec_path)  # Should not raise

    def test_validate_results_file(self):
        """Test validating results file."""
        results_path = FIXTURES_DIR / "results_min.json"
        validate_file("results", results_path)  # Should not raise

    def test_invalid_kind(self):
        """Test that invalid kind raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_file("invalid_kind", FIXTURES_DIR / "schema_min.json")

        assert "invalid_kind" in str(exc_info.value).lower()

    def test_file_not_found(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            validate_file("schema", Path("nonexistent.json"))


class TestRepoRootDetection:
    """Test repository root detection."""

    def test_find_repo_root_from_tests(self):
        """Test finding repo root from tests directory."""
        repo_root = find_repo_root(Path(__file__).parent)
        assert (repo_root / "contracts").is_dir()
        assert (repo_root / "src").is_dir()

    def test_find_repo_root_default(self):
        """Test finding repo root with default starting point."""
        repo_root = find_repo_root()
        assert (repo_root / "contracts").is_dir()


class TestSchemaLoading:
    """Test schema loading and caching."""

    def test_load_schema_caching(self):
        """Test that schemas are cached."""
        schema1 = load_schema("schema")
        schema2 = load_schema("schema")
        assert schema1 is schema2  # Same object due to caching

    def test_load_all_schema_types(self):
        """Test loading all three schema types."""
        schema_validator = load_schema("schema")
        spec_validator = load_schema("model_spec")
        results_validator = load_schema("results")

        assert schema_validator is not None
        assert spec_validator is not None
        assert results_validator is not None
