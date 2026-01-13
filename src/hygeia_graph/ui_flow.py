"""UI workflow helpers for navigation, state management, and ZIP export."""

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, MutableMapping, Optional

# Page order and navigation
PAGES = [
    "Data & Schema",
    "Model Settings",
    "Run MGM",
    "Explore",
    "Report & Export",
]

# Analysis goals
ANALYSIS_GOALS = {
    "explore": "Explore network (default)",
    "comparison": "Compare groups (NCT)",
    "robustness": "Robustness (bootnet)",
    "lasso": "Feature selection first (LASSO)",
    "publication": "Publication-ready figures",
}

# Keys to clear
CLEARABLE_KEYS = [
    "df", "uploaded_filename",
    "schema_obj", "schema_json", "schema_valid",
    "model_spec_obj", "model_spec_json",
    "results_json", "results_status",
    "derived_metrics_json", "r_posthoc_json",
    "derived_cache", "robustness_cache", "comparison_cache",
    "preprocess_cache", "simulation_cache", "publication_cache",
    "bootnet_meta", "bootnet_tables", "bootnet_cache",
    "nct_meta", "nct_summary", "nct_edge_table",
    "descriptives_payload", "descriptives_var_summary", "descriptives_cat_levels",
    "insights_report", "explore_config",
    "temp_paths", "workdir",
    "analysis_goal",
]


def get_next_page(
    current_page: str,
    analysis_goal: str = "explore",
    state_flags: Optional[Dict[str, bool]] = None,
) -> Optional[str]:
    """Determine the next page based on current state.

    Args:
        current_page: Current page name.
        analysis_goal: User's analysis goal.
        state_flags: Dict of state conditions (schema_ready, spec_ready, mgm_success).

    Returns:
        Next page name or None.
    """
    flags = state_flags or {}

    if current_page == "Data & Schema":
        if flags.get("schema_ready"):
            if analysis_goal == "lasso":
                return "Preprocessing"
            return "Model Settings"
        return None

    if current_page == "Model Settings":
        if flags.get("spec_ready"):
            return "Run MGM"
        return None

    if current_page == "Run MGM":
        if flags.get("mgm_success"):
            if analysis_goal == "comparison":
                return "Comparison"
            if analysis_goal == "robustness":
                return "Robustness"
            if analysis_goal == "publication":
                return "Report & Export"
            return "Explore"
        return None

    if current_page == "Explore":
        return "Report & Export"

    return None


def clear_all_state(session_state: MutableMapping) -> List[str]:
    """Clear all analysis data and caches from session state.

    Args:
        session_state: Streamlit session state or dict-like.

    Returns:
        List of removed keys.
    """
    removed = []

    for key in CLEARABLE_KEYS:
        if key in session_state:
            del session_state[key]
            removed.append(key)

    # Also clear keys matching patterns
    settings_keys = [k for k in list(session_state.keys()) if k.endswith("_settings_effective")]
    for key in settings_keys:
        del session_state[key]
        removed.append(key)

    return removed


def build_zip_bytes(
    artifacts: Dict[str, Any],
    tables: Dict[str, str],
    figures: Optional[Dict[str, bytes]] = None,
    session_info: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Build ZIP archive in memory.

    Args:
        artifacts: Dict of artifact_name -> dict (will be JSON serialized).
        tables: Dict of table_name -> CSV string.
        figures: Optional dict of figure_name -> bytes (PNG/HTML).
        session_info: Optional session metadata.

    Returns:
        ZIP file as bytes.
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Artifacts (JSON)
        for name, data in artifacts.items():
            if data is not None:
                json_str = json.dumps(data, indent=2, default=str)
                zf.writestr(f"artifacts/{name}.json", json_str)

        # Tables (CSV)
        for name, csv_str in tables.items():
            if csv_str:
                zf.writestr(f"tables/{name}.csv", csv_str)

        # Figures
        if figures:
            for name, fig_bytes in figures.items():
                if fig_bytes:
                    zf.writestr(f"figures/{name}", fig_bytes)

        # Session info
        if session_info:
            info = {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "privacy_notice": "All temporary files were deleted after analysis.",
                **session_info,
            }
            zf.writestr("meta/session_info.json", json.dumps(info, indent=2))

    return buffer.getvalue()


def get_schema_summary(schema_obj: Dict[str, Any]) -> str:
    """Get compact schema summary string.

    Args:
        schema_obj: Validated schema dict.

    Returns:
        Summary string like "12 variables: g=5, c=4, p=3"
    """
    if not schema_obj or "variables" not in schema_obj:
        return "Schema not ready"

    variables = schema_obj["variables"]
    n_total = len(variables)

    counts = {"g": 0, "c": 0, "p": 0}
    for var in variables:
        mgm_type = var.get("mgm_type", "c")
        if mgm_type in counts:
            counts[mgm_type] += 1

    return f"{n_total} variables: g={counts['g']}, c={counts['c']}, p={counts['p']}"
