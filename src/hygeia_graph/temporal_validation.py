"""Validation logic for Temporal Network module."""

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd


def detect_time_type(series: pd.Series) -> str:
    """Detect if series is numeric or datetime."""
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    return "unknown"

def check_equal_intervals(df: pd.DataFrame, id_col: str | None, time_col: str) -> Dict[str, Any]:
    """Check if time intervals are consistent per subject."""

    # If time is datetime, convert to numeric (nanoseconds) for diff check
    # If numeric, use as is.

    # Helper to check a single series
    def _check_series(t_ser):
        t_sorted = np.sort(t_ser.dropna().values)
        if len(t_sorted) < 2:
            return True # Too short to have intervals

        diffs = np.diff(t_sorted)
        # We allow small float precision errors?
        # Standard: round to 6 decimal places (or milliseconds)
        # Using a relaxed unique check

        # If integer/datetime-ns, exact. If float, tolerance.
        if np.issubdtype(diffs.dtype, np.integer) or np.issubdtype(diffs.dtype, np.timedelta64):
            unique_diffs = np.unique(diffs)
        else:
             unique_diffs = np.unique(np.round(diffs, 6))

        return len(unique_diffs) <= 1

    if id_col:
        ids = df[id_col].unique()
        unequal_ids = []
        for pid in ids:
            subset = df[df[id_col] == pid]
            if not _check_series(subset[time_col]):
                unequal_ids.append(str(pid))

        if unequal_ids:
            return {
                "ok": False,
                "unequal_ids": unequal_ids,
                "details": f"Found {len(unequal_ids)} subjects with unequal intervals."
            }
    else:
        if not _check_series(df[time_col]):
            return {
                "ok": False,
                "unequal_ids": ["single_subject"],
                "details": "Time column has unequal intervals."
            }

    return {"ok": True, "unequal_ids": [], "details": "Intervals are consistent."}


def validate_temporal_inputs(
    df: pd.DataFrame,
    id_col: str | None,
    time_col: str,
    vars: List[str],
    *,
    advanced_unlock: bool = False,
    unequal_ok: bool = False,
    impute: str = "none"
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate inputs against guardrails.
    Returns: (is_valid, messages, effective_settings)
    """
    messages = []

    # 1. Column Existence
    if time_col not in df.columns:
        return False, [f"Time column '{time_col}' not found."], {}

    missing_vars = [v for v in vars if v not in df.columns]
    if missing_vars:
        return False, [f"Missing variables: {missing_vars}"], {}

    if id_col and id_col not in df.columns:
        return False, [f"ID column '{id_col}' not found."], {}

    # 2. Time Type
    # Must be numeric or sortable. (String time not supported by R runner easily without parsing)
    # We enforce numeric or datetime.
    if detect_time_type(df[time_col]) == "unknown":
         # Try converting? No, strict for now.
         return False, ["Time column must be numeric or datetime."], {}

    # 3. Missing Data
    # Calculate overall missing rate in VARS only
    analysis_df = df[vars]
    total_cells = analysis_df.size
    total_na = analysis_df.isna().sum().sum()
    missing_rate = total_na / total_cells if total_cells > 0 else 0

    if missing_rate > 0:
        if impute == "none":
            messages.append(f"Data has {missing_rate:.1%} missing values. Imputation required.")
            return False, messages, {}

        if missing_rate > 0.20 and not advanced_unlock:
            messages.append(f"High missing rate ({missing_rate:.1%} > 20%). Requires Advanced Unlock to proceed with imputation.")
            return False, messages, {}

    # 4. Length sufficiency
    # Rule: at least 20 rows per subject ideally.
    # We'll block if total N < 20 (single subject) or if ANY subject < 10 (multi)?
    # Simple rule: Total rows >= 20 required.
    if len(df) < 20:
        messages.append("Dataset too small (<20 rows). Cannot run stable VAR.")
        return False, messages, {}

    if id_col:
        # Check per ID
        counts = df[id_col].value_counts()
        short_ids = counts[counts < 10]
        if not short_ids.empty:
            messages.append(f"{len(short_ids)} subjects have <10 timepoints. Remove them or use Advanced Unlock.")
            if not advanced_unlock:
                return False, messages, {}

    # 5. Equal Intervals
    interval_check = check_equal_intervals(df, id_col, time_col)
    if not interval_check["ok"]:
        msg = f"Unequal time intervals detected. {interval_check['details']}"
        messages.append(msg)
        if not unequal_ok:
             messages.append("Must check 'Proceed with unequal intervals' to continue.")
             return False, messages, {}

    return True, messages, {}
