import hashlib
import json
from typing import Any, Dict, Optional


def get_default_navigation() -> str:
    """Return the default navigation page."""
    return "Data & Schema"


def get_default_explore_config(results_json: Optional[Dict] = None) -> Dict[str, Any]:
    """Return default configuration for Explore page."""
    return {
        "threshold": 0.0,
        "use_absolute_weights": True,
        "top_edges": 500,
        "show_labels": True,
        "physics": True,
    }


def normalize_explore_config(
    cfg: Dict[str, Any], results_json: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Validate and clamp explore configuration.

    Args:
        cfg: The configuration dictionary to validate.
        results_json: The results JSON containing edges for threshold validation.

    Returns:
        A normalized configuration dictionary.

    Raises:
        ValueError: If configuration values are invalid.
    """
    # defaults
    top_edges_all_marker = "All"

    # 1. Threshold
    threshold = float(cfg.get("threshold", 0.0))
    if threshold < 0:
        raise ValueError("Threshold must be non-negative.")

    # Clamp to max weight if results available
    if results_json and "edges" in results_json:
        edges = results_json["edges"]
        if edges:
            max_abs_weight = max(abs(e.get("weight", 0.0)) for e in edges)
            if threshold > max_abs_weight:
                threshold = max_abs_weight
        elif threshold > 0:
            # If no edges, threshold must be 0? Or just leave it.
            # Prompt says "max computed ... (fallback 0)".
            # If edges is empty, max is 0.
            threshold = 0.0

    # 2. Top Edges
    top_edges = cfg.get("top_edges", 500)
    # top_edges can be int or "All", check validity
    allowed_top = [200, 500, 1000, top_edges_all_marker]
    if top_edges not in allowed_top:
        raise ValueError(f"top_edges must be one of {allowed_top}")

    return {
        "threshold": threshold,
        "use_absolute_weights": bool(cfg.get("use_absolute_weights", True)),
        "top_edges": top_edges,
        "show_labels": bool(cfg.get("show_labels", True)),
        "physics": bool(cfg.get("physics", True)),
    }


def explore_config_hash(cfg: Dict[str, Any], analysis_id: str) -> str:
    """
    Generate a deterministic hash for the explore configuration and analysis ID.

    Args:
        cfg: Explore configuration dictionary.
        analysis_id: Unique identifier for the analysis.

    Returns:
        SHA256 hash string.
    """
    data = {"analysis_id": str(analysis_id), "config": cfg}
    # Ensure deterministic JSON dump
    dump = json.dumps(data, sort_keys=True)
    return hashlib.sha256(dump.encode("utf-8")).hexdigest()


def get_analysis_id_from_state(
    schema_json: Optional[Dict], model_spec_json: Optional[Dict], results_json: Optional[Dict]
) -> Optional[str]:
    """
    Extract analysis_id from available state objects in priority order.
    Priority: results > model_spec > schema
    """
    if results_json and "analysis_id" in results_json:
        return results_json["analysis_id"]
    if model_spec_json and "analysis_id" in model_spec_json:
        return model_spec_json["analysis_id"]
    if schema_json and "analysis_id" in schema_json:
        return schema_json["analysis_id"]
    return None


# --- Cache Helpers ---


def init_derived_cache(session_state: Dict[str, Any]):
    """Initialize derived_cache in session state if missing."""
    if "derived_cache" not in session_state:
        session_state["derived_cache"] = {}


def get_cached_outputs(
    session_state: Dict[str, Any], analysis_id: str, config_hash: str
) -> Optional[Dict[str, Any]]:
    """Retrieve cached outputs if they exist."""
    init_derived_cache(session_state)
    return session_state["derived_cache"].get(analysis_id, {}).get(config_hash)


def set_cached_outputs(
    session_state: Dict[str, Any], analysis_id: str, config_hash: str, outputs: Dict[str, Any]
):
    """Store outputs in cache."""
    init_derived_cache(session_state)
    if analysis_id not in session_state["derived_cache"]:
        session_state["derived_cache"][analysis_id] = {}
    session_state["derived_cache"][analysis_id][config_hash] = outputs


def clear_analysis_cache(session_state: Dict[str, Any], analysis_id: str):
    """Clear cache for a specific analysis."""
    if analysis_id in session_state["derived_cache"]:
        del session_state["derived_cache"][analysis_id]


def init_robustness_cache(session_state: Dict[str, Any]):
    """Initialize robustness_cache in session state if missing."""
    if "robustness_cache" not in session_state:
        session_state["robustness_cache"] = {}


def get_robustness_cache(
    session_state: Dict[str, Any], analysis_id: str, settings_hash: str
) -> Optional[Dict[str, Any]]:
    """Retrieve cached robustness results."""
    init_robustness_cache(session_state)
    return session_state["robustness_cache"].get(analysis_id, {}).get(settings_hash)


def set_robustness_cache(
    session_state: Dict[str, Any], analysis_id: str, settings_hash: str, results: Dict[str, Any]
):
    """Store robustness results in cache."""
    init_robustness_cache(session_state)
    if analysis_id not in session_state["robustness_cache"]:
        session_state["robustness_cache"][analysis_id] = {}
    session_state["robustness_cache"][analysis_id][settings_hash] = results


def clear_robustness_cache(session_state: Dict[str, Any], analysis_id: str):
    """Clear robustness cache for an analysis."""
    init_robustness_cache(session_state)
    if analysis_id in session_state["robustness_cache"]:
        del session_state["robustness_cache"][analysis_id]

    if analysis_id in session_state["derived_cache"]:
        del session_state["derived_cache"][analysis_id]


# --- UI Feature Gating ---


def can_enable_predictability(r_posthoc_json: Optional[Dict[str, Any]]) -> bool:
    """Check if predictability metrics can be enabled."""
    if not r_posthoc_json:
        return False
    pred = r_posthoc_json.get("predictability", {})
    return bool(pred.get("enabled") and pred.get("by_node"))


def can_enable_communities(r_posthoc_json: Optional[Dict[str, Any]]) -> bool:
    """Check if community visualization can be enabled."""
    if not r_posthoc_json:
        return False
    comm = r_posthoc_json.get("communities", {})
    # Must be enabled and have membership data
    return bool(comm.get("enabled") and comm.get("membership"))


def get_community_counts(membership: Dict[str, str]) -> Dict[str, int]:
    """Count nodes per community."""
    counts = {}
    for _, comm_id in membership.items():
        counts[str(comm_id)] = counts.get(str(comm_id), 0) + 1
    return counts


def map_community_to_colors(membership: Dict[str, str]) -> Dict[str, str]:
    """Generate a deterministic color mapping for communities.

    Returns:
        Dict mapping community_id -> hex color string.
    """
    unique_comms = sorted(list(set(str(c) for c in membership.values())))

    # Standard qualitative palette (Set3-ish or similar)
    palette = [
        "#8dd3c7",
        "#ffffb3",
        "#bebada",
        "#fb8072",
        "#80b1d3",
        "#fdb462",
        "#b3de69",
        "#fccde5",
        "#d9d9d9",
        "#bc80bd",
        "#ccebc5",
        "#ffed6f",
        "#1f78b4",
        "#33a02c",
        "#e31a1c",
        "#ff7f00",
        "#6a3d9a",
        "#b15928",
    ]

    mapping = {}
    for i, comm_id in enumerate(unique_comms):
        # Cycle through palette
        mapping[comm_id] = palette[i % len(palette)]

    return mapping
