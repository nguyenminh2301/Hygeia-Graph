import pytest

from hygeia_graph.ui_state import (
    clear_analysis_cache,
    explore_config_hash,
    get_analysis_id_from_state,
    get_cached_outputs,
    get_default_explore_config,
    normalize_explore_config,
    set_cached_outputs,
)


def test_default_config_is_stable():
    config = get_default_explore_config()
    expected = {
        "threshold": 0.0,
        "use_absolute_weights": True,
        "top_edges": 500,
        "show_labels": True,
        "physics": True,
    }
    assert config == expected


def test_config_hash_is_deterministic():
    cfg1 = {"threshold": 0.5, "top_edges": 200}
    cfg2 = {"top_edges": 200, "threshold": 0.5}  # Different order

    hash1 = explore_config_hash(cfg1, "analysis_123")
    hash2 = explore_config_hash(cfg2, "analysis_123")

    assert hash1 == hash2
    assert isinstance(hash1, str)
    assert len(hash1) > 0  # Should be a hash string


def test_normalize_clamps_threshold():
    # Test valid case
    cfg = {"threshold": 0.1}
    results = {"edges": [{"weight": 0.5}, {"weight": -0.8}]}
    # Max abs is 0.8

    norm = normalize_explore_config(cfg, results)
    assert norm["threshold"] == 0.1

    # Test clamping
    cfg_high = {"threshold": 1.5}
    norm_clamped = normalize_explore_config(cfg_high, results)
    assert norm_clamped["threshold"] == 0.8

    # Test negative
    with pytest.raises(ValueError):
        normalize_explore_config({"threshold": -0.1}, results)

    # Test top_edges validation
    with pytest.raises(ValueError):
        normalize_explore_config({"top_edges": 999}, results)


def test_cache_set_get_clear():
    # Mock session state
    state = {}
    analysis_id = "test_run_1"
    config_hash = "abc123hash"
    outputs = {"df": "some_dataframe", "html": "<div></div>"}

    # Test Set/Get
    set_cached_outputs(state, analysis_id, config_hash, outputs)

    cached = get_cached_outputs(state, analysis_id, config_hash)
    assert cached == outputs

    # Test missing key
    assert get_cached_outputs(state, analysis_id, "wrong_hash") is None
    assert get_cached_outputs(state, "wrong_id", config_hash) is None

    # Test Clear
    clear_analysis_cache(state, analysis_id)
    assert get_cached_outputs(state, analysis_id, config_hash) is None
    assert "derived_cache" in state
    assert analysis_id not in state["derived_cache"]


def test_get_analysis_id_priority():
    schema = {"analysis_id": "schema_id"}
    spec = {"analysis_id": "spec_id"}
    res = {"analysis_id": "res_id"}

    # Result priority
    assert get_analysis_id_from_state(schema, spec, res) == "res_id"
    # Then spec
    assert get_analysis_id_from_state(schema, spec, None) == "spec_id"
    # Then schema
    assert get_analysis_id_from_state(schema, None, None) == "schema_id"
    # None
    assert get_analysis_id_from_state(None, None, None) is None
