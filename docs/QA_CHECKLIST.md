# QA Checklist for Hygeia-Graph

> Complete this checklist before each release or HF demo.

## Pre-requisites
- [ ] All unit tests pass (`pytest tests/`)
- [ ] E2E smoke passes (`python scripts/e2e_smoke.py`)
- [ ] Linting clean (`ruff check .`)

---

## Layer 4: Manual QA on Hugging Face

### 1. Cold Start
- [ ] HF Space loads without errors
- [ ] Home page displays README content correctly
- [ ] Language selector works (EN/VI)

### 2. Data Upload
- [ ] Upload `assets/example_data.csv`
- [ ] Data preview shows correctly
- [ ] Missing rate = 0% (clean data)

### 3. Schema Builder
- [ ] Auto-inferred types are correct (g/c/p for each column)
- [ ] Manual type edits work
- [ ] "Validate Schema" button → ✅ valid
- [ ] Download `schema.json` works

### 4. Model Settings
- [ ] EBIC gamma slider changes value
- [ ] Alpha slider changes value
- [ ] "Build & Validate" → ✅ valid
- [ ] Download `model_spec.json` works

### 5. Run MGM
- [ ] Pre-run checklist all ✅
- [ ] Click "Run MGM" → completes without error
- [ ] Edge count displayed
- [ ] R posthoc computed (if checkbox enabled)

### 6. Explore Page
- [ ] Overview tab: nodes/edges count correct
- [ ] Network tab: PyVis renders, zoom/pan works
- [ ] Threshold slider changes edge count
- [ ] Node Metrics tab: Strength/EI table correct
- [ ] Edges tab: table with source/target/weight
- [ ] Export tab: downloads work (results.json, CSV, HTML)

### 7. Robustness (if R available)
- [ ] Settings expandable
- [ ] Run bootnet (demo: nBoots=50) → completes
- [ ] CS coefficients displayed
- [ ] Export CSV/JSON works

### 8. Simulation (Experimental)
- [ ] Disclaimer banner visible
- [ ] Select node, set delta
- [ ] Run simulation → bar chart displayed
- [ ] Top affected nodes make sense (neighbors)
- [ ] Export JSON/CSV works

### 9. Preprocessing (LASSO)
- [ ] Select target variable
- [ ] Run LASSO → completes
- [ ] Selected features displayed
- [ ] "Apply to Analysis" resets pipeline correctly

### 10. Publication Pack
- [ ] Generate pack → completes
- [ ] Download ZIP
- [ ] ZIP contains:
  - [ ] `publication_pack/figures/*.svg`
  - [ ] `publication_pack/figures/*.pdf`
  - [ ] `publication_pack/tables/adjacency_matrix.csv`
  - [ ] `publication_pack/artifacts/results.json`
  - [ ] `publication_pack/meta/publication_pack_meta.json`
- [ ] SVG/PDF files open correctly

---

## Release Criteria for v0.1.0
- [ ] All Layer 1 (unit) tests pass
- [ ] All Layer 2 (integration) tests pass or skip gracefully
- [ ] E2E smoke test passes
- [ ] Full manual QA checklist completed
- [ ] README updated with features
- [ ] CHANGELOG updated
- [ ] Version bumped in `pyproject.toml`

---

**QA Completed By:** _______________  
**Date:** _______________  
**Version:** _______________
