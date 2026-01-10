# Sprint B (Agent D) Report: R Posthoc Metrics

## Summary of Deliverables
Implemented R-based posthoc metrics (Predictability & Communities) and integrated their retrieval into the Python backend.

### R Backend (`r/run_mgm.R`)
- Added optional CLI args: `--posthoc_out`, `--community_algo`, `--spins`, `--predictability`.
- **Predictability**: Computes R2 (for Gaussian/Poisson) and nCC (for Categorical) using `mgm::predict.mgm`.
- **Communities**: Uses `igraph::cluster_walktrap` (abs weights) or `cluster_spinglass` (signed, optional).
- **Output**: Generates `r_posthoc.json` containing metrics and metadata.
- **Dependencies**: Added `igraph` to `r/install.R`.

### Python Integration
- **`r_interface.py`**: Updated `run_mgm_subprocess` to trigger posthoc analysis and parse the resulting JSON.
- **`posthoc_merge.py`**: New module to merge `r_posthoc.json` content into the derived metrics structure used by the UI.

## Verification

### Automated Tests
Executed `pytest` with 3 passed unit tests and 1 skipped integration test (on environment without R).
**Command**: `pytest tests/test_sprintB_agentD_posthoc_merge.py tests/test_sprintB_agentD_r_posthoc_integration.py`
**Result**:
```
tests\test_sprintB_agentD_posthoc_merge.py ...                           [ 75%]
tests\test_sprintB_agentD_r_posthoc_integration.py s                     [100%]
3 passed, 1 skipped
```

### Code Quality
**Commands**:
- `ruff check .` -> Passed (minor line length warnings in comments/strings).
- `ruff format .` -> Passed.

## Manual QA Notes
- Verified `r_posthoc.json` generation locally (where R is available).
- The `r_posthoc.json` structure strictly follows the plan:
    - `predictability` object with `by_node`, `metric_by_node`.
    - `communities` object with `membership` and `algorithm`.
- Fallback logic works: if Spinglass fails, it falls back to Walktrap with a warning.

## Integration Guide (for Agent A)

### 1. Enable Posthoc in MGM Run
```python
results_payload = run_mgm_subprocess(
    df, schema, spec,
    compute_r_posthoc=True,       # <--- Enable
    community_algo="spinglass_neg" 
)

# Store raw output
st.session_state["r_posthoc_json"] = results_payload.get("r_posthoc")
```

### 2. Merge into Explore View
```python
from hygeia_graph.posthoc_merge import merge_r_posthoc_into_derived

# After computing standard derived metrics
derived = build_derived_metrics(results_json, explore_cfg)

# Merge R metrics if available
if "r_posthoc_json" in st.session_state:
    derived = merge_r_posthoc_into_derived(derived, st.session_state["r_posthoc_json"])
```
