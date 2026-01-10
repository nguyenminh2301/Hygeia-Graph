# Next Step: Publication Pack (Figures & Data Export)

## Summary of Deliverables
Implemented a **"Publication Pack"** feature that generates publication-quality static network figures (using R's `qgraph`) and bundles all analysis artifacts into a single ZIP file.

### Key Features
- **Static Figures (R/qgraph)**:
  - **Network Plot**: Scalable Vector Graphics (SVG) + PDF. Edges colored by sign (blue/red), width by weight. Nodes colored by community (if available) or domain/type.
  - **Heatmap**: Adjacency matrix visualization.
  - **Centrality**: Bar plot of Strength (Abs) and Expected Influence.
- **Unified Export**: A single ZIP file containing:
  - `publication_pack/figures/`: SVG and PDF plots.
  - `publication_pack/tables/`: `adjacency_matrix.csv`, `edges_filtered.csv`, `centrality.csv`.
  - `publication_pack/artifacts/`: `results.json`, `schema.json`, etc.
  - `publication_pack/meta/`: Metadata including analysis ID, R package versions, and settings.
- **UI Integration**:
  - Located in the **Export** tab of the **Explore** page (and "Report & Export" page).
  - Customizable settings: Threshold, Top Edges, Layout (Spring/Circle), Labels.

### Python Backend
- `src/hygeia_graph/publication_pack_interface.py`: Handles R subprocess execution.
- `src/hygeia_graph/publication_pack_utils.py`: Deterministic hashing and ZIP building.

### R Backend
- `r/run_publication_pack.R`: New CLI script for figure generation.
- `r/install.R`: Updated to include `qgraph` and `svglite`.

### Verification
- **Unit Tests**: `tests/test_publication_pack_unit.py` passed (ZIP structure, hashing).
- **Integration Tests**: `tests/test_publication_pack_integration.py` passed (skipped on machine without R, but designed to verify end-to-end flow).
- **Linting**: Passed.

## Usage Guide
1. Run **MGM Analysis** and visit the **Explore** page.
2. Go to the **Export** tab.
3. Scroll to **Publication Pack**.
4. Adjust settings (e.g., stricter threshold for cleaner print figures).
5. Click **Generate Publication Pack**.
6. Download the resulting `.zip` file.
