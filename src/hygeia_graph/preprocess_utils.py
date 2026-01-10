"""Utilities for Preprocessing module (hashing, caching)."""

import hashlib
import json
from typing import Any, Dict

import pandas as pd


def compute_dataset_hash(df: pd.DataFrame) -> str:
    """Compute stable hash for DataFrame content."""
    # Use pandas utility to get consistent object hash if possible
    # Simplest: hash the values bytes? Or hash of described stats?
    # For strict reproducibility, we iterate columns/types.
    # Fast approach for medium data: hash of csv string (memory heavy?).
    # Better: hash of shape + column names + sample values?
    # Let's use utility from hash_pandas_object if available, else simple aggregation.

    try:
        from pandas.util import hash_pandas_object

        h = hash_pandas_object(df)
        return hashlib.sha256(pd.Series(h).values.tobytes()).hexdigest()
    except ImportError:
        # Fallback: JSON dump of head + tail + shape
        # Sufficient for session-based caching
        subset = (
            str(df.shape)
            + str(df.columns.tolist())
            + str(df.head(5).values)
            + str(df.tail(5).values)
        )
        return hashlib.sha256(subset.encode("utf-8")).hexdigest()


def lasso_settings_hash(settings: Dict[str, Any], dataset_hash: str) -> str:
    """Generate deterministic hash for LASSO settings + dataset."""
    keys = [
        "target",
        "family",
        "alpha",
        "nfolds",
        "lambda_rule",
        "max_features",
        "standardize",
        "seed",
    ]
    subset = {k: settings.get(k) for k in keys if k in settings}

    data = {"dataset_hash": dataset_hash, "settings": subset}
    dump = json.dumps(data, sort_keys=True)
    return hashlib.sha256(dump.encode("utf-8")).hexdigest()
