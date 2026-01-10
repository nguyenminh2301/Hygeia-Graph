"""Caching utilities for descriptive statistics."""

import hashlib
import json
from typing import Any, Dict, Optional

import pandas as pd


def compute_dataset_hash(df: pd.DataFrame) -> str:
    """Compute deterministic hash for a DataFrame.

    Args:
        df: Input DataFrame.

    Returns:
        SHA256 hex string.
    """
    csv_bytes = df.to_csv(index=False, lineterminator="\n", na_rep="NA").encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()[:16]


def descriptives_settings_hash(settings: Dict[str, Any], dataset_hash: str) -> str:
    """Compute hash for descriptives settings.

    Args:
        settings: Settings dict.
        dataset_hash: Dataset hash.

    Returns:
        SHA256 hex string.
    """
    combined = json.dumps(settings, sort_keys=True) + dataset_hash
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]


def get_cached_descriptives(
    session_state: Dict,
    dataset_hash: str,
    settings_hash: str,
) -> Optional[Dict[str, Any]]:
    """Get cached descriptives if available.

    Args:
        session_state: Streamlit session state dict.
        dataset_hash: Dataset hash.
        settings_hash: Settings hash.

    Returns:
        Cached result or None.
    """
    cache = session_state.get("descriptives_cache", {})
    return cache.get(dataset_hash, {}).get(settings_hash)


def set_cached_descriptives(
    session_state: Dict,
    dataset_hash: str,
    settings_hash: str,
    result: Dict[str, Any],
) -> None:
    """Cache descriptives result.

    Args:
        session_state: Streamlit session state dict.
        dataset_hash: Dataset hash.
        settings_hash: Settings hash.
        result: Result to cache.
    """
    if "descriptives_cache" not in session_state:
        session_state["descriptives_cache"] = {}
    if dataset_hash not in session_state["descriptives_cache"]:
        session_state["descriptives_cache"][dataset_hash] = {}
    session_state["descriptives_cache"][dataset_hash][settings_hash] = result
