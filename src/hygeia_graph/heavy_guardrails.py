"""Heavy module guardrails for Bootnet, NCT, and LASSO.

Provides safe defaults and clamping for resource-intensive analysis modules.
"""

from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# THRESHOLD CONSTANTS
# ============================================================================

# Bootnet thresholds
BOOTNET_SAFE_MAX_BOOTS = 500
BOOTNET_HARD_MAX_BOOTS = 2000
BOOTNET_SAFE_MAX_CORES = 1
BOOTNET_HARD_MAX_CORES = 2
BOOTNET_DEFAULT_BOOTS = 200

# NCT thresholds
NCT_SAFE_MAX_PERMS = 500
NCT_HARD_MAX_PERMS = 5000
NCT_SAFE_MAX_CORES = 1
NCT_HARD_MAX_CORES = 2
NCT_DEFAULT_PERMS = 200
NCT_EDGE_TESTS_MAX_PERMS = 200  # Edge tests expensive above this

# LASSO thresholds
LASSO_SAFE_MAX_NFOLDS = 10
LASSO_HARD_MAX_NFOLDS = 20
LASSO_SAFE_MAX_FEATURES = 100
LASSO_HARD_MAX_FEATURES = 300
LASSO_DEFAULT_NFOLDS = 5
LASSO_DEFAULT_MAX_FEATURES = 30


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def clamp_int(x: int, lo: int, hi: int) -> int:
    """Clamp integer to range [lo, hi]."""
    return max(lo, min(hi, x))


def clamp_float(x: float, lo: float, hi: float) -> float:
    """Clamp float to range [lo, hi]."""
    return max(lo, min(hi, x))


def _make_message(
    level: str, code: str, message: str, details: Optional[Dict] = None
) -> Dict[str, Any]:
    """Create a guardrail message."""
    msg = {"level": level, "code": code, "message": message}
    if details:
        msg["details"] = details
    return msg


# ============================================================================
# BOOTNET NORMALIZATION
# ============================================================================


def normalize_bootnet_settings(
    settings: Dict[str, Any],
    *,
    advanced_unlocked: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Normalize bootnet settings with guardrails.

    Args:
        settings: Raw bootnet settings dict.
        advanced_unlocked: Whether advanced mode is enabled.

    Returns:
        Tuple of (normalized_settings, messages).
    """
    messages = []
    norm = settings.copy()

    # Extract values
    n_boots_np = settings.get("n_boots_np", BOOTNET_DEFAULT_BOOTS)
    n_boots_case = settings.get("n_boots_case", BOOTNET_DEFAULT_BOOTS)
    n_cores = settings.get("n_cores", 1)

    # Always apply hard max
    orig_np = n_boots_np
    orig_case = n_boots_case
    orig_cores = n_cores

    n_boots_np = clamp_int(n_boots_np, 1, BOOTNET_HARD_MAX_BOOTS)
    n_boots_case = clamp_int(n_boots_case, 1, BOOTNET_HARD_MAX_BOOTS)
    n_cores = clamp_int(n_cores, 1, BOOTNET_HARD_MAX_CORES)

    if n_boots_np < orig_np or n_boots_case < orig_case or n_cores < orig_cores:
        messages.append(
            _make_message(
                "warning",
                "BOOTNET_HARD_CLAMPED",
                    f"Values clamped to hard limits (boots≤{BOOTNET_HARD_MAX_BOOTS}, "
                    f"cores≤{BOOTNET_HARD_MAX_CORES}).",
            )
        )

    # Apply safe max if not advanced
    if not advanced_unlocked:
        safe_np = n_boots_np
        safe_case = n_boots_case
        safe_cores = n_cores

        n_boots_np = clamp_int(n_boots_np, 1, BOOTNET_SAFE_MAX_BOOTS)
        n_boots_case = clamp_int(n_boots_case, 1, BOOTNET_SAFE_MAX_BOOTS)
        n_cores = clamp_int(n_cores, 1, BOOTNET_SAFE_MAX_CORES)

        if n_boots_np < safe_np or n_boots_case < safe_case or n_cores < safe_cores:
            messages.append(
                _make_message(
                    "warning",
                    "BOOTNET_CLAMPED",
                    f"Clamped to safe limits (boots≤{BOOTNET_SAFE_MAX_BOOTS}, "
                    f"cores≤{BOOTNET_SAFE_MAX_CORES}). "
                    "Enable Advanced unlock for larger runs.",
                    {
                        "original_np": orig_np,
                        "original_case": orig_case,
                        "original_cores": orig_cores,
                    },
                )
            )

    # Validate caseMin/caseMax
    case_min = settings.get("caseMin", 0.25)
    case_max = settings.get("caseMax", 0.75)

    case_min = clamp_float(case_min, 0.0, 1.0)
    case_max = clamp_float(case_max, 0.0, 1.0)

    if case_min >= case_max:
        case_min = 0.25
        case_max = 0.75
        messages.append(
            _make_message(
                "warning",
                "BOOTNET_CASE_RANGE_FIXED",
                "caseMin must be < caseMax. Reset to defaults (0.25, 0.75).",
            )
        )

    norm["n_boots_np"] = n_boots_np
    norm["n_boots_case"] = n_boots_case
    norm["n_cores"] = n_cores
    norm["caseMin"] = case_min
    norm["caseMax"] = case_max

    return norm, messages


# ============================================================================
# NCT NORMALIZATION
# ============================================================================


def normalize_nct_settings(
    settings: Dict[str, Any],
    *,
    advanced_unlocked: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Normalize NCT settings with guardrails.

    Args:
        settings: Raw NCT settings dict.
        advanced_unlocked: Whether advanced mode is enabled.

    Returns:
        Tuple of (normalized_settings, messages).
    """
    messages = []
    norm = settings.copy()

    permutations = settings.get("permutations", NCT_DEFAULT_PERMS)
    edge_tests = settings.get("edge_tests", False)
    n_cores = settings.get("n_cores", 1)
    mode = settings.get("mode", "auto")

    orig_perms = permutations
    orig_cores = n_cores

    # Hard max
    permutations = clamp_int(permutations, 1, NCT_HARD_MAX_PERMS)
    n_cores = clamp_int(n_cores, 1, NCT_HARD_MAX_CORES)

    if permutations < orig_perms or n_cores < orig_cores:
        messages.append(
            _make_message(
                "warning",
                "NCT_HARD_CLAMPED",
                f"Values clamped to hard limits (perms≤{NCT_HARD_MAX_PERMS}, "
                f"cores≤{NCT_HARD_MAX_CORES}).",
            )
        )

    # Safe max if not advanced
    if not advanced_unlocked:
        safe_perms = permutations
        safe_cores = n_cores

        permutations = clamp_int(permutations, 1, NCT_SAFE_MAX_PERMS)
        n_cores = clamp_int(n_cores, 1, NCT_SAFE_MAX_CORES)

        if permutations < safe_perms or n_cores < safe_cores:
            messages.append(
                _make_message(
                    "warning",
                    "NCT_CLAMPED",
                    f"Clamped to safe limits (perms≤{NCT_SAFE_MAX_PERMS}). "
                    "Enable Advanced unlock for larger runs.",
                )
            )

    # Edge tests guard
    if edge_tests and permutations > NCT_EDGE_TESTS_MAX_PERMS:
        if not advanced_unlocked or permutations > NCT_SAFE_MAX_PERMS:
            edge_tests = False
            messages.append(
                _make_message(
                    "warning",
                    "NCT_EDGE_TESTS_DISABLED",
                    f"Edge tests disabled (permutations>{NCT_EDGE_TESTS_MAX_PERMS} "
                    "is too expensive).",
                )
            )
        else:
            messages.append(
                _make_message(
                    "info",
                    "NCT_EDGE_TESTS_WARNING",
                    "Edge tests enabled with Advanced unlock. This may be slow.",
                )
            )

    # Validate mode
    valid_modes = {"auto", "perm_mgm", "nct_pkg"}
    if mode not in valid_modes:
        mode = "auto"
        messages.append(
            _make_message(
                "warning",
                "NCT_MODE_INVALID",
                "Invalid mode. Reset to 'auto'.",
            )
        )

    norm["permutations"] = permutations
    norm["edge_tests"] = edge_tests
    norm["n_cores"] = n_cores
    norm["mode"] = mode

    return norm, messages


# ============================================================================
# LASSO NORMALIZATION
# ============================================================================


def normalize_lasso_settings(
    settings: Dict[str, Any],
    *,
    advanced_unlocked: bool = False,
    n_rows: Optional[int] = None,
    n_cols: Optional[int] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Normalize LASSO settings with guardrails.

    Args:
        settings: Raw LASSO settings dict.
        advanced_unlocked: Whether advanced mode is enabled.
        n_rows: Number of rows in dataset (for p>>n warning).
        n_cols: Number of columns in dataset.

    Returns:
        Tuple of (normalized_settings, messages).
    """
    messages = []
    norm = settings.copy()

    nfolds = settings.get("nfolds", LASSO_DEFAULT_NFOLDS)
    max_features = settings.get("max_features", LASSO_DEFAULT_MAX_FEATURES)
    alpha = settings.get("alpha", 1.0)

    orig_nfolds = nfolds
    orig_max_features = max_features

    # Hard max
    nfolds = clamp_int(nfolds, 2, LASSO_HARD_MAX_NFOLDS)
    max_features = clamp_int(max_features, 1, LASSO_HARD_MAX_FEATURES)

    if nfolds < orig_nfolds or max_features < orig_max_features:
        messages.append(
            _make_message(
                "warning",
                "LASSO_HARD_CLAMPED",
                f"Values clamped to hard limits (nfolds≤{LASSO_HARD_MAX_NFOLDS}, "
                f"max_features≤{LASSO_HARD_MAX_FEATURES}).",
            )
        )

    # Safe max if not advanced
    if not advanced_unlocked:
        safe_nfolds = nfolds
        safe_max_features = max_features

        nfolds = clamp_int(nfolds, 2, LASSO_SAFE_MAX_NFOLDS)
        max_features = clamp_int(max_features, 1, LASSO_SAFE_MAX_FEATURES)

        if nfolds < safe_nfolds or max_features < safe_max_features:
            messages.append(
                _make_message(
                    "warning",
                    "LASSO_CLAMPED",
                    f"Clamped to safe limits (nfolds≤{LASSO_SAFE_MAX_NFOLDS}, "
                    f"max_features≤{LASSO_SAFE_MAX_FEATURES}). "
                    "Enable Advanced unlock for larger runs.",
                )
            )

    # Validate alpha
    alpha = clamp_float(alpha, 0.0, 1.0)
    norm["alpha"] = alpha

    # High dimension warning (p >> n)
    if n_rows and n_cols:
        p = n_cols - 1  # Exclude target
        if p > 500 and n_rows < 200:
            messages.append(
                _make_message(
                    "warning",
                    "LASSO_HIGH_DIMENSION",
                    f"High dimensionality detected (p={p}, n={n_rows}). Results may be unstable.",
                )
            )

    norm["nfolds"] = nfolds
    norm["max_features"] = max_features

    return norm, messages


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def should_require_advanced_unlock(module: str, settings: Dict[str, Any]) -> bool:
    """Check if settings require advanced unlock.

    Args:
        module: One of "bootnet", "nct", "lasso".
        settings: Settings dictionary.

    Returns:
        True if advanced unlock is needed.
    """
    if module == "bootnet":
        return (
            settings.get("n_boots_np", 0) > BOOTNET_SAFE_MAX_BOOTS
            or settings.get("n_boots_case", 0) > BOOTNET_SAFE_MAX_BOOTS
            or settings.get("n_cores", 1) > BOOTNET_SAFE_MAX_CORES
        )
    elif module == "nct":
        return (
            settings.get("permutations", 0) > NCT_SAFE_MAX_PERMS
            or settings.get("n_cores", 1) > NCT_SAFE_MAX_CORES
            or (
                settings.get("edge_tests", False)
                and settings.get("permutations", 0) > NCT_EDGE_TESTS_MAX_PERMS
            )
        )
    elif module == "lasso":
        return (
            settings.get("nfolds", 0) > LASSO_SAFE_MAX_NFOLDS
            or settings.get("max_features", 0) > LASSO_SAFE_MAX_FEATURES
        )
    return False


def render_messages_to_markdown(messages: List[Dict[str, Any]]) -> str:
    """Render guardrail messages to markdown for UI display.

    Args:
        messages: List of message dicts.

    Returns:
        Markdown string.
    """
    if not messages:
        return ""

    lines = []
    for msg in messages:
        icon = "⚠️" if msg["level"] == "warning" else "ℹ️"
        lines.append(f"- {icon} **{msg['code']}**: {msg['message']}")

    return "\n".join(lines)
