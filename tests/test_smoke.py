"""Smoke tests for Hygeia Graph."""

from pathlib import Path

import hygeia_graph


def test_package_import():
    """Test that hygeia_graph package can be imported."""
    assert hygeia_graph is not None
    assert hasattr(hygeia_graph, "__version__")


def test_contract_schemas_exist():
    """Test that all expected contract schema files exist."""
    # Get repository root (tests/ is at root level)
    repo_root = Path(__file__).resolve().parent.parent
    contracts_dir = repo_root / "contracts"

    expected_schemas = [
        "schema.json",
        "model_spec.json",
        "results.json",
    ]

    for schema_file in expected_schemas:
        schema_path = contracts_dir / schema_file
        assert schema_path.exists(), f"Missing contract schema: {schema_file}"
        assert schema_path.is_file(), f"Contract schema is not a file: {schema_file}"
