"""Unit tests for Preprocessing module."""

import pandas as pd

from hygeia_graph.preprocess_utils import compute_dataset_hash, lasso_settings_hash


def test_compute_dataset_hash():
    """Test dataset hashing stability."""
    df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    df2 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    df3 = pd.DataFrame({"A": [1, 2], "B": [4, 3]})  # Different

    h1 = compute_dataset_hash(df1)
    h2 = compute_dataset_hash(df2)
    h3 = compute_dataset_hash(df3)

    assert h1 == h2
    assert h1 != h3


def test_lasso_settings_hash():
    """Test settings hashing."""
    ds_hash = "abc1234"
    s1 = {"target": "Y", "alpha": 1.0}

    h1 = lasso_settings_hash(s1, ds_hash)
    h2 = lasso_settings_hash(s1, ds_hash)
    h3 = lasso_settings_hash(s1, "other_ds")

    assert h1 == h2
    assert h1 != h3
