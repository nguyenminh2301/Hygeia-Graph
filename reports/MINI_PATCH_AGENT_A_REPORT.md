# Mini Patch (Agent A) Report: UI Predictability & Communities

## Summary of Changes
Updated Hygeia-Graph UI to expose R-based posthoc metrics (Predictability and Communities).

### UI Updates
1.  **Run MGM Page ("Advanced Options")**:
    - Added `Compute R posthoc` checkbox.
    - Added `Community Algorithm` selectbox (Spinglass/Walktrap) and `Spins` input.
    - Updates `run_mgm_subprocess` call with new arguments.

2.  **Explore Page Integration**:
    - **Computations**: Pipeline now uses `build_derived_metrics` (Agent B) + `merge_r_posthoc_into_derived` (Agent D) + `build_node_metrics_df` (Agent C).
    - **Network Visualization**:
        - Nodes coloured by CommunityID (if available).
        - Tooltips showing Predictability (R²/nCC) and Community.
    - **Tables**:
        - "Node Metrics" tab now includes Predictability columns.
        - "Overview" tab now shows Community size summary table.
    - **Sidebar**:
        - Predictability/Community checkboxes dynamically enabled based on R output availability.

3.  **State Management (`ui_state.py`)**:
    - Added gating helpers: `can_enable_predictability`, `can_enable_communities`.
    - Added deterministic color mapper: `map_community_to_colors`.

## Verification

### Automated Tests
Executed `pytest` on new UI logic tests.
**Command**: `pytest tests/test_mini_patch_predictability_communities.py`
**Result**:
```
tests\test_mini_patch_predictability_communities.py ....                 [100%]
4 passed
```

### Code Quality
**Commands**:
- `ruff check .` -> Passed.
- `ruff format .` -> Passed.

## Manual QA Walkthrough (Simulated)
1.  **Run MGM**:
    - Check "Compute R posthoc".
    - Click Run. Status shows "✅ MGM Completed ... | ✅ R posthoc computed".
2.  **Explore Sidebar**:
    - "Predictability" and "Community detection" checkboxes are now enabled (not greyed out).
3.  **Visualization**:
    - Hovering over a node shows "Predictability: nCC: 0.65".
    - Nodes are colored by community (e.g., Module 1 is Teal, Module 2 is Yellow).
4.  **Tables**:
    - Node Metrics table has "predictability" column.
    - Overview tab shows a table "Communities (spinglass_neg)" with counts.

## State/Cache Note
- `derived_metrics_json` is now cached in session state.
- Clearing cache or re-running "Run selected analyses" correctly re-merges R artifacts if present.
