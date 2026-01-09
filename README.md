# Hygeia-Graph

Mixed Graphical Models for medical network analysis — powered by Streamlit + R mgm.

## Features

- **Data Upload & Profiling**: Load CSV data with automatic type inference
- **Schema Builder**: Generate validated `schema.json` contracts
- **Model Specification**: Configure MGM with EBIC regularization
- **R MGM Backend**: Execute Mixed Graphical Models via R subprocess
- **Network Metrics**: Compute strength, betweenness, and closeness centrality
- **Interactive Visualization**: PyVis network graphs with customizable styling
- **Contract Validation**: JSON Schema validation for all artifacts

## Setup

### Prerequisites
- Python 3.10 or higher
- R 4.0+ (for MGM execution)
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/nguyenminh2301/Hygeia-Graph.git
cd Hygeia-Graph
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

3. Install R packages (if R is installed):
```bash
Rscript r/install.R
```

## Running the Application

Launch the Streamlit app:
```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

## Deployment

### Option 1: Local Run (with R)

Best for development and full functionality.

**Prerequisites**: Python 3.10+, R 4.0+

```bash
# Install Python deps
pip install -r requirements.txt
pip install -e .

# Install R packages
Rscript r/install.R

# Run
streamlit run app.py
```

### Option 2: Streamlit Community Cloud (Best Effort)

Deploy directly from GitHub with one click.

**Steps**:
1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select the repository and set main file to `app.py`
5. Deploy

**Configuration files used**:
- `requirements.txt` — Python dependencies
- `packages.txt` — APT packages (R, libcurl, etc.)

**Known Limitations**:
- R package installation (mgm, jsonlite) may require manual setup
- If R packages fail to install, use Docker deployment instead
- Data processing and schema building work without R

### Option 3: Docker (Recommended for Reproducibility)

Guaranteed environment with Python + R + all packages.

**Build the image**:
```bash
docker build -t hygeia-graph .
```

**Run the container**:
```bash
docker run -p 8501:8501 hygeia-graph
```

**Custom port**:
```bash
docker run -p 8080:8080 -e PORT=8080 hygeia-graph
```

**Deploy to cloud platforms**:
- **Google Cloud Run**: `gcloud run deploy`
- **Hugging Face Spaces**: Docker mode
- **Render.com**: Docker deploy
- **Fly.io**: `fly launch`

## Development

### Running Tests
```bash
pytest -q
```

> **Note**: R-dependent tests skip automatically if R is not installed.
> Run locally with R to fully verify the MGM pipeline.

### Linting
```bash
ruff check .
```

### Code Formatting
```bash
# Check
ruff format --check .

# Auto-format
ruff format .
```

## Contract Validation

Hygeia-Graph uses JSON Schema (Draft 2020-12) to validate three core contract types:
- `schema.json`: Dataset metadata and variable specifications
- `model_spec.json`: MGM model parameters and configuration
- `results.json`: MGM execution results and network data

### Validating Contracts

```bash
# Validate schema contract
python -m hygeia_graph.validate schema path/to/schema.json

# Validate model spec contract
python -m hygeia_graph.validate model_spec path/to/model_spec.json

# Validate results contract
python -m hygeia_graph.validate results path/to/results.json
```

### Using Validation in Python

```python
from hygeia_graph.contracts import (
    validate_schema_json,
    validate_model_spec_json,
    validate_results_json,
    ContractValidationError
)

try:
    validate_schema_json(my_schema_dict)
    print("Valid!")
except ContractValidationError as e:
    print(f"Validation failed: {e}")
```

## Project Structure

```
Hygeia-Graph/
├── app.py                      # Streamlit application entry point
├── src/
│   └── hygeia_graph/           # Main package
│       ├── __init__.py
│       ├── contracts.py        # JSON Schema validation
│       ├── data_processor.py   # CSV loading & profiling
│       ├── model_spec.py       # Model specification builder
│       ├── r_interface.py      # R subprocess bridge
│       ├── network_metrics.py  # NetworkX centrality
│       └── visualizer.py       # PyVis visualization
├── r/
│   ├── install.R               # R package installer
│   └── run_mgm.R               # MGM execution script
├── contracts/                   # JSON Schema contracts
│   ├── schema.schema.json
│   ├── model_spec.schema.json
│   └── results.schema.json
├── tests/                       # Test suite
├── reports/                     # Step reports
├── Dockerfile                   # Docker deployment
├── packages.txt                 # Streamlit Cloud APT packages
├── requirements.txt             # Python runtime dependencies
├── requirements-dev.txt         # Development dependencies
└── pyproject.toml              # Project configuration
```

## Troubleshooting

### "Rscript not found"
Install R from https://cran.r-project.org/ and ensure `Rscript` is on PATH.

### "mgm package missing"
Run `Rscript r/install.R` to install required R packages.

### "ModuleNotFoundError: hygeia_graph"
Install the package in development mode:
```bash
pip install -e .
```

### R tests skipping in CI
This is expected behavior. CI does not have R installed. Run tests locally with R to fully verify the pipeline.

## CI/CD

GitHub Actions automatically runs:
- Ruff linting (`ruff check`)
- Code formatting validation (`ruff format --check`)
- Test suite (`pytest`)

All checks must pass before merging pull requests.

## License

MIT License — see LICENSE file for details.
