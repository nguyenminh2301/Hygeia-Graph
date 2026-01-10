# UX Guidance Report

## Summary
Implemented UX improvements for better user guidance and workflow navigation.

## Deliverables

### `src/hygeia_graph/ui_guidance.py`
- **Data format guidance:** Short + detailed notes about CSV requirements, variable types, missing data policy
- **Navigation helpers:** `get_next_page()`, `get_prev_page()`, `can_proceed_to_next()`
- **Branching hints:** Recommended defaults for EBIC gamma, alpha, threshold, etc.

### UI Integration
- Added data format notes at top of Data & Schema page
- Added "More details" expander for extended guidance
- Added "Next: Model Settings" button after schema completion

## Verification

```bash
pytest tests/test_ui_guidance_unit.py -q
# 14 passed
```

## Manual QA
1. Navigate to Data & Schema page
2. See data format requirements at top
3. Upload valid CSV, generate schema
4. "Next: Model Settings" button appears
5. Click to navigate to next step
