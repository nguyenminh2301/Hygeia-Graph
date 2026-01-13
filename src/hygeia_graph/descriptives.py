"""Descriptive statistics for dataset variables.

Computes summaries, missing values, and distribution tests for all variables.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Check for scipy availability
try:
    from scipy import stats as scipy_stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def classify_variables(
    df: pd.DataFrame,
    schema_json: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """Classify variables by type.

    Args:
        df: Input DataFrame.
        schema_json: Optional validated schema.

    Returns:
        List of variable descriptors.
    """
    variables = []

    if schema_json and "variables" in schema_json:
        # Use schema
        for var in schema_json["variables"]:
            col = var.get("column", var.get("id"))
            if col not in df.columns:
                continue

            mgm_type = var.get("mgm_type", "unknown")
            level = var.get("measurement_level", var.get("level", "unknown"))
            categories = var.get("categories")

            variables.append({
                "var_id": var.get("id", col),
                "column": col,
                "mgm_type": mgm_type,
                "measurement_level": level,
                "is_numeric": mgm_type in ("g", "p"),
                "is_categorical": mgm_type == "c",
                "categories": categories,
            })
    else:
        # Infer from data
        for col in df.columns:
            series = df[col]
            dtype = series.dtype

            if pd.api.types.is_float_dtype(dtype):
                variables.append({
                    "var_id": col,
                    "column": col,
                    "mgm_type": "g",
                    "measurement_level": "continuous",
                    "is_numeric": True,
                    "is_categorical": False,
                    "categories": None,
                })
            elif pd.api.types.is_integer_dtype(dtype):
                nunique = series.nunique()
                if (series.dropna() >= 0).all() and nunique > 10:
                    # Likely count
                    variables.append({
                        "var_id": col,
                        "column": col,
                        "mgm_type": "p",
                        "measurement_level": "count",
                        "is_numeric": True,
                        "is_categorical": False,
                        "categories": None,
                    })
                else:
                    # Ordinal
                    variables.append({
                        "var_id": col,
                        "column": col,
                        "mgm_type": "c",
                        "measurement_level": "ordinal",
                        "is_numeric": False,
                        "is_categorical": True,
                        "categories": sorted(series.dropna().unique().tolist()),
                    })
            else:
                # Object/categorical
                variables.append({
                    "var_id": col,
                    "column": col,
                    "mgm_type": "c",
                    "measurement_level": "nominal",
                    "is_numeric": False,
                    "is_categorical": True,
                    "categories": series.dropna().unique().tolist(),
                })

    return variables


def compute_missing_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute missing value summary.

    Args:
        df: Input DataFrame.

    Returns:
        Missing summary dict.
    """
    n_rows, n_cols = df.shape
    total_cells = n_rows * n_cols
    missing_cells = int(df.isna().sum().sum())
    missing_rate = missing_cells / total_cells if total_cells > 0 else 0.0

    by_column = {}
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        by_column[col] = {
            "missing": n_missing,
            "rate": n_missing / n_rows if n_rows > 0 else 0.0,
        }

    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "missing_cells": missing_cells,
        "missing_rate": round(missing_rate, 4),
        "by_column": by_column,
    }


def normality_test(series: pd.Series) -> Dict[str, Any]:
    """Run normality test on a series.

    Args:
        series: Numeric series.

    Returns:
        Test result dict.
    """
    clean = series.dropna()
    n = len(clean)

    if not SCIPY_AVAILABLE:
        return {
            "test": "unavailable",
            "p_value": None,
            "n_used": n,
            "note": "scipy not installed",
        }

    if n < 8:
        return {
            "test": "skipped",
            "p_value": None,
            "n_used": n,
            "note": "n < 8, insufficient data",
        }

    try:
        if n <= 5000:
            stat, p = scipy_stats.shapiro(clean)
            return {
                "test": "shapiro",
                "p_value": round(float(p), 6),
                "n_used": n,
                "note": "",
            }
        else:
            # Sample deterministically
            np.random.seed(0)
            sample = clean.sample(5000, random_state=0)
            stat, p = scipy_stats.normaltest(sample)
            return {
                "test": "normaltest",
                "p_value": round(float(p), 6),
                "n_used": 5000,
                "note": "sampled 5000 for large n",
            }
    except Exception as e:
        return {
            "test": "skipped",
            "p_value": None,
            "n_used": n,
            "note": str(e),
        }


def poisson_diagnostics(series: pd.Series) -> Dict[str, Any]:
    """Run Poisson diagnostics on a count series.

    Args:
        series: Count series (non-negative integers).

    Returns:
        Diagnostics dict.
    """
    clean = series.dropna()

    # Check if valid counts
    if not pd.api.types.is_integer_dtype(clean) or (clean < 0).any():
        return {
            "mean": None,
            "var": None,
            "dispersion_ratio": None,
            "gof_test": "skipped",
            "gof_p_value": None,
            "note": "not valid count data",
        }

    if len(clean) < 5:
        return {
            "mean": None,
            "var": None,
            "dispersion_ratio": None,
            "gof_test": "skipped",
            "gof_p_value": None,
            "note": "insufficient data",
        }

    mean_val = float(clean.mean())
    var_val = float(clean.var())
    dispersion = var_val / mean_val if mean_val > 0 else None

    result = {
        "mean": round(mean_val, 4),
        "var": round(var_val, 4),
        "dispersion_ratio": round(dispersion, 4) if dispersion else None,
        "gof_test": "skipped",
        "gof_p_value": None,
        "note": "",
    }

    return result


def summarize_continuous(series: pd.Series) -> Dict[str, Any]:
    """Summarize continuous variable.

    Args:
        series: Numeric series.

    Returns:
        Summary dict.
    """
    clean = series.dropna()

    if len(clean) == 0:
        return {
            "mean": None, "sd": None, "median": None,
            "q1": None, "q3": None, "iqr": None,
            "min": None, "max": None,
        }

    q1 = float(clean.quantile(0.25))
    q3 = float(clean.quantile(0.75))

    return {
        "mean": round(float(clean.mean()), 4),
        "sd": round(float(clean.std()), 4),
        "median": round(float(clean.median()), 4),
        "q1": round(q1, 4),
        "q3": round(q3, 4),
        "iqr": round(q3 - q1, 4),
        "min": round(float(clean.min()), 4),
        "max": round(float(clean.max()), 4),
    }


def summarize_categorical(
    series: pd.Series,
    categories_order: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Summarize categorical variable.

    Args:
        series: Categorical series.
        categories_order: Optional ordering for levels.

    Returns:
        Tuple of (summary dict, levels DataFrame).
    """
    clean = series.dropna().astype(str)
    counts = clean.value_counts()

    if categories_order:
        # Reorder
        counts = counts.reindex(categories_order, fill_value=0)

    total = counts.sum()
    rates = counts / total if total > 0 else counts * 0

    levels_df = pd.DataFrame({
        "level": counts.index,
        "count": counts.values,
        "rate": rates.values,
    })

    # Calculate entropy
    probs = rates.values
    probs = probs[probs > 0]
    entropy = -np.sum(probs * np.log2(probs)) if len(probs) > 0 else 0.0

    top_level = counts.idxmax() if len(counts) > 0 else None
    top_rate = float(rates.max()) if len(rates) > 0 else 0.0

    summary = {
        "n_levels": len(counts),
        "top_level": top_level,
        "top_level_rate": round(top_rate, 4),
        "entropy": round(entropy, 4),
        "mode": top_level,
    }

    return summary, levels_df


def build_variable_summary_table(
    df: pd.DataFrame,
    variables: List[Dict[str, Any]],
    run_normality: bool = True,
) -> pd.DataFrame:
    """Build summary table for all variables.

    Args:
        df: Input DataFrame.
        variables: Variable descriptors from classify_variables.
        run_normality: Whether to run normality tests.

    Returns:
        Summary DataFrame with one row per variable.
    """
    rows = []

    for var in variables:
        col = var["column"]
        series = df[col]
        n_total = len(series)
        n_missing = int(series.isna().sum())
        n_nonmissing = n_total - n_missing

        row = {
            "var_id": var["var_id"],
            "column": col,
            "mgm_type": var["mgm_type"],
            "measurement_level": var["measurement_level"],
            "n_total": n_total,
            "n_nonmissing": n_nonmissing,
            "n_missing": n_missing,
            "missing_rate": round(n_missing / n_total, 4) if n_total > 0 else 0.0,
        }

        if var["is_numeric"]:
            # Continuous or count
            stats = summarize_continuous(series)
            row.update(stats)

            if var["measurement_level"] == "continuous" and run_normality:
                norm = normality_test(series)
                row["dist_test"] = norm["test"]
                row["dist_p_value"] = norm["p_value"]
                row["dist_n_used"] = norm["n_used"]

            if var["measurement_level"] == "count":
                pois = poisson_diagnostics(series)
                row["dispersion_ratio"] = pois["dispersion_ratio"]

        elif var["is_categorical"]:
            # Categorical
            cat_summary, _ = summarize_categorical(series, var.get("categories"))
            row["n_levels"] = cat_summary["n_levels"]
            row["top_level"] = cat_summary["top_level"]
            row["top_level_rate"] = cat_summary["top_level_rate"]
            row["entropy"] = cat_summary["entropy"]

        rows.append(row)

    return pd.DataFrame(rows)


def build_categorical_levels_table(
    df: pd.DataFrame,
    variables: List[Dict[str, Any]],
) -> pd.DataFrame:
    """Build long-format table for categorical/ordinal variables.

    Args:
        df: Input DataFrame.
        variables: Variable descriptors.

    Returns:
        Levels DataFrame.
    """
    all_levels = []

    for var in variables:
        if not var["is_categorical"]:
            continue

        col = var["column"]
        _, levels_df = summarize_categorical(df[col], var.get("categories"))
        levels_df["var_id"] = var["var_id"]
        levels_df["column"] = col
        all_levels.append(levels_df)

    if all_levels:
        return pd.concat(all_levels, ignore_index=True)[
            ["var_id", "column", "level", "count", "rate"]
        ]
    return pd.DataFrame(columns=["var_id", "column", "level", "count", "rate"])


def build_descriptives_payload(
    missing_summary: Dict[str, Any],
    variable_summary_df: pd.DataFrame,
) -> Dict[str, Any]:
    """Build JSON payload for report integration.

    Args:
        missing_summary: Missing value summary.
        variable_summary_df: Variable summary table.

    Returns:
        Payload dict.
    """
    # Count variable types
    n_continuous = len(
        variable_summary_df[variable_summary_df["measurement_level"] == "continuous"]
    )
    n_count = len(variable_summary_df[variable_summary_df["measurement_level"] == "count"])
    n_nominal = len(variable_summary_df[variable_summary_df["measurement_level"] == "nominal"])
    n_ordinal = len(variable_summary_df[variable_summary_df["measurement_level"] == "ordinal"])

    # Normality stats
    if "dist_p_value" in variable_summary_df.columns:
        tested = variable_summary_df[variable_summary_df["dist_p_value"].notna()]
        n_tested = len(tested)
        n_non_normal = len(tested[tested["dist_p_value"] < 0.05])
    else:
        n_tested = 0
        n_non_normal = 0

    # Top missing
    top_missing = (
        variable_summary_df[["var_id", "missing_rate"]]
        .sort_values("missing_rate", ascending=False)
        .head(10)
        .to_dict("records")
    )

    messages = []
    if not SCIPY_AVAILABLE:
        messages.append({
            "level": "warning",
            "code": "SCIPY_NOT_AVAILABLE",
            "message": "scipy not installed; normality tests unavailable.",
        })

    return {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": missing_summary["n_rows"],
        "n_cols": missing_summary["n_cols"],
        "missing_rate": missing_summary["missing_rate"],
        "missing_cells": missing_summary["missing_cells"],
        "variables": {
            "n_total": len(variable_summary_df),
            "n_continuous": n_continuous,
            "n_count": n_count,
            "n_nominal": n_nominal,
            "n_ordinal": n_ordinal,
        },
        "normality": {
            "n_tested": n_tested,
            "n_non_normal_p_lt_0_05": n_non_normal,
        },
        "top_missing": top_missing,
        "messages": messages,
    }
