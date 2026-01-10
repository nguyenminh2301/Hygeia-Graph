"""Integration tests for Bootnet Robustness pipeline.

Requires R with bootnet installed. Skips otherwise.
"""

import shutil
import subprocess

import numpy as np
import pandas as pd
import pytest

from hygeia_graph.robustness_interface import run_bootnet_subprocess


def has_r_bootnet():
    if not shutil.which("Rscript"):
        return False
    # Check package
    cmd = ["Rscript", "-e", "if(!requireNamespace('bootnet', quietly=TRUE)) quit(status=1)"]
    ret = subprocess.call(cmd)
    return ret == 0


@pytest.mark.skipif(not has_r_bootnet(), reason="R or bootnet not installed")
def test_run_bootnet_integration_success():
    """Test successful bootnet run on synthetic data."""
    # 1. Setup Data (3 nodes)
    # Using small N to make it fast? Bootnet might need minimums.
    # N=20, 20 boots.

    df = pd.DataFrame(np.random.normal(size=(30, 3)), columns=["X1", "X2", "X3"])

    schema = {
        "schema_version": "1.0.0",
        "created_at": "2025-01-01T00:00:00Z",
        "dataset": {"row_count": 30, "column_count": 3, "missing": {"cells": 0, "rate": 0}},
        "variables": [
            {
                "id": "X1",
                "column": "X1",
                "mgm_type": "g",
                "measurement_level": "continuous",
                "level": 1,
            },
            {
                "id": "X2",
                "column": "X2",
                "mgm_type": "g",
                "measurement_level": "continuous",
                "level": 1,
            },
            {
                "id": "X3",
                "column": "X3",
                "mgm_type": "g",
                "measurement_level": "continuous",
                "level": 1,
            },
        ],
    }

    spec = {
        "analysis_id": "test-boot-001",
        "mgm": {"regularization": {"ebic_gamma": 0}, "rule_reg": "AND"},
        "full_spec": {},  # Dummy place holder
        "edge_mapping": {"zero_tolerance": 0.01},
        "schema_snapshot": schema,
        "random_seed": 42,
    }

    # 2. Run
    res = run_bootnet_subprocess(
        df,
        schema,
        spec,
        n_boots_np=10,
        n_boots_case=10,
        n_cores=1,
        case_n=5,
        debug=True,
        timeout_sec=120,
    )

    # 3. Assertions
    assert res["meta"]["status"] == "success"
    assert res["process"]["returncode"] == 0

    # Check tables
    edge_sum = res["tables"]["edge_summary"]
    assert edge_sum is not None
    assert "mean" in edge_sum.columns
    # Confirm bootnet ran: CI columns should exist
    assert "q2.5" in edge_sum.columns
    assert "q97.5" in edge_sum.columns

    stab = res["tables"]["centrality_stability"]
    assert stab is not None
    assert "strength" in stab["type"].values or "Strength" in stab["type"].values

    # Check CS
    cs = res["meta"]["cs_coefficient"]
    # Usually strength is present
    assert cs["strength"] is not None


@pytest.mark.skipif(not has_r_bootnet(), reason="R or bootnet not installed")
def test_run_bootnet_missing_values_error():
    """Test Python-side missing value check."""
    df = pd.DataFrame({"A": [1, np.nan], "B": [2, 3]})
    with pytest.raises(ValueError, match="Missing values detected"):
        run_bootnet_subprocess(df, {}, {})
