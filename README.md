---
title: Hygeia-Graph
emoji: 🧬
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# Hygeia-Graph

**Mixed Graphical Models for Medical Network Analysis**

Hygeia-Graph is an interactive Streamlit application that enables researchers to build and visualize Mixed Graphical Model (MGM) networks from medical datasets. It supports mixed variable types (continuous, categorical, count), uses EBIC regularization for sparse network estimation, and provides interactive PyVis visualization with exportable artifacts for reproducible research.

## Key Features

- **Mixed Variable Types**: Supports Gaussian (continuous), Categorical (nominal/ordinal), and Poisson (count) variables
- **EBIC Regularization**: Extended Bayesian Information Criterion for optimal sparsity tuning
- **Interactive Visualization**: PyVis network graphs with customizable node/edge styling
- **Centrality Metrics**: Strength, betweenness, and closeness centrality computation
- **Reproducible Artifacts**: Export `schema.json`, `model_spec.json`, `results.json` for full reproducibility
- **Contract Validation**: JSON Schema validation ensures artifact integrity

## Quickstart

### Prerequisites
- Python 3.10+
- R 4.0+ with `Rscript` on PATH (for MGM execution)

### Installation

```bash
# Clone repository
git clone https://github.com/nguyenminh2301/Hygeia-Graph.git
cd Hygeia-Graph

# Install Python dependencies
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .

# Install R packages
Rscript r/install.R
```

### Run the Application

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Tutorial: Run the Example

Follow these steps to test Hygeia-Graph with the included example dataset:

### Step 1: Upload Data
1. Launch the app: `streamlit run app.py`
2. In the sidebar, click **Browse files**
3. Select `assets/example_data.csv`
4. Wait for data profiling to complete

### Step 2: Review Variable Types
1. Scroll to the **Variable Settings** table
2. Verify inferred types:
   - Age, CRP → Gaussian (g)
   - Gender → Categorical (c)
   - CancerStage → Categorical (c), ordinal
   - HospitalDays, SymptomCount → Poisson (p)
3. Adjust if needed (uncommon with example data)

### Step 3: Export Schema (Optional)
1. Click **Export schema.json**
2. Compare with `assets/example_schema.json`

### Step 4: Configure Model Settings
1. Scroll to **Model Settings / EBIC**
2. Review defaults:
   - EBIC gamma: 0.5
   - Alpha: 0.5
   - Rule: AND
3. Adjust if experimenting

### Step 5: Run MGM
1. Click **🚀 Run MGM (EBIC)**
2. Wait for R subprocess (~10-30 seconds)
3. View execution status

### Step 6: Explore Results
1. **Network Tables**: View filtered edge table and centrality rankings
2. **Centrality**: Check which nodes are most central (e.g., CancerStage, HospitalDays)
3. **Adjust threshold**: Use slider to filter weak edges

### Step 7: Visualize Network
1. Scroll to **Interactive Network (PyVis)**
2. Explore the graph:
   - Drag nodes to rearrange
   - Hover for tooltips
   - Toggle physics/labels
3. Adjust edge threshold for clarity

### Step 8: Export Results
Download these artifacts:
- `results.json` — Full MGM output
- `edges_filtered.csv` — Edge table
- `centrality.csv` — Centrality metrics
- `network.html` — Standalone visualization

## Methods

Hygeia-Graph implements **pairwise Mixed Graphical Models (k=2)** using the R `mgm` package.

### Key Settings
| Setting | Default | Description |
|---------|---------|-------------|
| Lambda selection | EBIC | Extended Bayesian Information Criterion |
| EBIC gamma | 0.5 | Sparsity control (0–1) |
| Alpha | 0.5 | Elastic net mixing (0=Ridge, 1=Lasso) |
| Edge aggregator | max_abs | Map parameter blocks to scalar weights |
| Sign strategy | dominant | Assign edge sign from largest parameter |
| Missing policy | warn_and_abort | No internal imputation |

### Missing Data
Hygeia-Graph does **not** impute missing values. If missing data is detected, analysis aborts with a warning. Users must preprocess data externally (e.g., using MICE for multiple imputation).

📖 **Full details**: See [docs/METHODS.md](docs/METHODS.md)

## Reproducibility

### Saved Artifacts
Each analysis produces three JSON artifacts:

1. **schema.json**: Variable definitions, types, and metadata
2. **model_spec.json**: Model configuration and parameters
3. **results.json**: Network nodes, edges, and analysis metadata

### Traceability
- Each artifact includes `analysis_id` (UUID) linking them together
- Input files are hashed (SHA256) for verification
- Timestamps track when artifacts were created

### Re-running Analysis
With saved artifacts, you can:
1. Load the same data
2. Import `schema.json` and `model_spec.json`
3. Re-run MGM to reproduce identical results

## Deployment

### Local (Recommended for Development)
```bash
pip install -r requirements.txt -e .
Rscript r/install.R
streamlit run app.py
```

### Streamlit Community Cloud
Deploy from GitHub to [share.streamlit.io](https://share.streamlit.io):
- Uses `requirements.txt` + `packages.txt`
- ⚠️ R packages may require manual setup

### Docker (Recommended for Production)
```bash
# Build
docker build -t hygeia-graph .

# Run
docker run -p 8501:8501 hygeia-graph
```

### Hugging Face Spaces (Docker)
Automated deployment via GitHub Actions:

1. **Create a Hugging Face Space** (Docker SDK)
2. **Add GitHub Secrets**:
   - `HF_TOKEN`: Your Hugging Face write token
   - `HF_SPACE`: Your space name (e.g., `username/hygeia-graph`)
3. **Push to main**: Deployment triggers automatically

**Note**: Runs on free CPU with ephemeral disk. Port 7860.

📖 **Deployment details**: See [reports/STEP9_REPORT.md](reports/STEP9_REPORT.md)

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError: hygeia_graph | `pip install -e .` |
| Rscript not found | Install R and add to PATH |
| mgm package missing | `Rscript r/install.R` |
| Missing values abort | Preprocess data to remove/impute NA |

📖 **Full guide**: See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## Project Structure

```
Hygeia-Graph/
├── app.py                      # Streamlit entry point
├── src/hygeia_graph/           # Python package
│   ├── contracts.py            # JSON Schema validation
│   ├── data_processor.py       # CSV loading & profiling
│   ├── model_spec.py           # Model specification builder
│   ├── r_interface.py          # R subprocess bridge
│   ├── network_metrics.py      # Centrality computation
│   └── visualizer.py           # PyVis visualization
├── r/                          # R backend
│   ├── install.R               # Package installer
│   └── run_mgm.R               # MGM execution
├── contracts/                  # JSON Schema contracts
├── assets/                     # Example data & artifacts
├── docs/                       # Documentation
├── tests/                      # Test suite
└── reports/                    # Step reports
```

## License

This project is licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE) for details.

### Disclaimer

Hygeia-Graph is a **research tool** intended for exploratory network analysis. It is **not** a medical device and should **not** be used for clinical decision-making or diagnosis. Results should be interpreted by qualified researchers in the context of the specific study design and data limitations.

## Citation

If you use Hygeia-Graph in your research, please cite:

```bibtex
@software{hygeia_graph,
  author       = {Nguyen, Minh},
  title        = {{Hygeia-Graph}: Mixed Graphical Models for Medical Network Analysis},
  year         = {2026},
  version      = {0.1.0},
  url          = {https://github.com/nguyenminh2301/Hygeia-Graph}
}
```

See also: [CITATION.cff](CITATION.cff) | [CITATION.bib](CITATION.bib)

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

Ensure all tests pass: `pytest -q && ruff check .`

## Acknowledgments

- [mgm R package](https://cran.r-project.org/package=mgm) by Haslbeck & Waldorp
- [Streamlit](https://streamlit.io/) for the web framework
- [PyVis](https://pyvis.readthedocs.io/) for network visualization
- [NetworkX](https://networkx.org/) for graph algorithms
