"""R Subprocess Interface for Temporal Networks."""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from hygeia_graph.temporal_validation import validate_temporal_inputs


def run_temporal_var_subprocess(
    df: pd.DataFrame,
    *,
    id_col: Optional[str],
    time_col: str,
    vars: List[str],
    gamma: float = 0.5,
    n_lambda: int = 50,
    scale: bool = True,
    detrend: bool = False,
    impute: str = "none",
    unequal_ok: bool = False,
    seed: int = 1,
    advanced_unlock: bool = False,
    timeout_sec: int = 600
) -> Dict[str, Any]:
    """
    Run r/run_temporal_var.R in a subprocess.
    """

    # 1. Validation (Double check)
    is_valid, msgs, _ = validate_temporal_inputs(
        df, id_col, time_col, vars,
        advanced_unlock=advanced_unlock,
        unequal_ok=unequal_ok,
        impute=impute
    )
    if not is_valid:
        return {
            "status": "failed",
            "error": "Validation failed",
            "messages": msgs
        }

    # 2. Setup Temp Dir
    temp_dir = tempfile.mkdtemp(prefix="hygeia_temporal_")
    data_path = os.path.join(temp_dir, "data.csv")
    out_dir = os.path.join(temp_dir, "out")

    try:
        # Write Data
        # Ensure we write only needed cols to keep it clean, but keep ID/Time
        cols_to_write = [time_col] + vars
        if id_col:
            cols_to_write.insert(0, id_col)

        # Write CSV
        df[cols_to_write].to_csv(data_path, index=False)

        # 3. Build Command
        # Resolve script path relative to this file?
        # Assuming we are running from root or src... best to rely on relative from root
        # or use known absolute logic.
        # This file is in src/hygeia_graph/temporal_interface.py
        # Root is ../../../

        root_dir = Path(__file__).resolve().parent.parent.parent
        r_script = root_dir / "r" / "run_temporal_var.R"

        if not r_script.exists():
            return {"status": "failed", "error": f"R script not found at {r_script}"}

        from hygeia_graph.diagnostics import get_rscript_path
        r_cmd = get_rscript_path()
        if not r_cmd:
            return {"status": "failed", "error": "Rscript not found"}

        cmd = [
            r_cmd,
            str(r_script),
            "--data", data_path,
            "--time_col", time_col,
            "--vars", ",".join(vars),
            "--out_dir", out_dir,
            "--gamma", str(gamma),
            "--n_lambda", str(n_lambda),
            "--scale", "1" if scale else "0",
            "--detrend", "1" if detrend else "0",
            "--impute", impute,
            "--unequal_ok", "1" if unequal_ok else "0",
            "--seed", str(seed)
        ]

        if id_col:
            cmd.extend(["--id_col", id_col])

        # 4. Execute
        start_t = time.time()
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=str(root_dir) # Execute from root so relative imports inside R work if any
        )
        duration = time.time() - start_t

        # 5. Parse Outputs
        meta = {}
        meta_path = Path(out_dir) / "meta" / "temporal_meta.json"

        tables = {}

        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception as e:
                meta = {"status": "failed", "error": f"JSON load error: {e}"}
        else:
             meta = {
                 "status": "failed",
                 "error": "No meta file produced",
                 "stderr": proc.stderr
             }

        if meta.get("status") == "success":
            # Load tables
            t_path = Path(out_dir) / "tables"

            def load_safe(fname):
                p = t_path / fname
                if p.exists():
                    return pd.read_csv(p)
                return None

            tables["PDC"] = load_safe("PDC.csv")
            tables["PCC"] = load_safe("PCC.csv")
            tables["temporal_edges"] = load_safe("temporal_edges.csv")
            tables["contemporaneous_edges"] = load_safe("contemporaneous_edges.csv")

        return {
            "meta": meta,
            "tables": tables,
            "process": {
                "returncode": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "duration": duration
            }
        }

    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": "Timeout expired"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
