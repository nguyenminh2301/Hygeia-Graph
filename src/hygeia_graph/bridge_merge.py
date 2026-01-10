"""Merge bridge metrics into derived_metrics."""

from typing import Any, Dict


def merge_bridge_into_derived(
    derived: Dict[str, Any],
    bridge_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge networktools bridge metrics into derived_metrics.

    Args:
        derived: The existing derived_metrics dictionary.
        bridge_result: The output from run_bridge_subprocess.

    Returns:
        Updated derived_metrics with bridge canonical metrics.
    """
    if not derived:
        derived = {}

    if not bridge_result or bridge_result.get("status") != "success":
        return derived

    metrics = bridge_result.get("metrics", {})

    # Ensure node_metrics exists
    if "node_metrics" not in derived:
        derived["node_metrics"] = {}

    # Add bridge metrics with canonical suffix
    if metrics.get("bridge_strength"):
        derived["node_metrics"]["bridge_strength_networktools"] = metrics["bridge_strength"]

    if metrics.get("bridge_expected_influence"):
        derived["node_metrics"]["bridge_expected_influence_networktools"] = metrics[
            "bridge_expected_influence"
        ]

    if metrics.get("bridge_betweenness"):
        derived["node_metrics"]["bridge_betweenness_networktools"] = metrics["bridge_betweenness"]

    if metrics.get("bridge_closeness"):
        derived["node_metrics"]["bridge_closeness_networktools"] = metrics["bridge_closeness"]

    # Add bridge metadata
    if "bridge" not in derived:
        derived["bridge"] = {}

    derived["bridge"]["canonical_enabled"] = True
    derived["bridge"]["method"] = bridge_result.get("method", "networktools::bridge")
    derived["bridge"]["n_communities"] = bridge_result.get("n_communities")
    derived["bridge"]["community_source"] = bridge_result.get("community_source")
    derived["bridge"]["computed_at"] = bridge_result.get("computed_at")

    return derived
