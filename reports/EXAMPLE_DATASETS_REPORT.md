# Example Datasets Report

## Summary
Created 3 curated example datasets with in-app selector for quick testing.

## Datasets

| Dataset | Rows | Columns | Theme |
|---------|------|---------|-------|
| **Easy** | 140 | 6 | Inflammation & Sleep (Mini demo) |
| **Medium** | 280 | 12 | Metabolic–Mood Comorbidity |
| **Hard** | 600 | 30 | Multi-domain Hairball Stress Test |

## Features
- No missing values (clean data)
- Mixed variable types (Gaussian, Categorical, Count)
- Correlated variables for interpretable networks
- Recommended settings applied when loading

## UI Integration
- Radio selector: "Upload file" / "Use example dataset"
- Dropdown for Easy/Medium/Hard selection
- Shows goal and notes for each example
- One-click "Load Example Dataset" button

## Verification
```bash
pytest tests/test_example_datasets.py -q
# 11 passed
```

## Files
- `assets/example_easy.csv`
- `assets/example_medium.csv`  
- `assets/example_hard.csv`
- `src/hygeia_graph/example_datasets.py`
