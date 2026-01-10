"""Interface for R bootnet analysis (Robustness)."""

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from hygeia_graph.contracts import validate_model_spec_json, validate_schema_json


class RobustnessError(Exception):
    """Raised when Bootnet analysis fails."""

    def __init__(self, message: str, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.message = message
        self.stdout = stdout
        self.stderr = stderr


def run_bootnet_subprocess(
    df: pd.DataFrame,
    schema_json: Dict[str, Any],
    model_spec_json: Dict[str, Any],
    *,
    n_boots_np: int = 200,
    n_boots_case: int = 200,
    n_cores: int = 1,
    case_min: float = 0.05,
    case_max: float = 0.75,
    case_n: int = 10,
    cor_level: float = 0.7,
    timeout_sec: int = 3600,
    keep_workdir: bool = False,
    debug: bool = False,
) -> Dict[str, Any]:
    """Execute R bootnet workflow via subprocess.

    Args:
        df: Input DataFrame (must handle missing check prior).
        schema_json: Hygeia-Graph schema.
        model_spec_json: Hygeia-Graph model spec.
        ... bootnet params ...

    Returns:
        Dict structure: {
            "meta": dict,
            "tables": {"edge_summary": DF, "edge_ci_flag": DF, "centrality_stability": DF},
            "paths": {...},
            "process": {...}
        }
    """
    # 0. Pre-flight Checks
    if df.isna().any().any():
        raise ValueError("Missing values detected. Bootnet requires complete data.")

    validate_schema_json(schema_json)
    validate_model_spec_json(model_spec_json)

    # 1. Setup Workspace
    workdir_obj = tempfile.TemporaryDirectory(prefix="hygeia_bootnet_")
    workdir = Path(workdir_obj.name)

    out_dir = workdir / "bootnet_out"
    out_dir.mkdir()

    # Paths
    data_path = workdir / "data.csv"
    schema_path = workdir / "schema.json"
    spec_path = workdir / "model_spec.json"

    # Write inputs
    df.to_csv(data_path, index=False)
    with open(schema_path, "w") as f:
        json.dump(schema_json, f)
    with open(spec_path, "w") as f:
        json.dump(model_spec_json, f)

    # 2. Build Command
    script_path = Path("r/run_bootnet.R").resolve()
    if not script_path.exists():
        raise RuntimeError(f"R runner not found at {script_path}")

    cmd = [
        "Rscript",
        str(script_path),
        "--data",
        str(data_path),
        "--schema",
        str(schema_path),
        "--spec",
        str(spec_path),
        "--out_dir",
        str(out_dir),
        "--n_boots_np",
        str(n_boots_np),
        "--n_boots_case",
        str(n_boots_case),
        "--n_cores",
        str(n_cores),
        "--caseMin",
        str(case_min),
        "--caseMax",
        str(case_max),
        "--caseN",
        str(case_n),
        "--cor_level",
        str(cor_level),
    ]

    if not debug:
        cmd.append("--quiet")

    # 3. Execute
    start_time = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,  # We handle returncode manually
        )
    except subprocess.TimeoutExpired as e:
        if not keep_workdir:
            workdir_obj.cleanup()
        raise RobustnessError(
            f"Bootnet timed out after {timeout_sec}s", stdout=e.stdout or "", stderr=e.stderr or ""
        )

    duration = time.time() - start_time

    # 4. Parse Outputs
    meta_path = out_dir / "bootnet_meta.json"
    meta = {}

    # Load meta if exists
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
        except Exception:
            pass

    # Check process success
    if proc.returncode != 0:
        err_msg = meta.get("messages", [{}])[0].get("message") if meta else ""
        full_msg = f"R process failed (code {proc.returncode}). {err_msg}"
        if not keep_workdir:
            workdir_obj.cleanup()
        raise RobustnessError(full_msg, stdout=proc.stdout, stderr=proc.stderr)

    # Load Tables
    tables = {"edge_summary": None, "edge_ci_flag": None, "centrality_stability": None}

    def load_table(name: str):
        p = out_dir / f"{name}.csv"
        if p.exists():
            return pd.read_csv(p)
        return None

    tables["edge_summary"] = load_table("edge_summary")
    tables["edge_ci_flag"] = load_table("edge_ci_flag")
    tables["centrality_stability"] = load_table("centrality_stability")

    # Result
    res = {
        "meta": meta,
        "tables": tables,
        "paths": {"workdir": str(workdir), "out_dir": str(out_dir)},
        "process": {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "seconds": duration,
        },
    }

    if not keep_workdir:
        workdir_obj.cleanup()

    return res
