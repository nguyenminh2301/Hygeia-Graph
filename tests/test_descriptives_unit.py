"""Unit tests for descriptives module."""

import numpy as np
import pandas as pd
import pytest

from hygeia_graph.descriptives import (
    build_categorical_levels_table,
    build_descriptives_payload,
    build_variable_summary_table,
    classify_variables,
    compute_missing_summary,
    normality_test,
    summarize_categorical,
    summarize_continuous,
)


@pytest.fixture
def sample_df():
    """Create sample DataFrame with mixed types."""
    np.random.seed(42)
    return pd.DataFrame({
        "Age": [25.0, 30.0, np.nan, 45.0, 50.0, 35.0, 40.0, 28.0, 55.0, 60.0],
        "HospitalDays": [0, 1, 2, 0, 3, 1, 5, 0, 2, 1],
        "Gender": [
            "Male", "Female", "Male", "Female", "Male",
            None, "Female", "Male", "Female", "Male"
        ],
    })


class TestClassifyVariables:
    """Tests for variable classification."""

    def test_classify_without_schema(self, sample_df):
        """Test classification from data only."""
        variables = classify_variables(sample_df)

        assert len(variables) == 3

        age_var = next(v for v in variables if v["column"] == "Age")
        assert age_var["mgm_type"] == "g"
        assert age_var["is_numeric"]

        gender_var = next(v for v in variables if v["column"] == "Gender")
        assert gender_var["mgm_type"] == "c"
        assert gender_var["is_categorical"]


class TestMissingSummary:
    """Tests for missing value summary."""

    def test_compute_missing_summary(self, sample_df):
        """Test missing summary computation."""
        summary = compute_missing_summary(sample_df)

        assert summary["n_rows"] == 10
        assert summary["n_cols"] == 3
        assert summary["missing_cells"] == 2  # Age has 1, Gender has 1
        assert summary["missing_rate"] > 0

        assert "Age" in summary["by_column"]
        assert summary["by_column"]["Age"]["missing"] == 1


class TestNormalityTest:
    """Tests for normality test."""

    def test_normality_test_sufficient_data(self):
        """Test normality test with sufficient data."""
        np.random.seed(42)
        series = pd.Series(np.random.normal(0, 1, 100))
        result = normality_test(series)

        assert result["test"] in ("shapiro", "unavailable")
        if result["test"] == "shapiro":
            assert result["p_value"] is not None
            assert result["n_used"] == 100

    def test_normality_test_small_n(self):
        """Test normality test with small n."""
        series = pd.Series([1.0, 2.0, 3.0])
        result = normality_test(series)

        assert result["test"] in ("skipped", "unavailable")


class TestSummarizeContinuous:
    """Tests for continuous variable summary."""

    def test_summarize_continuous(self, sample_df):
        """Test continuous summary."""
        stats = summarize_continuous(sample_df["Age"])

        assert "mean" in stats
        assert "sd" in stats
        assert "median" in stats
        assert "q1" in stats
        assert "q3" in stats
        assert "iqr" in stats
        assert "min" in stats
        assert "max" in stats

        assert stats["min"] <= stats["median"] <= stats["max"]


class TestSummarizeCategorical:
    """Tests for categorical variable summary."""

    def test_summarize_categorical(self, sample_df):
        """Test categorical summary."""
        summary, levels_df = summarize_categorical(sample_df["Gender"])

        assert summary["n_levels"] == 2
        assert summary["top_level"] in ("Male", "Female")

        # Rates should sum to 1
        assert abs(levels_df["rate"].sum() - 1.0) < 0.01


class TestBuildTables:
    """Tests for building summary tables."""

    def test_build_variable_summary_table(self, sample_df):
        """Test variable summary table."""
        variables = classify_variables(sample_df)
        table = build_variable_summary_table(sample_df, variables)

        assert len(table) == 3
        assert "var_id" in table.columns
        assert "n_missing" in table.columns
        assert "missing_rate" in table.columns

    def test_build_categorical_levels_table(self, sample_df):
        """Test categorical levels table."""
        variables = classify_variables(sample_df)
        table = build_categorical_levels_table(sample_df, variables)

        assert "var_id" in table.columns
        assert "level" in table.columns
        assert "count" in table.columns
        assert "rate" in table.columns


class TestPayload:
    """Tests for payload building."""

    def test_payload_is_json_serializable(self, sample_df):
        """Test that payload can be serialized to JSON."""
        import json

        variables = classify_variables(sample_df)
        missing = compute_missing_summary(sample_df)
        table = build_variable_summary_table(sample_df, variables)
        payload = build_descriptives_payload(missing, table)

        # Should not raise
        json_str = json.dumps(payload)
        assert len(json_str) > 0
        assert "n_rows" in json_str
