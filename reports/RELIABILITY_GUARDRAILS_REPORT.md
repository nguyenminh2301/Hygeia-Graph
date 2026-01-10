# Reliability Guardrails Report

## Summary
Implemented environment health checks and resource safety guardrails for HF deployment.

## Deliverables

### Python Modules
- **`src/hygeia_graph/diagnostics.py`**:
  - `check_rscript()` - Verify Rscript availability
  - `check_r_packages()` - Check required/optional R packages
  - `run_r_install()` - Run `r/install.R` with logs
  - `build_diagnostics_report()` - Full system report

- **`src/hygeia_graph/resource_guardrails.py`**:
  - `recommend_defaults()` - Safe defaults based on network size
  - `enforce_explore_config()` - Clamp config with warnings
  - `estimate_memory()` - Approximate memory usage

### UI Integration
- **Sidebar "Environment" panel**:
  - Shows Rscript status (✅/❌)
  - Shows core package status
  - "Download diagnostics.json" button

### Tests
- `tests/test_reliability_diagnostics_unit.py` - 14 tests

## Guardrail Thresholds

| Condition | Action |
|-----------|--------|
| n_nodes > 80 | Hide labels |
| n_nodes > 120 | Limit to 1000 edges |
| n_nodes > 200 | Disable PyVis, increase threshold |
| n_edges > 5000 | Require threshold > 0 |

## Verification

```bash
pytest tests/test_reliability_diagnostics_unit.py -q
# Expected: 14 passed
```

## Manual QA
1. Run app locally
2. Check sidebar shows environment status
3. Test with R missing: status should show ❌
4. Test download diagnostics.json
