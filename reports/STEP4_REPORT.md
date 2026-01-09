# Step 4 Report — Model Spec Builder + Settings Panel

## Environment

- **OS**: Windows
- **Python Version**: 3.13.6
- **Date**: 2026-01-09

## Overview

Successfully implemented Step 4 for Hygeia-Graph, building the model specification builder with EBIC regularization settings, edge mapping configuration, comprehensive Streamlit UI controls, and validated model_spec.json export with locked field enforcement.

## Implementation Summary

### Core Model Spec Module
Created `src/hygeia_graph/model_spec.py` (243 lines) with:
- `default_model_settings()`: Return default settings with all EBIC and edge mapping parameters
- `sanitize_settings()`: Validate and coerce user settings with clamping and normalization
- `build_model_spec()`: Construct validated model_spec.json from schema + settings
- `compute_sha256_bytes()`: SHA256 utility for reproducibility

**Locked Fields (Non-Negotiable)**:
- `lambda_selection`: Always "EBIC" (enforced in sanitize_settings)
- `missing_policy.action`: Always "warn_and_abort" (enforced in sanitize_settings)
- `mgm.k`: Always 2 (pairwise only)

**Configurable Parameters**:
- EBIC: gamma [0-1], alpha [0-1]
- Regularization: rule_reg (AND/OR), overparameterize, scale_gaussian, sign_info
- Edge mapping: aggregator, sign_strategy, zero_tolerance
- Random seed: Integer >= 0
- Visualization: edge_threshold, layout
- Centrality: compute, weighted, use_absolute_weights

### Streamlit UI Enhancement
Updated `app.py` with comprehensive Model Settings section:

**Section 5: Model Settings (EBIC Regularization)**
- EBIC Gamma slider [0.0-1.0]
- Alpha slider [0.0-1.0]  
- Rule Regularization selectbox [AND, OR]
- Checkboxes: overparameterize, scale_gaussian, sign_info
- Random seed number input

**Edge Mapping Configuration**
- Aggregator selectbox: [max_abs, l2_norm, mean, mean_abs, sum_abs, max]
- Sign strategy selectbox: [dominant, mean, none]
- Zero tolerance number input

**Visualization & Centrality (Optional)**
- Edge threshold, layout algorithm
- Centrality computation options

**Section 6: Build & Export**
- "Build & Validate model_spec.json" button
- Download button (enabled only after validation)
- Locked field enforcement notification
- JSON preview expander

### Testing
Created `tests/test_step4_model_spec.py` (352 lines) with 13 comprehensive tests:
- Default settings structure and values (3 tests)
- Model spec building and validation (5 tests)
- Settings sanitization and coercion (5 tests)

## Commands Executed

### 1. Run Step 4 Tests
```bash
pytest tests/test_step4_model_spec.py -v
```

**Output**:
```
13 passed in 2.98s
```
✅ All Step 4 tests passed

### 2. Run Full Test Suite
```bash
pytest -q
```

**Output**:
```
..........................................................               [100%]
58 passed in 6.35s
```
✅ All tests passed (13 Step 4 + 45 previous steps)

### 3. Lint with Ruff
```bash
ruff check . --fix
```

**Output**:
```
All checks passed!
```
✅ No linting errors

### 4. Format with Ruff
```bash
ruff format .
```

**Output**:
```
3 files reformatted, 7 files left unchanged
```
✅ Code formatted

## Test Results

### Step 4 Tests (13/13 passed)
**Default Settings**:
- ✅ Locked fields (EBIC, warn_and_abort)
- ✅ Complete structure
- ✅ Correct default values

**Build Model Spec**:
- ✅ Validates against contract
- ✅ Forces locked fields
- ✅ Includes all required fields
- ✅ Generates UUID when not provided
- ✅ Includes optional SHA256 hashes

**Settings Sanitization**:
- ✅ Clamps numeric values
- ✅ Forces locked fields
- ✅ Handles missing fields
- ✅ Normalizes enums
- ✅ Coerces booleans

### Code Quality
- ✅ Ruff linting: All checks passed
- ✅ Ruff formatting: Compliant
- ✅ All 58 tests passed (cumulative)

## Files Created/Modified

### New Files
- `src/hygeia_graph/model_spec.py` - Model spec builder (243 lines)
- `tests/test_step4_model_spec.py` - Test suite (352 lines)
- `reports/STEP4_REPORT.md` - This report

### Modified Files
- `app.py` - Added Model Settings UI (497 lines total, +238 lines)

## Locked Field Enforcement

The implementation rigorously enforces locked design decisions:

1. **Lambda Selection = "EBIC"**:
   - Hard-coded in `sanitize_settings()` (line 74)
   - Any user attempt to change is ignored
   - Validated in tests

2. **Missing Policy = "warn_and_abort"**:
   - Hard-coded in `sanitize_settings()` (line 98)
   - Any user attempt to change is ignored
   - Validated in tests

3. **MGM k = 2**:
   - Always set to 2 (pairwise only)
   - Not exposed in UI

These are non-negotiable and cannot be bypassed through the UI or API.

## Settings Sanitization

The `sanitize_settings()` function provides robust input validation:
- **Clamping**: Numeric values clamped to valid ranges (e.g., gamma [0-1])
- **Type coercion**: Converts to correct types (int, float, bool)
- **Enum normalization**: Case-sensitive enum matching with fallback to defaults
- **Missing values**: Fills in defaults for any missing fields

This ensures model specs are always valid regardless of user input.

## Manual QA Checklist

To verify the Streamlit UI works correctly:

1. **Start Streamlit**:
   ```bash
   streamlit run app.py
   ```

2. **Navigate** to "Data Upload & Schema Builder"

3. **Upload CSV** (from Step 3) and generate schema.json

4. **Scroll to Step 5**: Model Settings (EBIC Regularization)

5. **Adjust settings**:
   - Move EBIC gamma slider → verify value updates
   - Change edge mapping aggregator → verify dropdown works
   - Toggle checkboxes → verify state changes

6. **Build model spec**:
   - Click "Build & Validate model_spec.json"
   - Should show ✅ success message
   - Should show 🔒 locked fields notification

7. **Verify locked fields**:
   - Open JSON preview
   - Confirm `lambda_selection: "EBIC"`
   - Confirm `missing_policy.action: "warn_and_abort"`

8. **Download**:
   - Click "Download model_spec.json"
   - Verify file is valid JSON

9. **External validation**:
   ```bash
   python -m hygeia_graph.validate model_spec model_spec.json
   ```
   Should return exit code 0

## Summary

✅ **All acceptance criteria met**:
- Model spec builder module complete with all required functions
- Settings sanitization with clamping and coercion
- Locked fields rigorously enforced (EBIC, warn_and_abort)
- Comprehensive Streamlit UI with all controls
- 13/13 Step 4 tests pass
- All linting checks pass
- Validation against contract succeeds
- Comprehensive report with test evidence

**Step 4 is complete and ready for Step 5 (R/MGM integration).**
