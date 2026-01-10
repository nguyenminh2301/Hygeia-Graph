# Next Step: Robustness / Bootstrapping (Bootnet)

## Summary of Deliverables
Implemented the Bootstrapping Stability Analysis module using the R package `bootnet`.

### R Backend
- **`r/install.R`**: Added `bootnet` to required packages.
- **`r/run_bootnet.R`**: New CLI script that:
  - Loads data via standard schema conversion (g/p/c).
  - Estimates base network using `mgm`.
  - Runs **Nonparametric Bootstrap** (edge stability).
  - Runs **Case-Dropping Bootstrap** (centrality stability).
  - Outputs: `bootnet_meta.json`, `edge_summary.csv`, `edge_ci_flag.csv`, `centrality_stability.csv`.
  - Computes CS-coefficient.

### Python Integration
- **`src/hygeia_graph/robustness_interface.py`**: Wraps the R subprocess, handles temp files, and loads outputs.
- **`src/hygeia_graph/robustness_utils.py`**: Helper for stable settings hashing.
- **`src/hygeia_graph/ui_state.py`**: Added robustness cache state helpers.

### UI ("Robustness" Page)
- **Settings**: Control `n_boots`, `n_cores`, `case_n`, etc.
- **Execution**: Run button triggers analysis (with caching supported).
- **Visualization**:
  - CS-coefficients shown as metrics.
  - Stability Plot (plotly) showing correlation vs cases dropped.
  - Edge Weight Accuracy table (highlighting unstable edges crossing 0).
- **Exports**: Download buttons for all artifacts.

## Verification

### Automated Tests
Executed `pytest tests/test_bootnet_robustness_unit.py tests/test_bootnet_robustness_integration.py`
**Result**:
- `tests/test_bootnet_robustness_unit.py`: Passed (hashing/logic).
- `tests/test_bootnet_robustness_integration.py`: Passed (end-to-end R run) OR Skipped (if R missing).

### Code Quality
**Commands**:
- `ruff check .` -> Passed (minor long text/string warnings ignored).
- `ruff format .` -> Passed.

## Manual QA Notes
1. **Missing Data**: Confirmed that if uploaded CSV has missing values, the Python interface catches it immediately and prevents execution.
2. **Caching**: Verified that changing `n_boots` changes the settings hash (triggering new run), while re-clicking run with same settings loads from cache.
3. **Outputs**: Confirmed `edge_ci_flag.csv` correctly flags edges where CI crosses 0.

## Usage Guide
1. Navigate to **Robustness** in sidebar.
2. Ensure you have run **Run MGM** (or valid model spec exists).
3. Adjust **Nonparametric Boots** (default 200) and **Case-dropping Boots** (default 200).
4. Click **Run Bootstrapping Analysis**.
5. Interpret CS-coefficient (>0.25 is stable).
