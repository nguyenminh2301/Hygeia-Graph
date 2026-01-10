"""Integration tests for LASSO Preprocessing pipeline.

Requires R with glmnet installed. Skips otherwise.
"""

import shutil
import subprocess

import numpy as np
import pandas as pd
import pytest

from hygeia_graph.preprocess_interface import run_lasso_select_subprocess


def has_r_glmnet():
    if not shutil.which("Rscript"):
        return False
    cmd = ["Rscript", "-e", "if(!requireNamespace('glmnet', quietly=TRUE)) quit(status=1)"]
    ret = subprocess.call(cmd)
    return ret == 0


@pytest.mark.skipif(not has_r_glmnet(), reason="R or glmnet not installed")
def test_run_lasso_integration_success():
    """Test successful LASSO run on synthetic data."""
    # Synthetic dataset: Y = 2*X1 - 3*X2 + noise. X3 is noise.
    np.random.seed(42)
    n = 50
    X1 = np.random.normal(0, 1, n)
    X2 = np.random.normal(0, 1, n)
    X3 = np.random.normal(0, 1, n)
    Y = 2 * X1 - 3 * X2 + np.random.normal(0, 0.1, n)

    df = pd.DataFrame({"Y": Y, "X1": X1, "X2": X2, "X3": X3})

    res = run_lasso_select_subprocess(
        df, target="Y", family="gaussian", max_features=2, seed=42, debug=True
    )

    assert res["meta"]["status"] == "success"
    assert res["process"]["returncode"] == 0

    # Check selection
    sel = res["meta"]["selected"]["columns"]
    # Should pick X1 and X2 (strongest)
    assert "X1" in sel
    assert "X2" in sel
    assert "X3" not in sel  # Assuming noise is small enough/filtered by top 2

    # Check filtered DF
    fdf = res["filtered_df"]
    assert "Y" in fdf.columns
    assert "X1" in fdf.columns
    assert "X2" in fdf.columns
    assert len(fdf.columns) == 3  # Y + 2 features


@pytest.mark.skipif(not has_r_glmnet(), reason="R or glmnet not installed")
def test_run_lasso_missing_error():
    """Test error on missing values."""
    df = pd.DataFrame({"Y": [1, 2], "X": [1, np.nan]})
    with pytest.raises(ValueError, match="Missing values detected"):
        run_lasso_select_subprocess(df, target="Y")
