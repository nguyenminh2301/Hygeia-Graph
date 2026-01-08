"""Contract validation for Hygeia Graph.

This module provides JSON Schema validation for the three core contract types:
- schema.json: Dataset metadata and variable specifications
- model_spec.json: MGM model parameters and configuration
- results.json: MGM execution results and network data
"""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError


class ContractValidationError(Exception):
    """Exception raised when contract validation fails."""

    def __init__(self, kind: str, errors: list[dict[str, Any]]):
        """Initialize validation error.

        Args:
            kind: Contract type ("schema", "model_spec", or "results")
            errors: List of error dictionaries with keys:
                - path: JSON Pointer path to error location
                - message: Human-readable error message
                - validator: Validator that failed (optional)
                - schema_path: Path in schema to failing constraint (optional)
        """
        self.kind = kind
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message from error list."""
        lines = [f"Validation failed for {self.kind}:"]
        for err in self.errors:
            path = err.get("path", "/")
            msg = err.get("message", "Unknown error")
            lines.append(f"  {path}: {msg}")
        return "\n".join(lines)


# Schema cache to avoid reloading
_SCHEMA_CACHE: dict[str, Draft202012Validator] = {}


def find_repo_root(start: Path | None = None) -> Path:
    """Find repository root by scanning up for contracts/ directory.

    Args:
        start: Starting path (defaults to this file's directory)

    Returns:
        Path to repository root

    Raises:
        FileNotFoundError: If contracts/ directory not found
    """
    if start is None:
        start = Path(__file__).resolve().parent

    current = start.resolve()
    for parent in [current] + list(current.parents):
        contracts_dir = parent / "contracts"
        if contracts_dir.is_dir():
            return parent

    raise FileNotFoundError("Could not find repository root (no 'contracts/' directory found)")


def load_schema(kind: str) -> Draft202012Validator:
    """Load and cache JSON Schema validator for given contract type.

    Args:
        kind: Contract type ("schema", "model_spec", or "results")

    Returns:
        JSON Schema validator instance

    Raises:
        ValueError: If kind is invalid
        FileNotFoundError: If schema file not found
    """
    if kind in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[kind]

    # Map kind to schema filename
    schema_files = {
        "schema": "schema.json",
        "model_spec": "model_spec.json",
        "results": "results.json",
    }

    if kind not in schema_files:
        raise ValueError(
            f"Invalid contract kind: {kind}. Must be one of: {list(schema_files.keys())}"
        )

    # Load schema from contracts/ directory
    repo_root = find_repo_root()
    schema_path = repo_root / "contracts" / schema_files[kind]

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    # Create and cache validator
    validator = Draft202012Validator(schema)
    _SCHEMA_CACHE[kind] = validator

    return validator


def _extract_errors(validation_errors: list[ValidationError]) -> list[dict[str, Any]]:
    """Extract structured error information from jsonschema ValidationErrors.

    Args:
        validation_errors: List of validation errors

    Returns:
        List of error dictionaries
    """
    errors = []
    for err in validation_errors:
        # Build JSON Pointer path
        path_parts = [""] + list(err.absolute_path)
        json_pointer = "/".join(str(p) for p in path_parts)

        error_dict = {
            "path": json_pointer if json_pointer else "/",
            "message": err.message,
        }

        if err.validator:
            error_dict["validator"] = err.validator

        if err.schema_path:
            schema_path_parts = list(err.schema_path)
            error_dict["schema_path"] = "/".join(str(p) for p in schema_path_parts)

        errors.append(error_dict)

    return errors


def validate_schema_json(obj: dict[str, Any]) -> None:
    """Validate a schema.json contract.

    Args:
        obj: Parsed JSON object to validate

    Raises:
        ContractValidationError: If validation fails
    """
    validator = load_schema("schema")
    errors = list(validator.iter_errors(obj))

    if errors:
        raise ContractValidationError("schema", _extract_errors(errors))


def validate_model_spec_json(obj: dict[str, Any]) -> None:
    """Validate a model_spec.json contract.

    Args:
        obj: Parsed JSON object to validate

    Raises:
        ContractValidationError: If validation fails
    """
    validator = load_schema("model_spec")
    errors = list(validator.iter_errors(obj))

    if errors:
        raise ContractValidationError("model_spec", _extract_errors(errors))


def validate_results_json(obj: dict[str, Any]) -> None:
    """Validate a results.json contract.

    Args:
        obj: Parsed JSON object to validate

    Raises:
        ContractValidationError: If validation fails
    """
    validator = load_schema("results")
    errors = list(validator.iter_errors(obj))

    if errors:
        raise ContractValidationError("results", _extract_errors(errors))


def load_json(path: str | Path) -> dict[str, Any]:
    """Load JSON file from path.

    Args:
        path: Path to JSON file

    Returns:
        Parsed JSON object

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_file(kind: str, path: Path) -> None:
    """Validate a JSON file against its contract schema.

    Args:
        kind: Contract type ("schema", "model_spec", or "results")
        path: Path to JSON file

    Raises:
        ContractValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    obj = load_json(path)

    validators = {
        "schema": validate_schema_json,
        "model_spec": validate_model_spec_json,
        "results": validate_results_json,
    }

    if kind not in validators:
        raise ValueError(
            f"Invalid contract kind: {kind}. Must be one of: {list(validators.keys())}"
        )

    validators[kind](obj)
