# Descriptive Statistics Feature Report

## Summary
Added comprehensive descriptive statistics for all dataset variables with report integration.

## Features

### Variable Classification
- Auto-detect from data or use schema
- Types: continuous (Gaussian), count (Poisson), nominal, ordinal

### Missing Value Summary
- Total missing cells and rate
- Per-column missing counts

### Statistical Summaries
| Type | Metrics |
|------|---------|
| Continuous | mean, SD, median, Q1/Q3, IQR, min, max, normality test |
| Count | mean, var, dispersion ratio, Poisson diagnostics |
| Categorical | level counts, rates, entropy, top level |

### Normality Tests
- Shapiro-Wilk for n ≤ 5000
- D'Agostino K² for larger samples
- Deterministic sampling (seed=0)

## Output Files
- `variable_summary.csv` - One row per variable
- `categorical_levels.csv` - Level distribution for categoricals
- `descriptives.json` - JSON payload for report integration

## Verification
```bash
pytest tests/test_descriptives_unit.py -q
# 11 passed
```

## Dependencies
Added `scipy` to requirements.txt for statistical tests.
