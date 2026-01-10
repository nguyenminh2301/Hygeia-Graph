# Next Step: LASSO Feature Selection Module

## Summary of Deliverables
Implemented a supervised feature selection module using **LASSO (glmnet)** to filter predictors before network analysis.

### R Backend
- **`r/install.R`**: Added `glmnet`.
- **`r/run_lasso_select.R`**:
  - Automatically detects family (gaussian, binomial, multinomial).
  - Handles one-hot encoding of categorical variables.
  - Runs cross-validated LASSO (`cv.glmnet`) to select lambda (1se or min).
  - Extracts and aggregates coefficients.
  - Exports `lasso_meta.json`, `lasso_coefficients.csv`, and `filtered_data.csv`.

### Python Integration
- **`src/hygeia_graph/preprocess_interface.py`**:
  - Validates data completeness (aborts if missing values found).
  - Wrapper for R subprocess execution.
- **`src/hygeia_graph/preprocess_utils.py`**:
  - Deterministic hashing for dataset and settings caching.

### UI ("Preprocessing" Page)
- **Settings**: Target selection, Family, Max Features, CV folds, etc.
- **Run**: Execution with caching support.
- **Results**:
  - Table of selected features.
  - Coefficient table.
  - Preview of filtered dataset.
- **Action**: **"Use filtered dataset"** button updates the active dataframe (`st.session_state.df`) and resets downstream artifacts, forcing a clean re-analysis workflow.

### Verification

#### Automated Tests
- **`tests/test_lasso_unit.py`**: Passed. Verified hashing consistency.
- **`tests/test_lasso_integration.py`**: Skipped (as expected in environment without R/glmnet). Designed to verify end-to-end flow on synthetic data.

#### Manual QA Scenarios
1. **Validation**: Upload dataset with missing values -> Preprocessing should block or R script should abort with clear error.
2. **Selection**: Run LASSO on a target. Confirm selected features appear in results.
3. **Filtering**: Click "Use filtered dataset".
   - Confirm `st.session_state.df` shape changes.
   - Confirm Navigation resets or warnings appear for "Data & Schema".
   - Confirm downstream results (MGM, Explore) are cleared.

## Usage Guide
1. Go to **Preprocessing** page.
2. Select **Target Variable**.
3. Click **Run LASSO Selection**.
4. Review selected columns.
5. Click **Use filtered dataset** to set the new dataframe for analysis.
6. Proceed to **Data & Schema** to validate the new schema and run MGM.
