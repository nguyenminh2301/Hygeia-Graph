"""CLI tool for validating Hygeia Graph contracts.

Usage:
    python -m hygeia_graph.validate schema path/to/schema.json
    python -m hygeia_graph.validate model_spec path/to/model_spec.json
    python -m hygeia_graph.validate results path/to/results.json
"""

import argparse
import sys
from pathlib import Path

from hygeia_graph.contracts import ContractValidationError, validate_file


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Validate Hygeia Graph JSON contracts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "kind",
        choices=["schema", "model_spec", "results"],
        help="Type of contract to validate",
    )

    parser.add_argument("file_path", type=Path, help="Path to JSON file to validate")

    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print errors (default: True)",
    )

    args = parser.parse_args()

    try:
        validate_file(args.kind, args.file_path)
        print(f"OK: {args.kind} {args.file_path}")
        return 0

    except FileNotFoundError as e:
        print(f"FAIL: {args.kind} {args.file_path}", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        return 1

    except ContractValidationError as e:
        print(f"FAIL: {args.kind} {args.file_path}", file=sys.stderr)
        if args.pretty:
            print(f"\nValidation errors for {e.kind}:", file=sys.stderr)
            for err in e.errors:
                path = err.get("path", "/")
                message = err.get("message", "Unknown error")
                print(f"  • {path}: {message}", file=sys.stderr)
        else:
            print(str(e), file=sys.stderr)
        return 1

    except Exception as e:
        print(f"FAIL: {args.kind} {args.file_path}", file=sys.stderr)
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
