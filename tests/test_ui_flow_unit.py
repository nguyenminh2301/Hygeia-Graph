"""Unit tests for UI flow helpers."""


from hygeia_graph.ui_flow import (
    build_zip_bytes,
    clear_all_state,
    get_next_page,
    get_schema_summary,
)


class TestGetNextPage:
    """Tests for next page logic."""

    def test_after_schema_ready_goes_to_model_settings(self):
        """Test navigation after schema is ready."""
        result = get_next_page(
            "Data & Schema",
            "explore",
            {"schema_ready": True}
        )
        assert result == "Model Settings"

    def test_after_schema_lasso_goal_goes_to_preprocessing(self):
        """Test LASSO goal goes to preprocessing."""
        result = get_next_page(
            "Data & Schema",
            "lasso",
            {"schema_ready": True}
        )
        assert result == "Preprocessing"

    def test_after_spec_ready_goes_to_run_mgm(self):
        """Test navigation after spec is ready."""
        result = get_next_page(
            "Model Settings",
            "explore",
            {"spec_ready": True}
        )
        assert result == "Run MGM"

    def test_after_mgm_success_goes_to_explore(self):
        """Test default navigation after MGM success."""
        result = get_next_page(
            "Run MGM",
            "explore",
            {"mgm_success": True}
        )
        assert result == "Explore"

    def test_after_mgm_success_comparison_goal(self):
        """Test comparison goal goes to Comparison."""
        result = get_next_page(
            "Run MGM",
            "comparison",
            {"mgm_success": True}
        )
        assert result == "Comparison"

    def test_after_mgm_success_robustness_goal(self):
        """Test robustness goal goes to Robustness."""
        result = get_next_page(
            "Run MGM",
            "robustness",
            {"mgm_success": True}
        )
        assert result == "Robustness"

    def test_not_ready_returns_none(self):
        """Test returns None when not ready."""
        result = get_next_page(
            "Data & Schema",
            "explore",
            {"schema_ready": False}
        )
        assert result is None


class TestClearAllState:
    """Tests for clear all state function."""

    def test_clears_expected_keys(self):
        """Test that expected keys are removed."""
        fake_state = {
            "df": "data",
            "schema_obj": {},
            "results_json": {},
            "derived_cache": {},
            "other_key": "keep",
        }

        removed = clear_all_state(fake_state)

        assert "df" in removed
        assert "schema_obj" in removed
        assert "results_json" in removed
        assert "other_key" not in removed
        assert "other_key" in fake_state

    def test_clears_settings_effective_keys(self):
        """Test that *_settings_effective keys are removed."""
        fake_state = {
            "bootnet_settings_effective": {},
            "lasso_settings_effective": {},
            "keep_this": True,
        }

        removed = clear_all_state(fake_state)

        assert "bootnet_settings_effective" in removed
        assert "lasso_settings_effective" in removed
        assert "keep_this" in fake_state


class TestBuildZipBytes:
    """Tests for ZIP builder."""

    def test_returns_bytes(self):
        """Test that ZIP is returned as bytes."""
        result = build_zip_bytes(
            artifacts={"schema": {"test": True}},
            tables={"edges": "a,b,c\n1,2,3"},
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_zip_contains_expected_files(self):
        """Test that ZIP contains expected files."""
        import io
        import zipfile

        result = build_zip_bytes(
            artifacts={"schema": {"test": True}, "results": {"status": "success"}},
            tables={"edges": "a,b,c\n1,2,3"},
            session_info={"analysis_id": "test123"},
        )

        with zipfile.ZipFile(io.BytesIO(result), "r") as zf:
            names = zf.namelist()

            assert "artifacts/schema.json" in names
            assert "artifacts/results.json" in names
            assert "tables/edges.csv" in names
            assert "meta/session_info.json" in names


class TestGetSchemaSummary:
    """Tests for schema summary."""

    def test_schema_summary_counts_types(self):
        """Test schema summary counts variable types."""
        schema = {
            "variables": [
                {"id": "Age", "mgm_type": "g"},
                {"id": "BMI", "mgm_type": "g"},
                {"id": "Gender", "mgm_type": "c"},
                {"id": "Days", "mgm_type": "p"},
            ]
        }

        result = get_schema_summary(schema)

        assert "4 variables" in result
        assert "g=2" in result
        assert "c=1" in result
        assert "p=1" in result

    def test_empty_schema_returns_not_ready(self):
        """Test empty schema returns not ready message."""
        assert "not ready" in get_schema_summary({}).lower()
        assert "not ready" in get_schema_summary(None).lower()
