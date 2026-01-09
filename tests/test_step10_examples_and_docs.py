"""Unit tests for Step 10 example assets and documentation."""

import json
from pathlib import Path

import pandas as pd

from hygeia_graph.contracts import validate_model_spec_json, validate_schema_json

# Get repo root
REPO_ROOT = Path(__file__).parent.parent


class TestExampleFilesExist:
    """Test that all required example files exist."""

    def test_example_data_exists(self):
        """Test example_data.csv exists."""
        path = REPO_ROOT / "assets" / "example_data.csv"
        assert path.exists(), f"Missing: {path}"

    def test_example_schema_exists(self):
        """Test example_schema.json exists."""
        path = REPO_ROOT / "assets" / "example_schema.json"
        assert path.exists(), f"Missing: {path}"

    def test_example_model_spec_exists(self):
        """Test example_model_spec.json exists."""
        path = REPO_ROOT / "assets" / "example_model_spec.json"
        assert path.exists(), f"Missing: {path}"

    def test_methods_doc_exists(self):
        """Test METHODS.md exists."""
        path = REPO_ROOT / "docs" / "METHODS.md"
        assert path.exists(), f"Missing: {path}"

    def test_troubleshooting_doc_exists(self):
        """Test TROUBLESHOOTING.md exists."""
        path = REPO_ROOT / "docs" / "TROUBLESHOOTING.md"
        assert path.exists(), f"Missing: {path}"

    def test_citation_cff_exists(self):
        """Test CITATION.cff exists."""
        path = REPO_ROOT / "CITATION.cff"
        assert path.exists(), f"Missing: {path}"

    def test_citation_bib_exists(self):
        """Test CITATION.bib exists."""
        path = REPO_ROOT / "CITATION.bib"
        assert path.exists(), f"Missing: {path}"


class TestExampleSchemaValidates:
    """Test that example schema validates against contract."""

    def test_example_schema_validates(self):
        """Load and validate example_schema.json."""
        path = REPO_ROOT / "assets" / "example_schema.json"
        with open(path) as f:
            schema = json.load(f)

        # Should not raise
        validate_schema_json(schema)

    def test_example_schema_has_variables(self):
        """Test schema has expected variables."""
        path = REPO_ROOT / "assets" / "example_schema.json"
        with open(path) as f:
            schema = json.load(f)

        assert "variables" in schema
        assert len(schema["variables"]) >= 5

        # Check expected columns exist
        var_ids = {v["id"] for v in schema["variables"]}
        expected = {"age", "crp", "gender", "cancer_stage", "hospital_days", "symptom_count"}
        assert expected.issubset(var_ids)


class TestExampleModelSpecValidates:
    """Test that example model spec validates against contract."""

    def test_example_model_spec_validates(self):
        """Load and validate example_model_spec.json."""
        path = REPO_ROOT / "assets" / "example_model_spec.json"
        with open(path) as f:
            spec = json.load(f)

        # Should not raise
        validate_model_spec_json(spec)

    def test_locked_fields_correct(self):
        """Test locked fields have expected values."""
        path = REPO_ROOT / "assets" / "example_model_spec.json"
        with open(path) as f:
            spec = json.load(f)

        # Lambda selection must be EBIC
        assert spec["mgm"]["regularization"]["lambda_selection"] == "EBIC"

        # Missing policy must be warn_and_abort
        assert spec["missing_policy"]["action"] == "warn_and_abort"

    def test_edge_mapping_defaults(self):
        """Test edge mapping has expected defaults."""
        path = REPO_ROOT / "assets" / "example_model_spec.json"
        with open(path) as f:
            spec = json.load(f)

        assert spec["edge_mapping"]["aggregator"] == "max_abs"
        assert spec["edge_mapping"]["sign_strategy"] == "dominant"


class TestExampleDataNoMissing:
    """Test that example data has no missing values."""

    def test_no_missing_values(self):
        """Load example_data.csv and verify no missing."""
        path = REPO_ROOT / "assets" / "example_data.csv"
        df = pd.read_csv(path)

        missing_count = df.isna().sum().sum()
        assert missing_count == 0, f"Found {missing_count} missing values"

    def test_expected_column_count(self):
        """Test data has at least 5 columns."""
        path = REPO_ROOT / "assets" / "example_data.csv"
        df = pd.read_csv(path)

        assert len(df.columns) >= 5

    def test_expected_row_count(self):
        """Test data has 100-300 rows."""
        path = REPO_ROOT / "assets" / "example_data.csv"
        df = pd.read_csv(path)

        assert 100 <= len(df) <= 300, f"Expected 100-300 rows, got {len(df)}"

    def test_mixed_types_present(self):
        """Test data has mixed variable types."""
        path = REPO_ROOT / "assets" / "example_data.csv"
        df = pd.read_csv(path)

        # Check for continuous (float)
        float_cols = df.select_dtypes(include=["float64"]).columns
        assert len(float_cols) >= 2, "Expected at least 2 float columns"

        # Check for categorical/string
        object_cols = df.select_dtypes(include=["object"]).columns
        assert len(object_cols) >= 1, "Expected at least 1 string column"

        # Check for integer (Poisson/count)
        int_cols = df.select_dtypes(include=["int64"]).columns
        assert len(int_cols) >= 1, "Expected at least 1 integer column"


class TestDocumentationContent:
    """Test documentation files have required content."""

    def test_methods_has_mgm_section(self):
        """Test METHODS.md mentions MGM."""
        path = REPO_ROOT / "docs" / "METHODS.md"
        content = path.read_text(encoding="utf-8")

        assert "Mixed Graphical Model" in content or "MGM" in content
        assert "EBIC" in content
        assert "pairwise" in content.lower() or "k=2" in content

    def test_troubleshooting_has_common_issues(self):
        """Test TROUBLESHOOTING.md covers common issues."""
        path = REPO_ROOT / "docs" / "TROUBLESHOOTING.md"
        content = path.read_text(encoding="utf-8")

        assert "Rscript" in content
        assert "missing" in content.lower()
        assert "pip install" in content

    def test_citation_cff_valid_yaml(self):
        """Test CITATION.cff is valid YAML."""
        path = REPO_ROOT / "CITATION.cff"
        content = path.read_text(encoding="utf-8")

        # Basic checks for CFF format
        assert "cff-version:" in content
        assert "title:" in content
        assert "authors:" in content
