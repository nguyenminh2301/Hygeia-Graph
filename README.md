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
