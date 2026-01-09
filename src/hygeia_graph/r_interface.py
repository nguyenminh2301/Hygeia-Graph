"""Python↔R subprocess bridge for MGM execution.

This module provides the interface between Python/Streamlit and the R backend
for running Mixed Graphical Models with EBIC regularization.
"""

import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import pandas as pd

from hygeia_graph.contracts import (
    ContractValidationError,
    validate_model_spec_json,
    validate_results_json,
    validate_schema_json,
)


class RBackendError(Exception):
    """Exception raised when R backend execution fails.

    Attributes:
        message: Error description
        stdout: Captured stdout from R process
        stderr: Captured stderr from R process
        returncode: Process exit code (None if not applicable)
        workdir: Path to working directory (for debugging)
    """

    def __init__(
        self,
        message: str,
        stdout: str = "",
        stderr: str = "",
        returncode: int | None = None,
        workdir: Path | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.workdir = workdir

    def __str__(self) -> str:
        parts = [self.message]
        if self.returncode is not None:
            parts.append(f"Exit code: {self.returncode}")
        if self.stderr:
            parts.append(f"Stderr: {self.stderr[:500]}")
        return " | ".join(parts)


def locate_repo_root(start: Path | None = None) -> Path:
    """Find the repository root directory.

    Ascends from the starting path until finding a directory containing
    both 'contracts' and 'r' subdirectories.

    Args:
        start: Starting path (defaults to this file's directory)

    Returns:
        Path to repository root

    Raises:
        RuntimeError: If repository root cannot be found
    """
    if start is None:
        start = Path(__file__).resolve().parent

    current = start
    for _ in range(10):  # Limit search depth
        contracts_dir = current / "contracts"
        r_dir = current / "r"
        if contracts_dir.is_dir() and r_dir.is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    raise RuntimeError(
        f"Cannot find repository root from {start}. "
        "Expected to find 'contracts/' and 'r/' directories."
    )


def ensure_rscript_available() -> str:
    """Check that Rscript is available on PATH.

    Returns:
        Path to Rscript executable

    Raises:
        RuntimeError: If Rscript is not found
    """
    rscript = shutil.which("Rscript")
    if rscript is None:
        raise RuntimeError(
            "Rscript not found. Please install R and ensure Rscript is on PATH. "
            "Download R from https://cran.r-project.org/"
        )
    return rscript


def compute_sha256(data: bytes) -> str:
    """Compute SHA256 hash of bytes.

    Args:
        data: Bytes to hash

    Returns:
        Lowercase hexadecimal hash string
    """
    return hashlib.sha256(data).hexdigest()


def write_artifacts_to_dir(
    workdir: Path,
    df: pd.DataFrame,
    schema_json: dict[str, Any],
    model_spec_json: dict[str, Any],
) -> dict[str, Any]:
    """Write input artifacts to working directory.

    Args:
        workdir: Directory to write files
        df: DataFrame to export as CSV
        schema_json: Schema object
        model_spec_json: Model spec object

    Returns:
        Dictionary with paths and SHA256 hashes:
        {
            "paths": {"data": Path, "schema": Path, "spec": Path},
            "sha256": {"data": str, "schema": str, "spec": str}
        }
    """
    workdir.mkdir(parents=True, exist_ok=True)

    # Write data.csv
    data_path = workdir / "data.csv"
    df.to_csv(data_path, index=False, encoding="utf-8")
    data_bytes = data_path.read_bytes()
    data_sha256 = compute_sha256(data_bytes)

    # Write schema.json
    schema_path = workdir / "schema.json"
    schema_bytes = json.dumps(schema_json, indent=2).encode("utf-8")
    schema_path.write_bytes(schema_bytes)
    schema_sha256 = compute_sha256(schema_bytes)

    # Write model_spec.json
    spec_path = workdir / "model_spec.json"
    spec_bytes = json.dumps(model_spec_json, indent=2).encode("utf-8")
    spec_path.write_bytes(spec_bytes)
    spec_sha256 = compute_sha256(spec_bytes)

    return {
        "paths": {"data": data_path, "schema": schema_path, "spec": spec_path},
        "sha256": {"data": data_sha256, "schema": schema_sha256, "spec": spec_sha256},
    }


def run_mgm_subprocess(
    df: pd.DataFrame,
    schema_json: dict[str, Any],
    model_spec_json: dict[str, Any],
    *,
    timeout_sec: int = 600,
    keep_workdir: bool = False,
    workdir: Path | None = None,
    quiet: bool = True,
    debug: bool = False,
) -> dict[str, Any]:
    """Run MGM analysis via R subprocess.

    Args:
        df: Input DataFrame (raw data, may contain strings)
        schema_json: Valid schema.json object
        model_spec_json: Valid model_spec.json object
        timeout_sec: Subprocess timeout in seconds (default: 600)
        keep_workdir: If True, don't delete working directory after run
        workdir: Custom working directory (temp dir created if None)
        quiet: Pass --quiet to R script
        debug: Pass --debug to R script

    Returns:
        Dictionary with results and process info:
        {
            "results": dict,  # Validated results.json content
            "paths": {
                "workdir": Path,
                "results_json": Path,
                "data_csv": Path,
                "schema_json": Path,
                "spec_json": Path
            },
            "sha256": {"data": str, "schema": str, "spec": str},
            "process": {
                "returncode": int,
                "stdout": str,
                "stderr": str,
                "timed_out": bool,
                "seconds": float
            }
        }

    Raises:
        ContractValidationError: If input contracts are invalid
        RBackendError: If R execution fails or results are invalid
    """
    # 1. Validate inputs
    validate_schema_json(schema_json)
    validate_model_spec_json(model_spec_json)

    # 2. Locate resources
    rscript = ensure_rscript_available()
    repo_root = locate_repo_root()
    r_script = repo_root / "r" / "run_mgm.R"

    if not r_script.exists():
        raise RBackendError(f"R script not found: {r_script}")

    # 3. Create working directory
    temp_dir = None
    if workdir is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="hygeia_graph_")
        workdir = Path(temp_dir.name)

    try:
        # 4. Write artifacts
        artifacts = write_artifacts_to_dir(workdir, df, schema_json, model_spec_json)
        results_path = workdir / "results.json"

        # 5. Build command
        cmd = [
            rscript,
            str(r_script),
            "--data",
            str(artifacts["paths"]["data"]),
            "--schema",
            str(artifacts["paths"]["schema"]),
            "--spec",
            str(artifacts["paths"]["spec"]),
            "--out",
            str(results_path),
        ]
        if quiet:
            cmd.append("--quiet")
        if debug:
            cmd.append("--debug")

        # 6. Run subprocess
        start_time = time.time()
        timed_out = False
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            returncode = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
        except subprocess.TimeoutExpired as e:
            timed_out = True
            returncode = -1
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            raise RBackendError(
                f"R process timed out after {timeout_sec} seconds",
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
                workdir=workdir,
            ) from e

        elapsed = time.time() - start_time

        # 7. Check results
        if not results_path.exists():
            raise RBackendError(
                "R process did not produce results.json",
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
                workdir=workdir,
            )

        # 8. Load and validate results
        with open(results_path, encoding="utf-8") as f:
            results_obj = json.load(f)

        try:
            validate_results_json(results_obj)
        except ContractValidationError as e:
            error_msgs = "; ".join(f"{err['path']}: {err['message']}" for err in e.errors)
            raise RBackendError(
                f"results.json failed contract validation: {error_msgs}",
                stdout=stdout,
                stderr=stderr,
                returncode=returncode,
                workdir=workdir,
            ) from e

        # 9. Return success
        return {
            "results": results_obj,
            "paths": {
                "workdir": workdir,
                "results_json": results_path,
                "data_csv": artifacts["paths"]["data"],
                "schema_json": artifacts["paths"]["schema"],
                "spec_json": artifacts["paths"]["spec"],
            },
            "sha256": artifacts["sha256"],
            "process": {
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": timed_out,
                "seconds": elapsed,
            },
        }

    finally:
        # Cleanup temp dir unless keeping
        if temp_dir is not None and not keep_workdir:
            try:
                temp_dir.cleanup()
            except Exception:
                pass  # Ignore cleanup errors
