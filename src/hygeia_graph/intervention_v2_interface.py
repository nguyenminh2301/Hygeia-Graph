"""Python interface to intervention v2 R script (mgm::predict.mgm)."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


class InterventionV2Error(Exception):
    """Error during intervention v2 computation."""

    def __init__(self, message: str, code: str = "UNKNOWN", stdout: str = "", stderr: str = ""):
        self.message = message
        self.code = code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(message)


def run_intervention_v2_subprocess(
    model_rds_path: str,
    data_path: str,
    schema_json: Dict[str, Any],
    intervene_node: str,
    delta: float = 1.0,
    delta_units: str = "sd",
    timeout_sec: int = 60,
) -> Dict[str, Any]:
    """Run intervention v2 using mgm::predict.mgm.

    Args:
        model_rds_path: Path to saved MGM model RDS file.
        data_path: Path to original data CSV.
        schema_json: Schema dictionary.
        intervene_node: Node ID to intervene on.
        delta: Change amount.
        delta_units: "sd" or "raw".
        timeout_sec: Subprocess timeout.

    Returns:
        Dictionary with intervention effects.

    Raises:
        InterventionV2Error: If computation fails.
        ValueError: If inputs invalid.
    """
    if not model_rds_path or not Path(model_rds_path).exists():
        raise ValueError("model_rds_path must exist")

    if not data_path or not Path(data_path).exists():
        raise ValueError("data_path must exist")

    if not schema_json:
        raise ValueError("schema_json is required")

    if not intervene_node:
        raise ValueError("intervene_node is required")

    # Find R script
    script_path = Path(__file__).parent.parent.parent / "r" / "run_intervention_v2.R"
    if not script_path.exists():
        raise InterventionV2Error("R script not found", code="SCRIPT_NOT_FOUND")

    # Create temp directory
    with tempfile.TemporaryDirectory(prefix="hygeia_intv2_") as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Write schema
        schema_path = tmpdir_path / "schema.json"
        with open(schema_path, "w") as f:
            json.dump(schema_json, f)

        out_path = tmpdir_path / "intervention_v2.json"

        # Build command
        cmd = [
            "Rscript",
            str(script_path),
            "--model_rds",
            str(model_rds_path),
            "--data",
            str(data_path),
            "--schema",
            str(schema_path),
            "--out_path",
            str(out_path),
            "--intervene_node",
            intervene_node,
            "--delta",
            str(delta),
            "--delta_units",
            delta_units,
            "--quiet",
        ]

        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            raise InterventionV2Error(
                f"Intervention v2 timed out after {timeout_sec}s",
                code="TIMEOUT",
            )
        except FileNotFoundError:
            raise InterventionV2Error(
                "Rscript not found in PATH",
                code="RSCRIPT_NOT_FOUND",
            )

        # Parse output
        if not out_path.exists():
            raise InterventionV2Error(
                "Intervention output file not created",
                code="NO_OUTPUT",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        with open(out_path, "r") as f:
            output = json.load(f)

        if output.get("status") != "success":
            raise InterventionV2Error(
                output.get("message", "Unknown error"),
                code=output.get("code", "UNKNOWN"),
                stdout=result.stdout,
                stderr=result.stderr,
            )

        return output
