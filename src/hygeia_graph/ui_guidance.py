"""UI Guidance content and navigation helpers.

Provides consistent UX copy and workflow navigation for Hygeia-Graph.
"""

from typing import Any, Dict, List, Optional

# ============================================================================
# DATA FORMAT GUIDANCE
# ============================================================================

DATA_FORMAT_SHORT = """
**📋 Data Requirements:**
- **Format:** CSV only (UTF-8 recommended)
- **Structure:** First row = headers, each column = variable (node), each row = observation
- **Variable types:**
  - Continuous (Gaussian): numeric (BMI, lab values)
  - Categorical: strings or small integers with few unique values
  - Count (Poisson): non-negative integers with many unique values
- **⚠️ Missing values are NOT imputed** — preprocess your data first (e.g., MICE, complete cases)
- **⚠️ Constant columns** (zero variance) will be dropped
- **Recommended:** n≥100, p≤30 for demos; n≥200, p≤60 for better stability
"""

DATA_FORMAT_DETAILS = """
### Detailed Data Formatting Guidelines

**Supported Variable Types (mapped to MGM types):**
| Type | MGM Code | Description | Example |
|------|----------|-------------|---------|
| Gaussian | `g` | Continuous numeric | BMI, blood pressure, lab values |
| Categorical | `c` | Nominal/ordinal with few levels | Sex, diagnosis category, severity level |
| Poisson | `p` | Count data (non-negative integers) | Hospital days, symptom count |

**Common Pitfalls:**
1. **Missing values:** MGM uses `warn_and_abort` policy — no imputation. Use listwise deletion or impute beforehand.
2. **Rare categories:** Categories with <8 samples can cause unstable estimates or glmnet warnings.
3. **High dimensionality (p >> n):** Consider using LASSO feature selection first via Preprocessing page.
4. **Non-UTF8 encoding:** May cause parsing errors — convert to UTF-8.

**Dataset Size Recommendations:**
- Demo/testing: n≥100, p≤30
- Publication-quality: n≥200, p≤60
- Large p (100+): Use LASSO funnel preprocessing

**Longitudinal Data (V2):**
If your dataset has paired columns (e.g., `Symptom_T1`, `Symptom_T2`), you can use the
V2 Longitudinal Flow module to visualize transitions.
"""

# ============================================================================
# BRANCHING HINTS (DEFAULT RECOMMENDATIONS)
# ============================================================================

MODEL_SETTINGS_HINTS = {
    "ebic_gamma": "Recommended: 0.5 (balanced sparsity). Higher = sparser network.",
    "alpha": "Recommended: 0.5 (elastic-net). 1.0 = pure LASSO, 0 = ridge.",
    "rule_reg": "Recommended: AND (stricter edges). OR allows more edges.",
    "scale_gaussian": "Usually True. Set False if already standardized.",
}

EXPLORE_HINTS = {
    "threshold": "Start at 0, increase to reduce hairball. Common: 0.05–0.1.",
    "top_edges": "Recommended: 500 for HF. Increase for full network.",
    "layout": "spring = force-directed (default), circle = radial layout.",
}

HEAVY_MODULE_HINTS = {
    "bootnet_boots": "Demo: 200. Publication: 1000+ (use Advanced unlock).",
    "nct_perms": "Demo: 200. Publication: 1000+ (use Advanced unlock).",
    "lasso_nfolds": "Demo: 5. Publication: 10 (use Advanced unlock for more).",
}


# ============================================================================
# NAVIGATION HELPERS
# ============================================================================

# Standard page order
PAGE_ORDER = [
    "Data & Schema",
    "Model Settings",
    "Run MGM",
    "Explore",
    "Report & Export",
]


def get_next_page(current_page: str) -> Optional[str]:
    """Get the next page in the workflow.

    Args:
        current_page: Current page name.

    Returns:
        Next page name or None if at end.
    """
    try:
        idx = PAGE_ORDER.index(current_page)
        if idx < len(PAGE_ORDER) - 1:
            return PAGE_ORDER[idx + 1]
    except ValueError:
        pass
    return None


def get_prev_page(current_page: str) -> Optional[str]:
    """Get the previous page in the workflow.

    Args:
        current_page: Current page name.

    Returns:
        Previous page name or None if at start.
    """
    try:
        idx = PAGE_ORDER.index(current_page)
        if idx > 0:
            return PAGE_ORDER[idx - 1]
    except ValueError:
        pass
    return None


def can_proceed_to_next(current_page: str, session_state: Dict[str, Any]) -> bool:
    """Check if user can proceed to the next step.

    Args:
        current_page: Current page name.
        session_state: Streamlit session state dict.

    Returns:
        True if prerequisites are met.
    """
    if current_page == "Data & Schema":
        # Need valid schema
        return session_state.get("schema_obj") is not None

    elif current_page == "Model Settings":
        # Need valid model spec
        return session_state.get("model_spec_obj") is not None

    elif current_page == "Run MGM":
        # Need successful results
        results = session_state.get("results_json")
        return results is not None and results.get("status") == "success"

    elif current_page == "Explore":
        # Need either derived metrics or results
        return (
            session_state.get("derived_metrics_json") is not None
            or session_state.get("results_json") is not None
        )

    return False


def get_workflow_status(session_state: Dict[str, Any]) -> Dict[str, bool]:
    """Get completion status for all workflow steps.

    Args:
        session_state: Streamlit session state dict.

    Returns:
        Dict mapping page names to completion status.
    """
    return {
        "Data & Schema": session_state.get("schema_obj") is not None,
        "Model Settings": session_state.get("model_spec_obj") is not None,
        "Run MGM": (
            session_state.get("results_json") is not None
            and session_state.get("results_json", {}).get("status") == "success"
        ),
        "Explore": session_state.get("derived_metrics_json") is not None,
        "Report & Export": True,  # Always accessible if anything exists
    }


def get_hint(category: str, key: str) -> str:
    """Get a branching hint for a setting.

    Args:
        category: One of "model", "explore", "heavy".
        key: The specific setting key.

    Returns:
        Hint text or empty string.
    """
    hints = {
        "model": MODEL_SETTINGS_HINTS,
        "explore": EXPLORE_HINTS,
        "heavy": HEAVY_MODULE_HINTS,
    }
    return hints.get(category, {}).get(key, "")
