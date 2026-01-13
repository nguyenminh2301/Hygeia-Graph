"""Integration test for Temporal VAR module (Optional)."""


import numpy as np
import pandas as pd
import pytest

from hygeia_graph.diagnostics import check_r_packages
from hygeia_graph.temporal_interface import run_temporal_var_subprocess


# Skip if graphicalVAR not installed
def r_has_graphicalvar():
    res = check_r_packages(["graphicalVAR"])
    return res["ok"]

@pytest.mark.skipif(not r_has_graphicalvar(), reason="graphicalVAR R package missing")
def test_temporal_integration_flow():
    """
    End-to-end integration test:
    1. Create synthetic time series (VAR(1) process).
    2. Run run_temporal_var_subprocess.
    3. Verify output structure.
    """

    # 1. Generate Data
    np.random.seed(42)
    n = 100
    p = 3
    # Simple VAR: X_t = 0.5 * X_{t-1} + e
    X = np.zeros((n, p))
    for i in range(1, n):
        X[i] = 0.5 * X[i-1] + np.random.normal(0, 1, p)

    df = pd.DataFrame(X, columns=["v1", "v2", "v3"])
    df["time"] = range(n)

    # 2. Run
    # Single subject mode
    res = run_temporal_var_subprocess(
        df,
        id_col=None,
        time_col="time",
        vars=["v1", "v2", "v3"],
        gamma=0.0, # Low regularisation to ensure edges
        detrend=False,
        seed=123
    )

    # 3. Assertions
    assert res["meta"]["status"] == "success"

    tables = res["tables"]
    assert "PDC" in tables
    assert "PCC" in tables
    assert "temporal_edges" in tables

    # Check dimensions
    pdc = tables["PDC"]
    assert pdc.shape == (3, 3) # p x p matrix

    # Check edge content
    edges = tables["temporal_edges"]
    # We generated autoregressive effects, so v1->v1, v2->v2, v3->v3 should prevent it from being empty
    # unless LASSO killed it. With gamma=0, unlikely.
    assert not edges.empty
    assert "source" in edges.columns
    assert "target" in edges.columns
    assert "weight" in edges.columns
