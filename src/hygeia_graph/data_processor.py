"""Data processing and schema.json builder for Hygeia Graph.

This module handles CSV ingestion, data profiling, type inference,
and schema.json contract generation.
"""

import re
from datetime import datetime, timezone
from typing import Any

import pandas as pd


def load_csv(uploaded_file_or_path) -> pd.DataFrame:
    """Load CSV file from Streamlit UploadedFile or filesystem path.

    Args:
        uploaded_file_or_path: Streamlit UploadedFile object or Path/str to CSV file

    Returns:
        Parsed DataFrame

    Raises:
        ValueError: If CSV parsing fails with helpful error message
    """
    try:
        if hasattr(uploaded_file_or_path, "read"):
            # Streamlit UploadedFile
            return pd.read_csv(uploaded_file_or_path)
        else:
            # Path or string
            return pd.read_csv(uploaded_file_or_path)
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}") from e


def make_variable_id(column_name: str, existing_ids: set[str]) -> str:
    """Generate valid variable ID from column name.

    Pattern: ^[A-Za-z_][A-Za-z0-9_\\-]*$

    Args:
        column_name: Original column name
        existing_ids: Set of already-used IDs for deduplication

    Returns:
        Valid, unique variable ID
    """
    # Normalize: strip and lowercase
    var_id = column_name.strip().lower()

    # Replace spaces with underscore
    var_id = var_id.replace(" ", "_")

    # Remove invalid characters (keep letters, digits, underscore, hyphen)
    var_id = re.sub(r"[^a-z0-9_\-]", "", var_id)

    # Strip trailing underscores
    var_id = var_id.rstrip("_")

    # If starts with digit, prefix with "v_"
    if var_id and var_id[0].isdigit():
        var_id = f"v_{var_id}"

    # If empty after cleaning, use generic name
    if not var_id:
        var_id = "var"

    # Deduplicate: append _2, _3, etc. until unique
    base_id = var_id
    counter = 2
    while var_id in existing_ids:
        var_id = f"{base_id}_{counter}"
        counter += 1

    return var_id


def profile_df(df: pd.DataFrame) -> dict[str, Any]:
    """Generate data profiling summary.

    Args:
        df: DataFrame to profile

    Returns:
        Dictionary with profiling metrics:
        - row_count, column_count
        - missing: {cells, rate, by_variable: [{variable_id, cells, rate}]}
        - per_column: {column: {dtype, n_unique, examples}}
    """
    row_count, column_count = df.shape
    total_cells = row_count * column_count

    # Overall missing
    missing_cells = int(df.isna().sum().sum())
    missing_rate = missing_cells / total_cells if total_cells > 0 else 0.0

    # Per-variable missing
    existing_ids: set[str] = set()
    by_variable = []
    per_column = {}

    for col in df.columns:
        var_id = make_variable_id(col, existing_ids)
        existing_ids.add(var_id)

        col_missing = int(df[col].isna().sum())
        col_missing_rate = col_missing / row_count if row_count > 0 else 0.0

        by_variable.append({"variable_id": var_id, "cells": col_missing, "rate": col_missing_rate})

        # Per-column stats
        non_null_values = df[col].dropna()
        n_unique = int(non_null_values.nunique())

        # Get example values (first 3 unique)
        examples = non_null_values.unique()[:3].tolist()

        per_column[col] = {
            "dtype": str(df[col].dtype),
            "n_unique": n_unique,
            "examples": examples,
        }

    return {
        "row_count": row_count,
        "column_count": column_count,
        "missing": {"cells": missing_cells, "rate": missing_rate, "by_variable": by_variable},
        "per_column": per_column,
    }


def infer_variables(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Infer variable specifications from DataFrame.

    Type inference heuristics:
    - Float → Gaussian (g, continuous, level=1)
    - Integer:
      - Non-negative with high uniqueness → count (p, count, level=1)
      - Small consecutive integers → ordinal categorical
      - Otherwise → nominal categorical or Gaussian (if negative)
    - Boolean → categorical (c, nominal, level=2)
    - String/Object → categorical (c, nominal)

    Args:
        df: DataFrame to analyze

    Returns:
        List of variable dictionaries compatible with schema contract
    """
    variables = []
    existing_ids: set[str] = set()

    for col in df.columns:
        var_id = make_variable_id(col, existing_ids)
        existing_ids.add(var_id)

        # Get non-null values for analysis
        non_null = df[col].dropna()
        if len(non_null) == 0:
            # All missing - default to Gaussian
            mgm_type = "g"
            measurement_level = "continuous"
            level = 1
            categories = None
            encoding_strategy = "identity"
            constraints = None
        else:
            dtype = df[col].dtype

            # Float type → Gaussian
            if pd.api.types.is_float_dtype(dtype):
                mgm_type = "g"
                measurement_level = "continuous"
                level = 1
                categories = None
                encoding_strategy = "identity"
                constraints = None

            # Boolean → Categorical with 2 levels
            elif pd.api.types.is_bool_dtype(dtype):
                mgm_type = "c"
                measurement_level = "nominal"
                level = 2
                categories = ["False", "True"]
                encoding_strategy = "categorical_codes"
                constraints = None

            # Integer type → Context-dependent
            elif pd.api.types.is_integer_dtype(dtype):
                n_unique = non_null.nunique()
                n_rows = len(non_null)
                all_non_negative = (non_null >= 0).all()

                if all_non_negative:
                    # High uniqueness → count data
                    # Use stricter threshold: need both high ratio AND many unique values
                    uniqueness_ratio = n_unique / n_rows if n_rows > 0 else 0
                    if n_unique > 20 and uniqueness_ratio >= 0.10:
                        mgm_type = "p"
                        measurement_level = "count"
                        level = 1
                        categories = None
                        encoding_strategy = "count_int"
                        constraints = {"nonnegative": True}
                    else:
                        # Check if consecutive integers (ordinal)
                        unique_vals = sorted(non_null.unique())
                        is_consecutive = all(
                            unique_vals[i + 1] - unique_vals[i] == 1
                            for i in range(len(unique_vals) - 1)
                        )

                        mgm_type = "c"
                        if is_consecutive:
                            measurement_level = "ordinal"
                            encoding_strategy = "ordinal_codes"
                        else:
                            measurement_level = "nominal"
                            encoding_strategy = "categorical_codes"
                        level = n_unique
                        categories = [str(v) for v in unique_vals]
                        constraints = None
                else:
                    # Has negatives → Gaussian
                    mgm_type = "g"
                    measurement_level = "continuous"
                    level = 1
                    categories = None
                    encoding_strategy = "identity"
                    constraints = None

            # String/Object/Category → Categorical
            else:
                mgm_type = "c"
                measurement_level = "nominal"
                unique_vals = sorted(non_null.astype(str).unique())
                level = len(unique_vals)
                categories = unique_vals
                encoding_strategy = "categorical_codes"
                constraints = None

        # Build variable dict
        variable = {
            "id": var_id,
            "column": col,
            "mgm_type": mgm_type,
            "measurement_level": measurement_level,
            "level": level,
            "label": col,  # Default label = column name
        }

        # Add encoding strategy
        variable["encoding"] = {"strategy": encoding_strategy}

        # Add categories if categorical
        if categories is not None:
            variable["categories"] = categories

        # Add constraints if applicable
        if constraints is not None:
            variable["constraints"] = constraints

        variables.append(variable)

    return variables


def build_schema_json(
    df: pd.DataFrame, variables: list[dict[str, Any]], dataset_meta: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build schema.json contract from DataFrame and variable specifications.

    Args:
        df: Source DataFrame
        variables: List of variable specifications (from infer_variables or edited)
        dataset_meta: Optional dataset metadata (name, description, etc.)

    Returns:
        Schema object compatible with contracts/schema.schema.json
    """
    profile = profile_df(df)

    # Build schema object
    schema = {
        "schema_version": "0.1.0",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset": {
            "row_count": profile["row_count"],
            "column_count": profile["column_count"],
            "missing": profile["missing"],
        },
        "variables": variables,
    }

    # Add dataset metadata if provided
    if dataset_meta:
        if "name" in dataset_meta:
            schema["dataset"]["name"] = dataset_meta["name"]
        if "description" in dataset_meta:
            schema["dataset"]["description"] = dataset_meta["description"]
        if "source" in dataset_meta:
            schema["dataset"]["source"] = dataset_meta["source"]

    # Add warnings if missing data detected
    if profile["missing"]["rate"] > 0:
        schema["warnings"] = [
            {
                "level": "warning",
                "code": "MISSING_DATA_DETECTED",
                "message": (
                    "Missing values detected. Hygeia-Graph does not impute; "
                    "please preprocess (e.g., MICE) before modeling."
                ),
            }
        ]

    return schema
