"""Integration tests for Step 5 R backend (MGM execution)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hygeia_graph.contracts import validate_results_json

# Get paths
REPO_ROOT = Path(__file__).parent.parent
R_SCRIPT = REPO_ROOT / "r" / "run_mgm.R"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def check_rscript_available():
    """Check if Rscript is available."""
    return shutil.which("Rscript") is not None


def check_r_packages_available():
    """Check if required R packages are installed."""
    try:
        result = subprocess.run(
            [
                "Rscript",
                "-e",
                "quit(status=ifelse(requireNamespace('mgm',quietly=TRUE) && "
                "requireNamespace('jsonlite',quietly=TRUE) && "
                "requireNamespace('digest',quietly=TRUE) && "
                "requireNamespace('uuid',quietly=TRUE),0,1))",
            ],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# Skip all tests in this module if R or packages are not available
pytestmark = pytest.mark.skipif(
    not check_rscript_available() or not check_r_packages_available(),
    reason="Rscript or required R packages (mgm, jsonlite, digest, uuid) not available",
)


class TestRBackendExecution:
    """Test R backend MGM execution."""

    def test_run_mgm_success(self, tmp_path):
        """Test successful MGM execution with valid data."""
        # Paths
        data_csv = FIXTURES_DIR / "step5_data.csv"
        schema_json = FIXTURES_DIR / "step5_schema.json"
        spec_json = FIXTURES_DIR / "step5_model_spec.json"
        out_json = tmp_path / "results.json"

        # Run R script
        result = subprocess.run(
            [
                "Rscript",
                str(R_SCRIPT),
                "--data",
                str(data_csv),
                "--schema",
                str(schema_json),
                "--spec",
                str(spec_json),
                "--out",
                str(out_json),
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should exit successfully (even if status=failed)
        assert result.returncode == 0, f"R script failed: {result.stderr}"

        # Output file should exist
        assert out_json.exists(), "results.json was not created"

        # Load and validate results
        with open(out_json) as f:
            results = json.load(f)

        # Should validate against contract
        validate_results_json(results)  # Will raise if invalid

        # Check required fields
        assert "result_version" in results
        assert "analysis_id" in results
        assert "status" in results
        assert "engine" in results
        assert "nodes" in results
        assert "edges" in results

        # Status should be success or failed (but valid JSON either way)
        assert results["status"] in ["success", "failed"]

    def test_run_mgm_missing_data_abort(self, tmp_path):
        """Test that missing data triggers warn_and_abort policy."""
        # Paths
        data_csv = FIXTURES_DIR / "step5_data_missing.csv"
        schema_json = FIXTURES_DIR / "step5_schema.json"
        spec_json = FIXTURES_DIR / "step5_model_spec.json"
        out_json = tmp_path / "results_missing.json"

        # Run R script
        result = subprocess.run(
            [
                "Rscript",
                str(R_SCRIPT),
                "--data",
                str(data_csv),
                "--schema",
                str(schema_json),
                "--spec",
                str(spec_json),
                "--out",
                str(out_json),
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should still exit with 0 (results.json written)
        assert result.returncode == 0

        # Load results
        assert out_json.exists()
        with open(out_json) as f:
            results = json.load(f)

        # Should validate
        validate_results_json(results)

        # Status should be failed
        assert results["status"] == "failed"

        # Should have MISSING_DATA_ABORT message
        messages = results.get("messages", [])
        assert len(messages) > 0
        assert any(msg.get("code") == "MISSING_DATA_ABORT" for msg in messages)

        # Edges should be empty
        assert len(results.get("edges", [])) == 0

    def test_results_json_structure(self, tmp_path):
        """Test that results.json has all expected fields."""
        # Paths
        data_csv = FIXTURES_DIR / "step5_data.csv"
        schema_json = FIXTURES_DIR / "step5_schema.json"
        spec_json = FIXTURES_DIR / "step5_model_spec.json"
        out_json = tmp_path / "results_struct.json"

        # Run R script
        subprocess.run(
            [
                "Rscript",
                str(R_SCRIPT),
                "--data",
                str(data_csv),
                "--schema",
                str(schema_json),
                "--spec",
                str(spec_json),
                "--out",
                str(out_json),
                "--quiet",
            ],
            capture_output=True,
            timeout=60,
        )

        # Load results
        with open(out_json) as f:
            results = json.load(f)

        # Check engine info
        assert results["engine"]["name"] == "R.mgm"
        assert "r_version" in results["engine"]
        assert "package_versions" in results["engine"]

        # Check input hashes
        assert "input" in results
        assert "schema_sha256" in results["input"]
        assert "spec_sha256" in results["input"]

        # Check nodes match schema variables
        assert "nodes" in results
        assert len(results["nodes"]) == 3  # age, height, group

        # Each node should have required fields
        for node in results["nodes"]:
            assert "id" in node
            assert "column" in node
            assert "mgm_type" in node
            assert "measurement_level" in node
            assert "level" in node

    def test_edge_structure(self, tmp_path):
        """Test that edges have correct structure if any are found."""
        # Paths
        data_csv = FIXTURES_DIR / "step5_data.csv"
        schema_json = FIXTURES_DIR / "step5_schema.json"
        spec_json = FIXTURES_DIR / "step5_model_spec.json"
        out_json = tmp_path / "results_edges.json"

        # Run R script
        subprocess.run(
            [
                "Rscript",
                str(R_SCRIPT),
                "--data",
                str(data_csv),
                "--schema",
                str(schema_json),
                "--spec",
                str(spec_json),
                "--out",
                str(out_json),
                "--quiet",
            ],
            capture_output=True,
            timeout=60,
        )

        # Load results
        with open(out_json) as f:
            results = json.load(f)

        # If edges exist, check structure
        if len(results.get("edges", [])) > 0:
            for edge in results["edges"]:
                assert "source" in edge
                assert "target" in edge
                assert "weight" in edge
                assert "sign" in edge
                assert "block_summary" in edge

                # Check block_summary
                bs = edge["block_summary"]
                assert "n_params" in bs
                assert "l2_norm" in bs
                assert "mean" in bs
                assert "max" in bs
                assert "min" in bs
                assert "max_abs" in bs

                # Sign should be valid
                assert edge["sign"] in ["positive", "negative", "zero", "unsigned"]
