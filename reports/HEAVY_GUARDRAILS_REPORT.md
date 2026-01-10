# Heavy Module Guardrails Report

## Summary
Implemented guardrails for resource-intensive analysis modules to ensure safe defaults on constrained environments (HF Free CPU).

## Modules Protected

| Module | Safe Max | Hard Max | Default |
|--------|----------|----------|---------|
| **Bootnet** | boots≤500, cores≤1 | boots≤2000, cores≤2 | boots=200 |
| **NCT** | perms≤500, cores≤1 | perms≤5000, cores≤2 | perms=200 |
| **LASSO** | nfolds≤10, features≤100 | nfolds≤20, features≤300 | nfolds=5 |

## API

```python
from hygeia_graph.heavy_guardrails import (
    normalize_bootnet_settings,
    normalize_nct_settings,
    normalize_lasso_settings,
    should_require_advanced_unlock,
    render_messages_to_markdown,
)

# Normalize with advanced unlock OFF
norm, msgs = normalize_bootnet_settings(raw_settings, advanced_unlocked=False)
```

## Verification

```bash
pytest tests/test_heavy_guardrails_unit.py -q
# 22 passed
```

## Manual QA
1. Go to Bootnet page, set n_boots=2000
2. Verify clamp to 500 unless Advanced unlock ON
3. Go NCT page, enable edge_tests with perms=500
4. Verify edge_tests auto-disabled unless unlock
5. Go LASSO page, set max_features=500
6. Verify clamp to 100 unless unlock
