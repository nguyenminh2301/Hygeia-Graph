"""Utilities for Intervention Simulation (Hashing)."""

import hashlib
import json
from typing import Any, Dict


def simulation_settings_hash(settings: Dict[str, Any], analysis_id: str) -> str:
    """Deterministic hash for simulation execution."""
    # subset relevant keys? Or assume caller passed clean settings
    # Key factors: intervene_node, delta, steps, damping, normalize, threshold, top_edges

    dump = json.dumps({"analysis_id": str(analysis_id), "settings": settings}, sort_keys=True)

    return hashlib.sha256(dump.encode("utf-8")).hexdigest()
