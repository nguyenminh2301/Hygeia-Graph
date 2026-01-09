"""Integration tests for Step 6 Python↔R subprocess bridge."""

import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from hygeia_graph.contracts import validate_results_json
from hygeia_graph.r_interface import (
    RBackendError,
    compute_sha256,
    ensure_rscript_available,
    locate_repo_root,
    run_mgm_subprocess,
    write_artifacts_to_dir,
)

# Get paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def check_rscript_available():
    """Check if Rscript is available."""
    return shutil.which("Rscript") is not None


def check_r_packages_available():
    """Check if required R packages are installed."""
    if not check_rscript_available():
        return False
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


class TestUtilityFunctions:
    """Test utility functions that don't require R."""

    def test_locate_repo_root(self):
        """Test that repo root can be found."""
        root = locate_repo_root()
        assert root.is_dir()
        assert (root / "contracts").is_dir()
        assert (root / "r").is_dir()

    def test_compute_sha256(self):
        """Test SHA256 computation."""
        data = b"hello world"
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        assert compute_sha256(data) == expected

    def test_write_artifacts_to_dir(self, tmp_path):
        """Test artifact writing."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        schema = {"schema_version": "0.1.0", "variables": []}
        spec = {"spec_version": "0.1.0", "mgm": {}}

        result = write_artifacts_to_dir(tmp_path, df, schema, spec)

        # Check paths exist
        assert result["paths"]["data"].exists()
        assert result["paths"]["schema"].exists()
        assert result["paths"]["spec"].exists()

        # Check SHA256 hashes present
        assert "sha256" in result
        assert len(result["sha256"]["data"]) == 64
        assert len(result["sha256"]["schema"]) == 64
        assert len(result["sha256"]["spec"]) == 64


class TestRscriptAvailability:
    """Test Rscript availability check."""

    def test_ensure_rscript_available_when_present(self):
        """Test that function returns path when Rscript available."""
        if not check_rscript_available():
            pytest.skip("Rscript not available")

        path = ensure_rscript_available()
        assert path is not None
        assert "Rscript" in path or "rscript" in path.lower()

    def test_ensure_rscript_available_error(self, monkeypatch):
        """Test that RuntimeError raised when Rscript not found."""
        monkeypatch.setattr(shutil, "which", lambda x: None)

        with pytest.raises(RuntimeError, match="Rscript not found"):
            ensure_rscript_available()


# Skip R-dependent tests if R or packages not available
pytestmark_r = pytest.mark.skipif(
    not check_rscript_available() or not check_r_packages_available(),
    reason="Rscript or required R packages not available",
)


@pytestmark_r
class TestRBackendExecution:
    """Test R backend execution (requires R and packages)."""

    def test_run_mgm_subprocess_success(self, tmp_path):
        """Test successful MGM execution."""
        # Load fixtures
        import json

        with open(FIXTURES_DIR / "step5_schema.json") as f:
            schema = json.load(f)
        with open(FIXTURES_DIR / "step5_model_spec.json") as f:
            spec = json.load(f)

        df = pd.read_csv(FIXTURES_DIR / "step5_data.csv")

        # Run MGM
        result = run_mgm_subprocess(
            df=df,
            schema_json=schema,
            model_spec_json=spec,
            timeout_sec=120,
            quiet=True,
        )

        # Check result structure
        assert "results" in result
        assert "process" in result
        assert "paths" in result
        assert "sha256" in result

        # Validate results
        validate_results_json(result["results"])

        # Check process info
        assert isinstance(result["process"]["returncode"], int)
        assert isinstance(result["process"]["seconds"], float)
        assert result["process"]["timed_out"] is False

        # Check status
        assert result["results"]["status"] in ["success", "failed"]

    def test_run_mgm_subprocess_missing_data_abort(self, tmp_path):
        """Test that missing data triggers abort."""
        import json

        # Load schema and spec from fixtures
        with open(FIXTURES_DIR / "step5_schema.json") as f:
            schema = json.load(f)
        with open(FIXTURES_DIR / "step5_model_spec.json") as f:
            spec = json.load(f)

        # Load data with missing values
        df = pd.read_csv(FIXTURES_DIR / "step5_data_missing.csv")

        # Run MGM - should complete but with status=failed
        result = run_mgm_subprocess(
            df=df,
            schema_json=schema,
            model_spec_json=spec,
            timeout_sec=120,
            quiet=True,
        )

        # Check result
        assert result["results"]["status"] == "failed"

        # Check for MISSING_DATA_ABORT message
        messages = result["results"].get("messages", [])
        assert len(messages) > 0
        assert any(msg.get("code") == "MISSING_DATA_ABORT" for msg in messages)

        # Edges should be empty
        assert len(result["results"].get("edges", [])) == 0


class TestRBackendErrorHandling:
    """Test R backend error handling."""

    def test_rbackend_error_attributes(self):
        """Test RBackendError exception attributes."""
        error = RBackendError(
            message="Test error",
            stdout="stdout content",
            stderr="stderr content",
            returncode=1,
            workdir=Path("/tmp/test"),
        )

        assert error.message == "Test error"
        assert error.stdout == "stdout content"
        assert error.stderr == "stderr content"
        assert error.returncode == 1
        assert error.workdir == Path("/tmp/test")

    def test_rbackend_error_str(self):
        """Test RBackendError string representation."""
        error = RBackendError(
            message="Test error",
            stderr="some error details",
            returncode=1,
        )

        error_str = str(error)
        assert "Test error" in error_str
        assert "Exit code: 1" in error_str
        assert "some error details" in error_str
