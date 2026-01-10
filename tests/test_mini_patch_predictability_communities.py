"""Tests for Mini Patch UI Logic (Predictability & Communities)."""

from hygeia_graph.ui_state import (
    can_enable_communities,
    can_enable_predictability,
    get_community_counts,
    map_community_to_colors,
)


def test_can_enable_predictability_features():
    """Test predictability available check."""
    assert can_enable_predictability(None) is False
    assert can_enable_predictability({}) is False
    assert can_enable_predictability({"predictability": {"enabled": False}}) is False

    valid = {"predictability": {"enabled": True, "by_node": {"A": 0.5}}}
    assert can_enable_predictability(valid) is True


def test_can_enable_community_features():
    """Test community available check."""
    assert can_enable_communities(None) is False
    assert can_enable_communities({}) is False

    # Missing membership
    invalid = {"communities": {"enabled": True}}
    assert can_enable_communities(invalid) is False

    # Empty membership
    invalid2 = {"communities": {"enabled": True, "membership": {}}}
    assert can_enable_communities(invalid2) is False

    valid = {"communities": {"enabled": True, "membership": {"A": "1"}}}
    assert can_enable_communities(valid) is True


def test_community_color_mapping_deterministic():
    """Test community colors are deterministic and cover all groups."""
    mem = {"A": "1", "B": "1", "C": "2"}

    # First run
    map1 = map_community_to_colors(mem)
    assert "1" in map1
    assert "2" in map1
    assert map1["1"] != map1["2"]

    # Second run
    map2 = map_community_to_colors(mem)
    assert map1 == map2


def test_community_counts():
    """Test community member counting."""
    mem = {"A": "1", "B": "1", "C": "2", "D": "2", "E": "2"}
    counts = get_community_counts(mem)
    assert counts["1"] == 2
    assert counts["2"] == 3
