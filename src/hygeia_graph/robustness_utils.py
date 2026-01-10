"""Utilities for Robustness module (hashing, caching)."""

import hashlib
import json
from typing import Any, Dict


def robustness_settings_hash(settings: Dict[str, Any], analysis_id: str) -> str:
    """Generate deterministic hash for robustness settings + analysis ID."""
    # Filter only relevant keys
    keys = ["n_boots_np", "n_boots_case", "n_cores", "case_min", "case_max", "case_n", "cor_level"]
    subset = {k: settings.get(k) for k in keys if k in settings}

    data = {"analysis_id": str(analysis_id), "settings": subset}
    dump = json.dumps(data, sort_keys=True)
    return hashlib.sha256(dump.encode("utf-8")).hexdigest()
