"""Hygeia Graph - Streamlit Application."""

from pathlib import Path

import streamlit as st

# Get repository root
REPO_ROOT = Path(__file__).resolve().parent
CONTRACTS_DIR = REPO_ROOT / "contracts"

# Expected contract schema files
EXPECTED_CONTRACTS = [
    "schema.json",
    "model_spec.json",
    "results.json",
]


def check_contracts():
    """Check if all expected contract schema files exist."""
    missing = []
    found = []

    for contract_file in EXPECTED_CONTRACTS:
        contract_path = CONTRACTS_DIR / contract_file
        if contract_path.exists():
            found.append(contract_file)
        else:
            missing.append(contract_file)

    return found, missing


def main():
    """Main Streamlit application."""
    st.title("Hygeia-Graph")
    st.markdown("Graph-based analysis tool for healthcare contracts")

    st.divider()

    # Contract validation section
    st.header("Contract Schema Validation")

    found, missing = check_contracts()

    if not missing:
        st.success("✅ All contract schemas found!")
        st.write("**Found schemas:**")
        for contract in found:
            st.write(f"- {contract}")
    else:
        st.error("❌ Missing contract schemas!")
        st.write("**Missing:**")
        for contract in missing:
            st.write(f"- {contract}")
        if found:
            st.write("**Found:**")
            for contract in found:
                st.write(f"- {contract}")


if __name__ == "__main__":
    main()
