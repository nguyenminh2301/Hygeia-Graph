# Hygeia-Graph

Graph-based analysis tool for healthcare contracts.

## Setup

### Prerequisites
- Python 3.10 or higher
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/nguyenminh2301/Hygeia-Graph.git
cd Hygeia-Graph
```

2. Install dependencies:
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

## Running the Application

Launch the Streamlit app:
```bash
streamlit run app.py
```

## Development

### Running Tests
```bash
pytest -q
```

### Linting
```bash
ruff check .
```

### Code Formatting
Check formatting:
```bash
ruff format --check .
```

Auto-format code:
```bash
ruff format .
```

## Contract Validation

Hygeia-Graph uses JSON Schema (Draft 2020-12) to validate three core contract types:
- `schema.json`: Dataset metadata and variable specifications
- `model_spec.json`: MGM model parameters and configuration
- `results.json`: MGM execution results and network data

### Validating Contracts

Validate a contract file using the CLI:

```bash
# Validate schema contract
python -m hygeia_graph.validate schema path/to/schema.json

# Validate model spec contract
python -m hygeia_graph.validate model_spec path/to/model_spec.json

# Validate results contract
python -m hygeia_graph.validate results path/to/results.json
```

Exit codes:
- `0`: Validation successful
- `1`: Validation failed (errors printed to stderr)

### Using Validation in Python

```python
from hygeia_graph.contracts import (
    validate_schema_json,
    validate_model_spec_json,
    validate_results_json,
    validate_file,
    ContractValidationError
)

# Validate a Python dict
try:
    validate_schema_json(my_schema_dict)
    print("Valid!")
except ContractValidationError as e:
    print(f"Validation failed: {e}")
    for error in e.errors:
        print(f"  {error['path']}: {error['message']}")

# Validate a file
from pathlib import Path
validate_file("schema", Path("path/to/schema.json"))
```

## Project Structure

```
Hygeia-Graph/
├── app.py                      # Streamlit application entry point
├── src/
│   └── hygeia_graph/          # Main package
│       └── __init__.py
├── contracts/                  # Contract schema files
│   ├── schema.json
│   ├── model_spec.json
│   └── results.json
├── tests/                      # Test suite
│   └── test_smoke.py
├── reports/                    # Step reports
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Development dependencies
└── pyproject.toml             # Project configuration
```

## CI/CD

GitHub Actions automatically runs:
- Ruff linting (`ruff check`)
- Code formatting validation (`ruff format --check`)
- Test suite (`pytest`)

All checks must pass before merging pull requests.
