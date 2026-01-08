"""Unit tests for Step 3 data layer (CSV ingestion, profiling, schema builder)."""

import io

import numpy as np
import pandas as pd

from hygeia_graph.contracts import validate_schema_json
from hygeia_graph.data_processor import (
    build_schema_json,
    infer_variables,
    load_csv,
    make_variable_id,
    profile_df,
)


class TestMakeVariableId:
    """Test variable ID generation and deduplication."""

    def test_simple_name(self):
        """Test simple column name conversion."""
        var_id = make_variable_id("Age", set())
        assert var_id == "age"

    def test_spaces_to_underscore(self):
        """Test space replacement."""
        var_id = make_variable_id("Body Mass Index", set())
        assert var_id == "body_mass_index"

    def test_invalid_chars_removed(self):
        """Test removal of invalid characters."""
        var_id = make_variable_id("Score (%)!", set())
        assert var_id == "score"

    def test_starts_with_digit(self):
        """Test prefixing when starting with digit."""
        var_id = make_variable_id("1st_measurement", set())
        assert var_id == "v_1st_measurement"

    def test_deduplication(self):
        """Test deduplication with suffix."""
        existing = {"age", "age_2"}
        var_id = make_variable_id("Age", existing)
        assert var_id == "age_3"

    def test_valid_pattern(self):
        """Test that generated IDs match required pattern."""
        import re

        pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*$")
        test_names = ["Age", "Body Mass Index", "Score (%)", "1st_measurement", "x"]
        existing: set[str] = set()

        for name in test_names:
            var_id = make_variable_id(name, existing)
            assert pattern.match(var_id), f"Invalid ID: {var_id}"
            existing.add(var_id)


class TestLoadCsv:
    """Test CSV loading."""

    def test_load_from_string_io(self):
        """Test loading from StringIO (simulates Streamlit UploadedFile)."""
        csv_data = "col1,col2\n1,2\n3,4\n"
        file_obj = io.StringIO(csv_data)
        df = load_csv(file_obj)

        assert len(df) == 2
        assert list(df.columns) == ["col1", "col2"]


class TestProfileDf:
    """Test data profiling."""

    def test_profile_no_missing(self):
        """Test profiling with no missing data."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})
        profile = profile_df(df)

        assert profile["row_count"] == 3
        assert profile["column_count"] == 2
        assert profile["missing"]["cells"] == 0
        assert profile["missing"]["rate"] == 0.0

    def test_profile_with_missing(self):
        """Test profiling with missing data."""
        df = pd.DataFrame({"a": [1, None, 3], "b": [4.0, 5.0, None]})
        profile = profile_df(df)

        assert profile["row_count"] == 3
        assert profile["column_count"] == 2
        assert profile["missing"]["cells"] == 2
        assert profile["missing"]["rate"] == 2 / 6  # 2 out of 6 cells

        # Check by_variable
        by_var = {v["variable_id"]: v for v in profile["missing"]["by_variable"]}
        assert by_var["a"]["cells"] == 1
        assert by_var["b"]["cells"] == 1


class TestInferVariables:
    """Test type inference."""

    def test_infer_float_is_gaussian(self):
        """Test that float columns are inferred as Gaussian."""
        df = pd.DataFrame({"height": [1.75, 1.80, 1.65, 1.90]})
        variables = infer_variables(df)

        assert len(variables) == 1
        var = variables[0]
        assert var["mgm_type"] == "g"
        assert var["measurement_level"] == "continuous"
        assert var["level"] == 1

    def test_infer_nonnegative_int_many_unique_is_count(self):
        """Test that non-negative integers with high uniqueness are inferred as count."""
        # 200 unique values → should be count
        df = pd.DataFrame({"count_var": list(range(200))})
        variables = infer_variables(df)

        assert len(variables) == 1
        var = variables[0]
        assert var["mgm_type"] == "p"
        assert var["measurement_level"] == "count"
        assert var["level"] == 1
        assert var["constraints"]["nonnegative"] is True

    def test_infer_small_consecutive_int_is_ordinal_categorical(self):
        """Test that small consecutive integers are inferred as ordinal categorical."""
        df = pd.DataFrame({"rating": [1, 2, 3, 1, 2, 3, 2, 1]})
        variables = infer_variables(df)

        assert len(variables) == 1
        var = variables[0]
        assert var["mgm_type"] == "c"
        assert var["measurement_level"] == "ordinal"
        assert var["level"] == 3
        assert var["categories"] == ["1", "2", "3"]

    def test_infer_boolean_is_categorical(self):
        """Test that boolean columns are inferred as categorical."""
        df = pd.DataFrame({"flag": [True, False, True, True]})
        variables = infer_variables(df)

        assert len(variables) == 1
        var = variables[0]
        assert var["mgm_type"] == "c"
        assert var["measurement_level"] == "nominal"
        assert var["level"] == 2

    def test_infer_string_is_categorical(self):
        """Test that string columns are inferred as categorical."""
        df = pd.DataFrame({"category": ["A", "B", "A", "C"]})
        variables = infer_variables(df)

        assert len(variables) == 1
        var = variables[0]
        assert var["mgm_type"] == "c"
        assert var["measurement_level"] == "nominal"
        assert var["level"] == 3
        assert set(var["categories"]) == {"A", "B", "C"}

    def test_infer_negative_int_is_gaussian(self):
        """Test that integers with negative values are inferred as Gaussian."""
        df = pd.DataFrame({"score": [-5, -10, 5, 10]})
        variables = infer_variables(df)

        assert len(variables) == 1
        var = variables[0]
        assert var["mgm_type"] == "g"
        assert var["measurement_level"] == "continuous"
        assert var["level"] == 1

    def test_infer_nonconsecutive_int_is_nominal(self):
        """Test that non-consecutive integers are inferred as nominal categorical."""
        df = pd.DataFrame({"group": [1, 3, 5, 1, 3]})
        variables = infer_variables(df)

        assert len(variables) == 1
        var = variables[0]
        assert var["mgm_type"] == "c"
        assert var["measurement_level"] == "nominal"  # Not ordinal because not consecutive
        assert var["level"] == 3


class TestBuildSchemaJson:
    """Test schema.json building."""

    def test_build_schema_validates(self):
        """Test that built schema validates against contract."""
        # Create simple DataFrame
        df = pd.DataFrame(
            {
                "age": [25, 30, 35, 40],
                "height": [1.75, 1.80, 1.65, 1.90],
                "group": ["A", "B", "A", "B"],
            }
        )

        # Infer variables
        variables = infer_variables(df)

        # Build schema
        schema_obj = build_schema_json(df, variables)

        # Should not raise ContractValidationError
        validate_schema_json(schema_obj)

    def test_schema_includes_required_fields(self):
        """Test that schema includes all required fields."""
        df = pd.DataFrame({"x": [1, 2, 3]})
        variables = infer_variables(df)
        schema = build_schema_json(df, variables)

        # Check required top-level fields
        assert "schema_version" in schema
        assert "created_at" in schema
        assert "dataset" in schema
        assert "variables" in schema

        # Check dataset fields
        assert schema["dataset"]["row_count"] == 3
        assert schema["dataset"]["column_count"] == 1

    def test_schema_includes_warnings_with_missing_data(self):
        """Test that schema includes warnings when missing data detected."""
        df = pd.DataFrame({"x": [1, None, 3]})
        variables = infer_variables(df)
        schema = build_schema_json(df, variables)

        assert "warnings" in schema
        assert len(schema["warnings"]) == 1
        assert schema["warnings"][0]["code"] == "MISSING_DATA_DETECTED"
        assert schema["warnings"][0]["level"] == "warning"

    def test_schema_no_warnings_without_missing_data(self):
        """Test that schema has no warnings when no missing data."""
        df = pd.DataFrame({"x": [1, 2, 3]})
        variables = infer_variables(df)
        schema = build_schema_json(df, variables)

        assert "warnings" not in schema or len(schema.get("warnings", [])) == 0


class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_workflow_mixed_types(self):
        """Test complete workflow with mixed data types."""
        # Create DataFrame with multiple types
        df = pd.DataFrame(
            {
                "patient_id": list(range(100)),  # Should be count
                "age": np.random.randint(20, 80, 100),  # Should be ordinal or nominal
                "height": np.random.normal(1.70, 0.10, 100),  # Should be Gaussian
                "sex": np.random.choice(["M", "F"], 100),  # Should be categorical
                "treatment": np.random.choice([1, 2, 3], 100),  # Should be ordinal
            }
        )

        # Run full workflow
        profile = profile_df(df)
        variables = infer_variables(df)
        schema = build_schema_json(df, variables)

        # Validate
        validate_schema_json(schema)  # Should not raise

        # Check profile
        assert profile["row_count"] == 100
        assert profile["column_count"] == 5

        # Check variables
        assert len(variables) == 5
        var_by_id = {v["id"]: v for v in variables}

        assert var_by_id["patient_id"]["mgm_type"] == "p"  # Count
        assert var_by_id["height"]["mgm_type"] == "g"  # Gaussian
        assert var_by_id["sex"]["mgm_type"] == "c"  # Categorical
