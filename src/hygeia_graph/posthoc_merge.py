"""Merge R-computed posthoc metrics into derived metrics.

Integrates r_posthoc.json validation results (Predictability, Communities)
into the derived_metrics structure used by the UI.
"""

import copy
from typing import Any


def merge_r_posthoc_into_derived(
    derived_metrics_json: dict[str, Any],
    r_posthoc_json: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge R posthoc outputs into the derived metrics object.

    Args:
        derived_metrics_json: The existing derived metrics (from Agent B).
        r_posthoc_json: The output from R posthoc analysis (or None).

    Returns:
        New dict with merged fields (deep copy safe).
    """
    # Defensive copy to avoid mutating input
    derived = copy.deepcopy(derived_metrics_json)

    if not r_posthoc_json:
        return derived

    # 1. Predictability
    pred = r_posthoc_json.get("predictability", {})
    if pred.get("enabled"):
        # Add to node_metrics
        nm = derived.setdefault("node_metrics", {})
        nm["predictability"] = pred.get("by_node", {})
        nm["predictability_metric"] = pred.get("metric_by_node", {})

        # Add details if useful for debugging or advanced view?
        # Requirement: "Add node_metrics.predictability" & "predictability_metric_by_node"
        # We can store full predictability object under 'r_predictability' for completeness,
        # but let's stick to the strict requirement first to keep schema clean.

    # 2. Communities
    comm = r_posthoc_json.get("communities", {})
    if comm.get("enabled"):
        # Store top-level under "communities"
        # We can just copy the whole structure
        derived["communities"] = comm

    # 3. Messages
    r_msgs = r_posthoc_json.get("messages", [])
    if r_msgs:
        d_msgs = derived.setdefault("messages", [])
        # Append all R messages, tagging source if needed?
        # Contract says "messages" is list of {level, code, message, details}
        # R messages match this structure.
        d_msgs.extend(r_msgs)

    return derived
