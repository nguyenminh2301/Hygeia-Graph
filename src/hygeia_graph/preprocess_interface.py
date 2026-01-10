"""Interface for R LASSO Feature Selection."""

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import pandas as pd


class PreprocessError(Exception):
    """Raised when Preprocessing analysis fails."""

    def __init__(self, message: str, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.message = message
        self.stdout = stdout
        self.stderr = stderr


def run_lasso_select_subprocess(
    df: pd.DataFrame,
    *,
    target: str,
    family: str = "auto",
    alpha: float = 1.0,
    nfolds: int = 5,
    lambda_rule: str = "lambda.1se",
    max_features: int = 30,
    standardize: bool = True,
    seed: int = 1,
    timeout_sec: int = 3600,
    keep_workdir: bool = False,
    debug: bool = False,
) -> Dict[str, Any]:
    """Execute R LASSO selection via subprocess."""

    # 0. Pre-flight Checks
    if df.isna().any().any():
        raise ValueError(
            "Missing values detected. LASSO requires complete data (or external imputation)."
        )
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found in dataframe.")

    # 1. Setup Workspace
    workdir_obj = tempfile.TemporaryDirectory(prefix="hygeia_lasso_")
    workdir = Path(workdir_obj.name)
    out_dir = workdir / "lasso_out"
    out_dir.mkdir()

    data_path = workdir / "data.csv"
    df.to_csv(data_path, index=False)

    # 2. Build Command
    script_path = Path("r/run_lasso_select.R").resolve()
    if not script_path.exists():
        raise RuntimeError(f"R runner not found at {script_path}")

    cmd = [
        "Rscript",
        str(script_path),
        "--data",
        str(data_path),
        "--target",
        str(target),
        "--out_dir",
        str(out_dir),
        "--family",
        str(family),
        "--alpha",
        str(alpha),
        "--nfolds",
        str(nfolds),
        "--lambda_rule",
        str(lambda_rule),
        "--max_features",
        str(max_features),
        "--standardize",
        "1" if standardize else "0",
        "--seed",
        str(seed),
    ]

    if not debug:
        cmd.append("--quiet")

    # 3. Execute
    start_time = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, check=False)
    except subprocess.TimeoutExpired as e:
        if not keep_workdir:
            workdir_obj.cleanup()
        raise PreprocessError(
            f"LASSO timed out after {timeout_sec}s", stdout=e.stdout or "", stderr=e.stderr or ""
        )

    duration = time.time() - start_time

    # 4. Parse Outputs
    meta_path = out_dir / "lasso_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
        except Exception:
            pass

    if proc.returncode != 0:
        err_msg = meta.get("messages", [{}])[0].get("message") if meta else ""
        full_msg = f"R process failed (code {proc.returncode}). {err_msg}"
        if not keep_workdir:
            workdir_obj.cleanup()
        raise PreprocessError(full_msg, stdout=proc.stdout, stderr=proc.stderr)

    # Load Tables
    coef_df = None
    filtered_df = None

    coef_path = out_dir / "lasso_coefficients.csv"
    if coef_path.exists():
        coef_df = pd.read_csv(coef_path)

    filtered_path = out_dir / "filtered_data.csv"
    if filtered_path.exists():
        filtered_df = pd.read_csv(filtered_path)

    res = {
        "meta": meta,
        "coeff_table": coef_df,
        "filtered_df": filtered_df,
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
