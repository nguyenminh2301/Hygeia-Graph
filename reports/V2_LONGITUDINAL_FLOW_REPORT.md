# V2 Longitudinal Flow Report

## Summary
Implemented V2 Longitudinal Flow feature for visualizing T1→T2 transitions using Sankey diagrams.

## Deliverables

### Core Module: `src/hygeia_graph/longitudinal_flow.py`
- `detect_longitudinal_pairs()` - Auto-detect _T1/_T2 pairs
- `validate_pair_data()` - Validate cardinality constraints
- `build_transition_table()` - Build source→target counts
- `build_sankey_nodes_links()` - Prepare Plotly Sankey data
- `make_sankey_figure()` - Create interactive Sankey
- `figure_to_html()` / `figure_to_json()` - Export functions

### Export Module: `src/hygeia_graph/longitudinal_flow_exports.py`
- `export_transitions_csv()`
- `export_sankey_html()`
- `export_sankey_json()`

### Tests: `tests/test_longitudinal_flow_unit.py`
- 9 tests covering detection, validation, transitions, Sankey, HTML export

## Verification

```bash
pytest tests/test_longitudinal_flow_unit.py -q
# 9 passed
```

## Usage Example

```python
from hygeia_graph.longitudinal_flow import (
    detect_longitudinal_pairs,
    build_transition_table,
    build_sankey_nodes_links,
    make_sankey_figure,
)

# Auto-detect pairs
pairs = detect_longitudinal_pairs(df)

# Build transitions
transitions = build_transition_table(df, pairs[0]["t1"], pairs[0]["t2"])

# Create Sankey
nodes_links = build_sankey_nodes_links(transitions)
fig = make_sankey_figure(nodes_links, title="Symptom Flow T1→T2")
```

## Manual QA
1. Upload dataset with `*_T1` and `*_T2` columns
2. Build flow and verify Sankey renders
3. Export transitions.csv and sankey.html
