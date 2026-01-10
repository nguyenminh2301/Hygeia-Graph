"""Interface for Publication Pack R Generator."""

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from hygeia_graph.contracts import validate_results_json, validate_schema_json


class PublicationPackError(Exception):
    """Raised when Publication Pack generation fails."""

    def __init__(self, message: str, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.message = message
        self.stdout = stdout
        self.stderr = stderr


def run_publication_pack_subprocess(
    results_json: Dict[str, Any],
    schema_json: Dict[str, Any],
    derived_metrics_json: Optional[Dict[str, Any]] = None,
    *,
    threshold: float = 0.0,
    use_abs_filter: bool = True,
    top_edges: int = 500,
    show_labels: bool = True,
    layout: str = "spring",
    width: float = 10.0,
    height: float = 8.0,
    timeout_sec: int = 900,
    keep_workdir: bool = False,
) -> Dict[str, Any]:
    """Execute R script to generate figures and tables."""

    # Validate Inputs
    validate_results_json(results_json)
    validate_schema_json(schema_json)

    # Setup Workdir
    workdir_obj = tempfile.TemporaryDirectory(prefix="hygeia_pubpack_")
    workdir = Path(workdir_obj.name)
    out_dir = workdir / "publication_pack_out"
    out_dir.mkdir()

    # Write Inputs
    results_path = workdir / "results.json"
    with open(results_path, "w") as f:
        json.dump(results_json, f)

    schema_path = workdir / "schema.json"
    with open(schema_path, "w") as f:
        json.dump(schema_json, f)

    derived_path_str = "NULL"
    if derived_metrics_json:
        derived_path = workdir / "derived_metrics.json"
        with open(derived_path, "w") as f:
            json.dump(derived_metrics_json, f)
        derived_path_str = str(derived_path)

    # Build Command
    script_path = Path("r/run_publication_pack.R").resolve()
    if not script_path.exists():
        raise RuntimeError(f"R script not found at {script_path}")

    cmd = [
        "Rscript",
        str(script_path),
        "--results",
        str(results_path),
        "--schema",
        str(schema_path),
        "--out_dir",
        str(out_dir),
        "--threshold",
        str(threshold),
        "--use_abs_filter",
        "1" if use_abs_filter else "0",
        "--top_edges",
        str(top_edges),
        "--show_labels",
        "1" if show_labels else "0",
        "--layout",
        str(layout),
        "--width",
        str(width),
        "--height",
        str(height),
    ]

    if derived_metrics_json:
        cmd.extend(["--derived", derived_path_str])

    # Execute
    start_time = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, check=False)
    except subprocess.TimeoutExpired as e:
        if not keep_workdir:
            workdir_obj.cleanup()
        raise PublicationPackError(
            f"Publication Pack timed out after {timeout_sec}s",
            stdout=e.stdout or "",
            stderr=e.stderr or "",
        )

    duration = time.time() - start_time

    # Check Meta
    meta_path = out_dir / "meta" / "publication_pack_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
        except Exception:
            pass

    if proc.returncode != 0:
        err_msg = ""
        if meta and meta.get("messages"):
            err_msg = meta["messages"][0].get("message", "")

        full_msg = f"R process failed (code {proc.returncode}). {err_msg}"
        if not keep_workdir:
            workdir_obj.cleanup()
        raise PublicationPackError(full_msg, stdout=proc.stdout, stderr=proc.stderr)

    # Collect Outputs
    # Paths relative to out_dir
    files_res = {"figures": [], "tables": []}

    # Walk output dir
    figures_dir = out_dir / "figures"
    if figures_dir.exists():
        for p in figures_dir.glob("*.*"):
            files_res["figures"].append(str(p))

    tables_dir = out_dir / "tables"
    if tables_dir.exists():
        for p in tables_dir.glob("*.*"):
            files_res["tables"].append(str(p))

    # Load Adjacency Table if exists (Optional, mostly for ZIP)
    # We return paths mainly. The caller (Utils) will zip them.

    res = {
        "meta": meta,
        "paths": {
            "workdir": str(workdir),
            "out_dir": str(out_dir),
            "meta_json": str(meta_path),
            "figures_dir": str(figures_dir),
            "tables_dir": str(tables_dir),
        },
        "files": files_res,
        "process": {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "seconds": duration,
        },
    }

    # NOTE: We keep workdir alive if caller wants to read files?
    # Actually, we should allow caller to handle cleanup or return object.
    # But usually we return paths to temp files, so we MUST NOT cleanup immediately if we return paths.
    # Wait, Reference: other interfaces (bootnet/lasso) read DF then cleanup.
    # Here we have binary files (SVG/PDF). Reading them all into memory is bad?
    # No, SVG/PDFs are small. But ZIP building needs them.
    # Strategy: ZIP builder should run while temp dir exists.
    # We will NOT cleanup here. We return the cleanup handle?
    # Or simplified: We assume caller will cleanup workdir if we return path.
    # Actually, `TemporaryDirectory` cleans up on object GC.
    # If we return `workdir_obj` reference, it stays alive.

    res["_workdir_obj"] = workdir_obj  # Keep alive

    return res
