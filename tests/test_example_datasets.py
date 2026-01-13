"""Unit tests for example datasets module."""


from hygeia_graph.example_datasets import (
    EXAMPLES,
    get_example_keys,
    get_example_meta,
    get_example_path,
    load_example_df,
)


class TestExampleMetadata:
    """Tests for example metadata registry."""

    def test_examples_list_has_three(self):
        """Test that we have 3 examples."""
        assert len(EXAMPLES) == 3

    def test_example_keys(self):
        """Test example keys are correct."""
        keys = get_example_keys()
        assert "easy" in keys
        assert "medium" in keys
        assert "hard" in keys

    def test_get_example_meta_easy(self):
        """Test getting easy example metadata."""
        meta = get_example_meta("easy")
        assert meta is not None
        assert "title" in meta
        assert "goal" in meta
        assert "filename" in meta

    def test_get_example_meta_invalid(self):
        """Test invalid key returns None."""
        assert get_example_meta("invalid") is None


class TestExampleFiles:
    """Tests for example CSV files."""

    def test_example_files_exist(self):
        """Test that all example files exist."""
        for key in get_example_keys():
            path = get_example_path(key)
            assert path is not None
            assert path.exists(), f"Missing: {path}"

    def test_examples_load_no_missing(self):
        """Test that examples have no missing values."""
        for key in get_example_keys():
            df = load_example_df(key)
            missing_count = df.isna().sum().sum()
            assert missing_count == 0, f"{key} has {missing_count} missing values"

    def test_examples_match_expected_size(self):
        """Test that examples are within expected row ranges."""
        for ex in EXAMPLES:
            df = load_example_df(ex["key"])
            min_rows, max_rows = ex["rows_expected"]
            assert min_rows <= len(df) <= max_rows, (
                f"{ex['key']}: {len(df)} rows not in range [{min_rows}, {max_rows}]"
            )

    def test_easy_has_six_columns(self):
        """Test easy dataset has expected columns."""
        df = load_example_df("easy")
        assert len(df.columns) == 6

    def test_medium_has_twelve_columns(self):
        """Test medium dataset has expected columns."""
        df = load_example_df("medium")
        assert len(df.columns) == 12

    def test_hard_has_many_columns(self):
        """Test hard dataset has many columns."""
        df = load_example_df("hard")
        assert len(df.columns) >= 25


class TestMixedTypes:
    """Tests for mixed variable types."""

    def test_examples_have_mixed_types(self):
        """Test that each example has mixed types."""
        for key in get_example_keys():
            df = load_example_df(key)

            # Check for numeric
            numeric_cols = df.select_dtypes(include=["float64", "int64"]).columns
            assert len(numeric_cols) > 0, f"{key} has no numeric columns"

            # Check for object (categorical)
            object_cols = df.select_dtypes(include=["object"]).columns
            assert len(object_cols) > 0, f"{key} has no categorical columns"
