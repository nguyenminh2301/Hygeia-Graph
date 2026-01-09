"""Model specification builder for Hygeia Graph.

This module handles model_spec.json construction with EBIC regularization settings,
edge mapping configuration, and locked design decisions.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any


def default_model_settings() -> dict[str, Any]:
    """Return default model settings with all parameters.

    Returns:
        Settings dictionary with EBIC, edge mapping, and other defaults
    """
    return {
        "engine": {"mode": "subprocess_rscript"},
        "random_seed": 1,
        "mgm": {
            "k": 2,
            "regularization": {
                "lambda_selection": "EBIC",  # LOCKED
                "ebic_gamma": 0.5,
                "alpha": 0.5,
            },
            "rule_reg": "AND",
            "overparameterize": True,
            "scale_gaussian": True,
            "sign_info": True,
        },
        "edge_mapping": {
            "aggregator": "max_abs",
            "sign_strategy": "dominant",
            "zero_tolerance": 1e-12,
        },
        "missing_policy": {"action": "warn_and_abort"},  # LOCKED
        "visualization": {"edge_threshold": 0.0, "layout": "force"},
        "centrality": {"compute": True, "weighted": True, "use_absolute_weights": True},
    }


def sanitize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce user settings to safe values.

    Args:
        settings: User-provided settings dictionary

    Returns:
        Sanitized settings dictionary

    Raises:
        ValueError: If settings cannot be safely corrected
    """
    clean = {}

    # Engine settings
    clean["engine"] = {"mode": settings.get("engine", {}).get("mode", "subprocess_rscript")}

    # Random seed (must be non-negative integer)
    seed = settings.get("random_seed", 1)
    try:
        seed = int(seed)
        if seed < 0:
            seed = 0
    except (TypeError, ValueError):
        seed = 1
    clean["random_seed"] = seed

    # MGM settings
    mgm = settings.get("mgm", {})
    clean["mgm"] = {
        "k": 2,  # Always 2 (pairwise)
        "regularization": {
            "lambda_selection": "EBIC",  # LOCKED - ignore user input
            "ebic_gamma": _clamp_float(
                mgm.get("regularization", {}).get("ebic_gamma", 0.5), 0.0, 1.0
            ),
            "alpha": _clamp_float(mgm.get("regularization", {}).get("alpha", 0.5), 0.0, 1.0),
        },
        "rule_reg": _normalize_enum(mgm.get("rule_reg", "AND"), ["AND", "OR"], default="AND"),
        "overparameterize": bool(mgm.get("overparameterize", True)),
        "scale_gaussian": bool(mgm.get("scale_gaussian", True)),
        "sign_info": bool(mgm.get("sign_info", True)),
    }

    # Edge mapping
    edge_map = settings.get("edge_mapping", {})
    clean["edge_mapping"] = {
        "aggregator": _normalize_enum(
            edge_map.get("aggregator", "max_abs"),
            ["l2_norm", "mean", "max_abs", "max", "mean_abs", "sum_abs"],
            default="max_abs",
        ),
        "sign_strategy": _normalize_enum(
            edge_map.get("sign_strategy", "dominant"),
            ["dominant", "mean", "none"],
            default="dominant",
        ),
        "zero_tolerance": _clamp_float(edge_map.get("zero_tolerance", 1e-12), 0.0, None),
    }

    # Missing policy (LOCKED)
    clean["missing_policy"] = {"action": "warn_and_abort"}

    # Visualization (optional but include defaults)
    viz = settings.get("visualization", {})
    clean["visualization"] = {
        "edge_threshold": _clamp_float(viz.get("edge_threshold", 0.0), 0.0, None),
        "layout": _normalize_enum(
            viz.get("layout", "force"), ["force", "circle", "random"], default="force"
        ),
    }

    # Centrality (optional but include defaults)
    cent = settings.get("centrality", {})
    clean["centrality"] = {
        "compute": bool(cent.get("compute", True)),
        "weighted": bool(cent.get("weighted", True)),
        "use_absolute_weights": bool(cent.get("use_absolute_weights", True)),
    }

    return clean


def build_model_spec(
    schema_json: dict[str, Any],
    settings: dict[str, Any],
    *,
    analysis_id: str | None = None,
    created_at: str | None = None,
    schema_ref: str = "schema.json",
    schema_sha256: str | None = None,
    data_sha256: str | None = None,
) -> dict[str, Any]:
    """Build model_spec.json contract from schema and settings.

    Args:
        schema_json: Valid schema.json object
        settings: Model settings (will be sanitized)
        analysis_id: Optional analysis ID (UUID4 generated if not provided)
        created_at: Optional ISO 8601 timestamp (generated if not provided)
        schema_ref: Reference to schema file (default: "schema.json")
        schema_sha256: Optional SHA256 hash of schema
        data_sha256: Optional SHA256 hash of data

    Returns:
        model_spec.json object compatible with contract schema
    """
    # Sanitize settings to enforce all constraints
    clean_settings = sanitize_settings(settings)

    # Determine analysis_id
    if analysis_id is None:
        # Try to use schema's analysis_id if present
        if "analysis_id" in schema_json:
            final_analysis_id = schema_json["analysis_id"]
        else:
            # Generate new UUID4
            final_analysis_id = str(uuid.uuid4())
    else:
        final_analysis_id = analysis_id

    # Determine created_at
    if created_at is None:
        final_created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        final_created_at = created_at

    # Build model_spec
    spec = {
        "spec_version": "0.1.0",
        "analysis_id": final_analysis_id,
        "created_at": final_created_at,
        "input": {"schema_ref": schema_ref},
        "engine": {"name": "R.mgm", "mode": clean_settings["engine"]["mode"]},
        "random_seed": clean_settings["random_seed"],
        "mgm": clean_settings["mgm"],
        "edge_mapping": clean_settings["edge_mapping"],
        "visualization": clean_settings["visualization"],
        "centrality": clean_settings["centrality"],
        "missing_policy": clean_settings["missing_policy"],
    }

    # Add optional SHA256 hashes if provided
    if schema_sha256 is not None:
        spec["input"]["schema_sha256"] = schema_sha256
    if data_sha256 is not None:
        spec["input"]["data_sha256"] = data_sha256

    return spec


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA256 hash of bytes.

    Args:
        data: Bytes to hash

    Returns:
        Lowercase hexadecimal SHA256 hash
    """
    return hashlib.sha256(data).hexdigest()


# Helper functions


def _clamp_float(value: Any, min_val: float | None, max_val: float | None) -> float:
    """Clamp a value to a float within range."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        # If conversion fails, return middle of range or min
        if min_val is not None and max_val is not None:
            return (min_val + max_val) / 2
        elif min_val is not None:
            return min_val
        else:
            return 0.0

    if min_val is not None and f < min_val:
        return min_val
    if max_val is not None and f > max_val:
        return max_val
    return f


def _normalize_enum(
    value: Any, allowed: list[str], default: str, case_sensitive: bool = True
) -> str:
    """Normalize enum value to one of allowed values."""
    if value is None:
        return default

    str_val = str(value)

    # Try direct match
    if str_val in allowed:
        return str_val

    # Try case-insensitive match
    if not case_sensitive:
        upper_val = str_val.upper()
        for option in allowed:
            if option.upper() == upper_val:
                return option

    # Not found, return default
    return default
