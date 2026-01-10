# Sprint A (Agent B) Report: Posthoc Metrics

## Summary of Deliverables
Implemented fast posthoc network metrics in `src/hygeia_graph/posthoc_metrics.py` without heavy dependencies or R changes.

### Key Features
1.  **Expected Influence (Signed)**: Computed as sum of signed weights (even if display uses absolute weights).
2.  **Bridge Metrics**:
    - **Bridge Strength (Abs)**: Sum of absolute weights for cross-group edges.
    - **Bridge Expected Influence**: Sum of signed weights for cross-group edges.
    - **Safety**: Automatically disabled if <2 groups or <80% node coverage, returning a warning.
3.  **MST Backbone**:
    - Min Spanning Tree (or Forest) computed on `distance = 1/(abs(weight) + eps)`.
    - Returns edges sorted by importance (weight).
4.  **Derived Artifact**: `build_derived_metrics` generates the required `derived_metrics.json` structure, ready for Agent A to wire up.

### Files Created
- `src/hygeia_graph/posthoc_metrics.py`
- `tests/test_sprintA_agentB_posthoc_metrics.py`

## Verification

### Automated Tests
Executed `pytest` with deterministic toy data.
**Command**: `pytest tests/test_sprintA_agentB_posthoc_metrics.py`
**Result**:
```
tests\test_sprintA_agentB_posthoc_metrics.py .......                     [100%]
7 passed
```

### Code Quality
**Commands**:
- `ruff check .` -> Passed (after fixing unused imports)
- `ruff format .` -> Passed (reformatted new files)

### Manual Verification Note
These functions are pure compute and strictly follow the schema requirements.
- **Edge Filtering**: Respects `threshold`, `use_absolute_weights`, and `top_edges`.
- **Structure**: `derived_metrics.json` structure verified by test `test_build_derived_metrics_structure`.
- **Integration**: Functions are exposed and ready for import by Agent A. No UI changes were made.

## Next Steps (Agent A)
- Import `build_derived_metrics` from `hygeia_graph.posthoc_metrics`.
- Call this function in the module-run orchestration layer.
- Cache the result keyed by `(analysis_id, config_hash)`.
- Provide download button for the generated JSON.
