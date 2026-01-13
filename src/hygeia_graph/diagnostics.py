"""Environment diagnostics for Hygeia-Graph.

Provides functions to check R environment health and generate system reports.
"""

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Required R packages by feature
REQUIRED_PACKAGES = ["mgm", "jsonlite", "digest"]
OPTIONAL_PACKAGES = [
    "igraph",
    "bootnet",
    "NetworkComparisonTest",
    "glmnet",
    "qgraph",
    "svglite",
    "networktools",
]



# Explicit overrides for R path
CUSTOM_R_PATHS = [
    r"C:\Program Files\R\R-4.3.3\bin\x64\Rscript.exe",
    r"C:\Program Files\R\R-4.3.3\bin\Rscript.exe",
]

def get_rscript_path() -> Optional[str]:
    """Find Rscript executable path."""
    # 1. Check PATH
    path = shutil.which("Rscript")
    if path:
        return path

    # 2. Check Custom Paths
    for p in CUSTOM_R_PATHS:
        if Path(p).exists():
            return p

    return None

def check_rscript() -> Dict[str, Any]:
    """Check if Rscript is available."""
    rscript_path = get_rscript_path()

    if rscript_path:
        # Get version
        try:
            result = subprocess.run(
                [rscript_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version_info = result.stderr.strip() or result.stdout.strip()
            return {
                "ok": True,
                "path": rscript_path,
                "version": version_info,
                "message": f"Rscript found at {rscript_path}",
            }
        except Exception as e:
            return {
                "ok": True,
                "path": rscript_path,
                "version": "unknown",
                "message": f"Rscript found but version check failed: {e}",
            }
    else:
        return {
            "ok": False,
            "path": None,
            "version": None,
            "message": "Rscript not found in PATH or standard locations. Install R to enable network analysis.",
        }


def check_r_packages(packages: Optional[List[str]] = None, timeout_sec: int = 20) -> Dict[str, Any]:
    """Check which R packages are available."""
    if packages is None:
        packages = REQUIRED_PACKAGES + OPTIONAL_PACKAGES

    # First check if Rscript exists
    r_check = check_rscript()
    if not r_check["ok"]:
        return {
            "ok": False,
            "missing": packages,
            "available": [],
            "message": "Cannot check packages: Rscript not available",
        }

    available = []
    missing = []

    for pkg in packages:
        try:

            cmd = [
                check_rscript()["path"], # Assuming check_rscript() found it if we are hereof
                "-e",
                f"quit(status=ifelse(requireNamespace('{pkg}',quietly=TRUE),0,1))",
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=timeout_sec)
            if result.returncode == 0:
                available.append(pkg)
            else:
                missing.append(pkg)
        except subprocess.TimeoutExpired:
            missing.append(pkg)
        except Exception:
            missing.append(pkg)

    # Check if required packages are missing
    required_missing = [p for p in missing if p in REQUIRED_PACKAGES]
    all_ok = len(required_missing) == 0

    if all_ok:
        msg = f"All required packages available. {len(available)}/{len(packages)} total."
    else:
        msg = f"Missing required packages: {required_missing}"

    return {
        "ok": all_ok,
        "missing": missing,
        "available": available,
        "message": msg,
    }


def run_r_install(keep_log: bool = True, timeout_sec: int = 1200) -> Dict[str, Any]:
    """Run r/install.R to install required packages."""
    r_check = check_rscript()
    if not r_check["ok"]:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "message": "Cannot run installer: Rscript not available",
        }

    install_script = Path("r/install.R")
    if not install_script.exists():
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "message": f"Installer script not found: {install_script}",
        }

    try:
        result = subprocess.run(
            [r_check["path"], str(install_script)],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

        ok = result.returncode == 0

        return {
            "ok": ok,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "message": "Installation completed" if ok else "Installation failed",
        }

    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "message": f"Installation timed out after {timeout_sec}s",
        }
    except Exception as e:
        return {
            "ok": False,
            "stdout": "",
            "stderr": str(e),
            "message": f"Installation error: {e}",
        }


def build_diagnostics_report(
    df: Optional[Any] = None,
    guardrail_triggers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build comprehensive diagnostics report."""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
        },
        "rscript": check_rscript(),
        "r_packages": check_r_packages(),
        "dataset": None,
        "guardrail_triggers": guardrail_triggers or [],
    }

    # Dataset stats
    if df is not None:
        try:
            n_rows, n_cols = df.shape
            missing_count = df.isna().sum().sum()
            total_cells = n_rows * n_cols
            missing_rate = missing_count / total_cells if total_cells > 0 else 0

            report["dataset"] = {
                "n_rows": n_rows,
                "n_cols": n_cols,
                "missing_cells": int(missing_count),
                "missing_rate": float(missing_rate),
            }
        except Exception:
            report["dataset"] = {"error": "Failed to compute dataset stats"}

    return report


def diagnostics_to_json(report: Dict[str, Any]) -> str:
    """Convert diagnostics report to JSON string."""
    return json.dumps(report, indent=2, default=str)
