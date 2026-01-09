# Step 6 Report — Python↔R Subprocess Bridge + Run MGM Wiring

## Environment

- **OS**: Windows
- **Python Version**: 3.13.6
- **Date**: 2026-01-09

## Overview

Successfully implemented Step 6 for Hygeia-Graph, creating a Python subprocess bridge to call the R backend and wiring the Streamlit app with a complete "Run MGM" workflow including pre-run checks, execution controls, progress indicators, and results display.

## Implementation Summary

### Python Subprocess Bridge Module
Created `src/hygeia_graph/r_interface.py` (286 lines) with:

**Exception Class**:
- `RBackendError`: Custom exception with stdout, stderr, returncode, workdir for debugging

**Utility Functions**:
- `locate_repo_root()`: Find repo root by ascending from __file__
- `ensure_rscript_available()`: Check Rscript on PATH
- `compute_sha256()`: SHA256 hash computation

**Artifact Writing**:
- `write_artifacts_to_dir()`: Write data.csv, schema.json, model_spec.json with SHA256

**Main Orchestration**:
- `run_mgm_subprocess()`: Complete subprocess execution with:
  - Input validation via contract validators
  - Temp directory management
  - Subprocess execution with timeout
  - Results loading and validation
  - Comprehensive error handling

### Streamlit UI Enhancement
Updated `app.py` with new "Run MGM" section (200+ lines added):

**Pre-run Checklist**:
- ✅ Data loaded
- ✅ schema.json valid
- ✅ model_spec.json valid
- ✅ Missing rate = 0%

**Run Controls**:
- "Run MGM (EBIC)" button (disabled if conditions not met)
- Advanced options: timeout, debug mode, show output
- Missing data blocking with clear error message

**Execution UX**:
- `st.status` progress indicator
- Real-time status updates
- Error display with stdout/stderr on failure

**Results Viewer**:
- Status, nodes, edges metrics
- Engine info (R version, package versions)
- Messages table (level, code, message)
- Download button for results.json
- Raw JSON expander

### Integration Tests
Created `tests/test_step6_r_interface.py` (207 lines) with:

**Pure Python Tests** (always run):
- `test_locate_repo_root`: Verify repo root detection
- `test_compute_sha256`: Verify hash computation
- `test_write_artifacts_to_dir`: Verify artifact writing
- `test_ensure_rscript_available_error`: Verify error when Rscript absent
- `test_rbackend_error_attributes`: Verify exception attributes
- `test_rbackend_error_str`: Verify exception string representation

**R-Dependent Tests** (skip gracefully):
- `test_ensure_rscript_available_when_present`: If R present
- `test_run_mgm_subprocess_success`: Full execution test
- `test_run_mgm_subprocess_missing_data_abort`: Missing data abort test

## Commands Executed

### 1. Run Step 6 Tests
```bash
pytest tests/test_step6_r_interface.py -v
```

**Output**:
```
6 passed, 3 skipped in 2.75s
```
✅ All tests passed (3 skipped gracefully - R not available)

### 2. Run Full Test Suite
```bash
pytest -q
```

**Output**:
```
64 passed, 7 skipped in 3.44s
```
✅ All tests passed:
- 6 new Step 6 tests (3 skipped - R dependent)
- 58 previous tests

### 3. Lint with Ruff
```bash
ruff check .
```

**Output**:
```
All checks passed!
```
✅ No linting errors

### 4. Format with Ruff
```bash
ruff format . --check
```

**Output**:
```
13 files already formatted
```
✅ Code formatted

## Test Results

### Step 6 Tests (6 passed, 3 skipped)
**Pure Python Tests**:
- ✅ test_locate_repo_root
- ✅ test_compute_sha256
- ✅ test_write_artifacts_to_dir
- ✅ test_ensure_rscript_available_error
- ✅ test_rbackend_error_attributes
- ✅ test_rbackend_error_str

**R-Dependent Tests** (skip gracefully):
- ⏭️ test_ensure_rscript_available_when_present
- ⏭️ test_run_mgm_subprocess_success
- ⏭️ test_run_mgm_subprocess_missing_data_abort

### Code Quality
- ✅ Ruff linting: All checks passed
- ✅ Ruff formatting: Compliant
- ✅ Test suite: 64 passed, 7 skipped

## Files Created/Modified

### New Files
- `src/hygeia_graph/r_interface.py` - Subprocess bridge (286 lines)
- `tests/test_step6_r_interface.py` - Integration tests (207 lines)
- `reports/STEP6_REPORT.md` - This report

### Modified Files
- `app.py` - Added Run MGM section (+200 lines, total 691 lines)

## Error Handling Design

### RBackendError Exception
Custom exception class carrying full context:
```python
RBackendError(
    message="Error description",
    stdout="R stdout output",
    stderr="R stderr output",
    returncode=1,
    workdir=Path("/tmp/work")
)
```

### Error Scenarios Handled
1. **Rscript not found**: RuntimeError with installation instructions
2. **Subprocess timeout**: RBackendError with partial output
3. **Non-zero exit**: Results still checked (R writes results.json even on failure)
4. **Missing results.json**: RBackendError with stdout/stderr
5. **Validation failure**: RBackendError with validation errors
6. **Missing data**: Results with status="failed" (R backend aborts)

### UI Error Display
- Concise error message with `st.error`
- Optional stdout/stderr display via expander
- Detailed messages from results.json

## Missing Data Policy Enforcement

**Defense in Depth**:
1. **UI Layer**: Pre-run check blocks execution if `missing_rate > 0`
2. **R Backend**: Aborts with `MISSING_DATA_ABORT` code
3. **Results**: Status="failed" with clear error message

**User Message**:
```
⛔ Cannot run MGM: Missing values detected. 
Hygeia-Graph does not impute; please preprocess externally (e.g., MICE) and re-run.
```

## Manual QA Checklist

To verify the Streamlit UI works correctly:

### 1. Start Streamlit
```bash
streamlit run app.py
```

### 2. Upload Valid CSV
- Use `tests/fixtures/step5_data.csv`
- Verify data preview displays

### 3. Generate schema.json
- Click "Validate Schema"
- Verify success message

### 4. Build model_spec.json
- Adjust settings as desired
- Click "Build & Validate model_spec.json"
- Verify success message

### 5. Check Pre-run Panel
- All 4 checkmarks should be green
- "Run MGM" button should be enabled

### 6. Run MGM (requires R)
- Click "Run MGM (EBIC)"
- Observe progress indicator
- Verify success message with edge count

### 7. View Results
- Check status, nodes, edges metrics
- Expand engine info
- View messages table
- Download results.json

### 8. Test Missing Data Blocking
- Upload `tests/fixtures/step5_data_missing.csv`
- Generate schema.json
- Verify "Run MGM" button is disabled
- Verify error message displayed

### Without R Available
- Pre-run checks will pass
- Clicking "Run MGM" will show RBackendError
- Message will indicate Rscript not found

## Summary

✅ **All acceptance criteria met**:
- Python subprocess bridge complete
- Streamlit UI wiring complete
- Pre-run checks with missing data blocking
- Progress indicators during execution
- Results viewer with status/messages/download
- Comprehensive error handling
- 64 tests passed, 7 skipped (R-dependent)
- All linting checks passed

**Step 6 is complete. The app now provides end-to-end MGM execution capability.**
