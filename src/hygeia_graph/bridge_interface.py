"""Python interface to networktools bridge R script."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


class BridgeError(Exception):
    """Error during bridge computation."""

    def __init__(self, message: str, code: str = "UNKNOWN", stdout: str = "", stderr: str = ""):
        self.message = message
        self.code = code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(message)


def run_bridge_subprocess(
    results_json: Dict[str, Any],
    derived_metrics_json: Optional[Dict[str, Any]] = None,
    threshold: float = 0.0,
    use_abs_filter: bool = True,
    top_edges: Optional[int] = None,
    timeout_sec: int = 120,
) -> Dict[str, Any]:
    """Run networktools bridge computation via R subprocess.

    Args:
        results_json: The MGM results JSON.
        derived_metrics_json: Optional derived metrics with communities.
        threshold: Edge weight threshold.
        use_abs_filter: Whether to use absolute weight for filtering.
        top_edges: Limit number of edges.
        timeout_sec: Subprocess timeout.

    Returns:
        Dictionary with bridge metrics.

    Raises:
        BridgeError: If computation fails.
        ValueError: If inputs invalid.
    """
    if not results_json:
        raise ValueError("results_json is required")

    if results_json.get("status") != "success":
        raise ValueError("results_json must have status=success")

    # Find R script
    script_path = Path(__file__).parent.parent.parent / "r" / "run_bridge_networktools.R"
    if not script_path.exists():
        raise BridgeError("R script not found", code="SCRIPT_NOT_FOUND")

    # Create temp directory
    with tempfile.TemporaryDirectory(prefix="hygeia_bridge_") as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Write input files
        results_path = tmpdir_path / "results.json"
        with open(results_path, "w") as f:
            json.dump(results_json, f)

        derived_path = None
        if derived_metrics_json:
            derived_path = tmpdir_path / "derived.json"
            with open(derived_path, "w") as f:
                json.dump(derived_metrics_json, f)

        out_path = tmpdir_path / "bridge_posthoc.json"

        # Build command
        cmd = [
            "Rscript",
            str(script_path),
            "--results",
            str(results_path),
            "--out_path",
            str(out_path),
            "--threshold",
            str(threshold),
            "--use_abs_filter",
            "1" if use_abs_filter else "0",
            "--quiet",
        ]

        if derived_path:
            cmd.extend(["--derived", str(derived_path)])

        if top_edges is not None and top_edges > 0:
            cmd.extend(["--top_edges", str(top_edges)])

        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            raise BridgeError(
                f"Bridge computation timed out after {timeout_sec}s",
                code="TIMEOUT",
            )
        except FileNotFoundError:
            raise BridgeError(
                "Rscript not found in PATH",
                code="RSCRIPT_NOT_FOUND",
            )

        # Parse output
        if not out_path.exists():
            raise BridgeError(
                "Bridge output file not created",
                code="NO_OUTPUT",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        with open(out_path, "r") as f:
            output = json.load(f)

        if output.get("status") != "success":
            raise BridgeError(
                output.get("message", "Unknown error"),
                code=output.get("code", "UNKNOWN"),
                stdout=result.stdout,
                stderr=result.stderr,
            )

        return output
