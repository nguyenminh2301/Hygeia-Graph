# Hygeia-Graph Enhancement Plan
# Date: 2026-01-14

## Task [1]: Hide pages completely from sidebar (keep functions) ✅ COMPLETED
### Changes to app.py:
1. Update `nav_order` list (lines 176-184) - removed Preprocessing, Robustness, Simulation, Comparison
2. Update router section (lines 311-369) - added comments and kept hidden page handling
3. Page functions in ui_pages.py remain intact for future re-enablement

### Sidebar Navigation after changes:
- Introduction
- Data & Schema
- Model Settings
- Run MGM
- Explore
- Temporal Networks (VAR)
- Report & Export

Hidden pages (not shown in sidebar but code remains):
- Preprocessing
- Robustness
- Simulation
- Comparison (coming soon)

## Task [2]: Regenerate example CSV files with new seeds ✅ COMPLETED
### Changes to example_datasets.py:
1. `generate_easy_dataset` seed: 42 → 2024
2. `generate_medium_dataset` seed: 42 → 2025
3. `generate_hard_dataset` seed: 42 → 2028 (fixed due to missing value issue)
4. Improved Ethnicity distribution: [0.4, 0.2, 0.15, 0.15, 0.1]
5. Fixed AlcoholUse: "None" → "Non-drinker" (to avoid pandas NaN interpretation)
6. Added `validate_generated_data()` function to ensure no zero-variance variables

### Regenerated files:
| File | Seed | Rows | Columns | Missing | Status |
|------|------|------|---------|---------|--------|
| example_easy.csv | 2024 | 140 | 6 | 0 | ✅ All cols >=2 values |
| example_medium.csv | 2025 | 280 | 12 | 0 | ✅ All cols >=2 values |
| example_hard.csv | 2028 | 600 | 32 | 0 | ✅ All cols >=2 values |

## Task [3]: Test the regenerated files ✅ COMPLETED
### Test results:
1. **Imports**: All modules imported successfully
2. **Datasets**: All 3 datasets loaded correctly with no zero-variance columns
3. **Schema validation**: All 3 datasets pass schema validation
4. **Model Spec validation**: All 3 datasets pass model spec validation
5. **Data profiling**: All datasets profiled correctly
6. **Centrality computation**: Network metrics work correctly
7. **UI page rendering**: Session state initialization works
8. **Visualizer**: HTML generation works (12,141 chars)

### Variable breakdown:
- Easy: 3 Gaussian, 2 Categorical, 1 Poisson
- Medium: 7 Gaussian, 4 Categorical, 1 Poisson
- Hard: 18 Gaussian, 11 Categorical, 3 Poisson

## Summary
All tasks completed successfully!

### To re-enable hidden pages, change `hidden=True` to `hidden=False` in `nav_options_advanced` (app.py lines 161-166):
```python
"Preprocessing": {"label": ..., "hidden": False},   # Bật lại
"Robustness": {"label": ..., "hidden": False},      # Bật lại
"Simulation": {"label": ..., "hidden": False},      # Bật lại
```

### To run the Streamlit app:
```bash
cd "G:\My Drive\Minh-ca nhan\Github\Hygeia-Graph"
streamlit run app.py
```

### To run the test suite:
```bash
python test_app.py
```
