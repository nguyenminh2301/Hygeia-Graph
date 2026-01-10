"""Utilities for Insights Report module."""

import hashlib
import json
from typing import Any, Dict


def report_settings_hash(settings: Dict[str, Any], analysis_id: str) -> str:
    """Generate deterministic hash for report settings + analysis ID.

    Args:
        settings: Dictionary of report settings (style, inclusions, etc.)
        analysis_id: Unique analysis ID

    Returns:
        SHA256 hash string
    """
    # Sort keys to ensure determinism
    dump = json.dumps({"analysis_id": str(analysis_id), "settings": settings}, sort_keys=True)

    return hashlib.sha256(dump.encode("utf-8")).hexdigest()
