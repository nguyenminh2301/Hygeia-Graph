# Sprint A (Agent C) Report: Plots and Exports

## Summary of Deliverables
Implemented paper-friendly plots (Centrality Bar Plot, Adjacency Heatmap) using Plotly and export utilities (CSV, JSON, HTML).

### Library Choice
**Plotly** was chosen and added to `requirements.txt` because:
- It produces interactive, zoomable plots suitable for the web.
- It is standard in the Streamlit ecosystem (`st.plotly_chart`).
- It supports high-quality HTML exports.

### Files Created
- `src/hygeia_graph/plots.py`: Core logic for data prep and plotting.
- `src/hygeia_graph/exports.py`: Helper functions for `st.download_button`.
- `tests/test_sprintA_agentC_plots_and_exports.py`: Test suite.

## Verification

### Automated Tests
Executed `pytest` with 7 passed tests.
**Command**: `pytest tests/test_sprintA_agentC_plots_and_exports.py`
**Result**:
```
tests\test_sprintA_agentC_plots_and_exports.py .......                   [100%]
7 passed
```

### Code Quality
**Commands**:
- `ruff check .` -> Passed.
- `ruff format .` -> Passed.

## Integration Handshake (For Agent A)

Use the following snippets to wire the new functionality into the UI.

### 1. Build DataFrames
```python
from hygeia_graph.plots import (
    build_node_metrics_df,
    compute_edges_filtered_df,
    build_adjacency_matrix_df,
    make_centrality_bar_plot,
    make_adjacency_heatmap
)
from hygeia_graph.exports import df_to_csv_bytes, df_to_csv_bytes_with_index, plot_to_html_bytes

# Inputs from Session State
results = st.session_state["results_json"]
derived = st.session_state["derived_metrics_json"]
cfg = st.session_state["explore_config"]

# Compute DFs
node_metrics_df = build_node_metrics_df(derived)
edges_df = compute_edges_filtered_df(results, cfg)
adjacency_df = build_adjacency_matrix_df(results, cfg, value_mode="signed")
```

### 2. Render Plots
```python
# Centrality Plot
fig_bar = make_centrality_bar_plot(
    node_metrics_df, 
    metric="expected_influence", # or "strength_abs", "bridge_strength_abs"
    top_n=20
)
st.plotly_chart(fig_bar, use_container_width=True)

# Heatmap
fig_heat = make_adjacency_heatmap(adjacency_df)
st.plotly_chart(fig_heat, use_container_width=True)
```

### 3. Exports
Place these in the "Export" tab/section.
```python
# Edges
st.download_button(
    "Download Edges (filtered)",
    data=df_to_csv_bytes(edges_df),
    file_name="edges_filtered.csv",
    mime="text/csv"
)

# Centrality
st.download_button(
    "Download Centrality Metrics",
    data=df_to_csv_bytes(node_metrics_df),
    file_name="centrality_metrics.csv",
    mime="text/csv"
)

# Adjacency Matrix
st.download_button(
    "Download Adjacency Matrix",
    data=df_to_csv_bytes_with_index(adjacency_df),
    file_name="adjacency_matrix.csv",
    mime="text/csv"
)

# Heatmap HTML
st.download_button(
    "Download Heatmap (HTML)",
    data=plot_to_html_bytes(fig_heat),
    file_name="adjacency_heatmap.html",
    mime="text/html"
)
```
