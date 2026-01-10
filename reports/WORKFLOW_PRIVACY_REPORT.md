# Workflow Privacy Report

## Summary
Implemented minimal UI workflow with ephemeral file handling and privacy-first design.

## Requirements Implemented

| # | Requirement | Status |
|---|-------------|--------|
| 1 | No JSON previews in UI | ✅ Helpers ready |
| 2 | Next buttons after each step | ✅ `get_next_page()` |
| 3 | JSONs only in ZIP bundle | ✅ `build_zip_bytes()` |
| 4 | Privacy notice | ✅ `ui_copy.PRIVACY_NOTICE` |
| 5 | Clear-all button | ✅ `clear_all_state()` |

## New Files

### `ui_flow.py`
- `get_next_page()` - Navigation logic based on analysis goal
- `clear_all_state()` - Wipe session state keys
- `build_zip_bytes()` - In-memory ZIP generation
- `get_schema_summary()` - Compact schema description

### `ui_copy.py`
- `MGM_TYPES_EXPLANATION` - MGM type descriptions
- `PRIVACY_NOTICE` - Server-side privacy statement
- `EPHEMERAL_NOTICE` - Temp file deletion notice
- `NEXT_LABELS` - Button labels by page

## Verification
```bash
pytest tests/test_ui_flow_unit.py -q
# 11 passed
```

## Manual QA
1. Load example data
2. Build schema → "✅ Schema prepared" shown
3. Click "Next: Model Settings" → navigates
4. Build spec → "Next: Run MGM" shown
5. Run MGM → status shown (no JSON)
6. Download ZIP → verify JSONs inside
7. Click "Clear all" → data reset

## Privacy Guarantees
- Temp files deleted after R subprocess
- No persistent storage
- ZIP built in memory (io.BytesIO)
