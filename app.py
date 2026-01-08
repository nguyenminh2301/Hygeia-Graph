"""Hygeia Graph - Streamlit Application."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from hygeia_graph.contracts import ContractValidationError, validate_schema_json
from hygeia_graph.data_processor import build_schema_json, infer_variables, load_csv, profile_df

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
    st.set_page_config(page_title="Hygeia-Graph", layout="wide")

    st.title("Hygeia-Graph")
    st.markdown("Graph-based analysis tool for healthcare contracts")

    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Home", "Data Upload & Schema Builder"],
        index=0,
    )

    if page == "Home":
        show_home_page()
    elif page == "Data Upload & Schema Builder":
        show_data_page()


def show_home_page():
    """Display home page with contract validation."""
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


def show_data_page():
    """Display data upload and schema builder page."""
    st.header("Data Upload & Schema Builder")

    # Initialize session state
    if "df" not in st.session_state:
        st.session_state.df = None
    if "variables" not in st.session_state:
        st.session_state.variables = None
    if "schema_obj" not in st.session_state:
        st.session_state.schema_obj = None
    if "schema_valid" not in st.session_state:
        st.session_state.schema_valid = False

    # Section 1: CSV Upload
    st.subheader("1. Upload CSV File")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            df = load_csv(uploaded_file)
            st.session_state.df = df
            st.success(f"✅ Loaded {len(df)} rows and {len(df.columns)} columns")

            # Show preview
            with st.expander("📊 Data Preview", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)

        except ValueError as e:
            st.error(f"❌ Error loading CSV: {e}")
            return

    # If no data loaded, stop here
    if st.session_state.df is None:
        st.info("👆 Please upload a CSV file to continue")
        return

    df = st.session_state.df

    # Section 2: Data Profiling
    st.subheader("2. Data Profiling")
    profile = profile_df(df)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rows", profile["row_count"])
    with col2:
        st.metric("Columns", profile["column_count"])
    with col3:
        st.metric("Missing Rate", f"{profile['missing']['rate']:.1%}")

    # Missing data warning
    if profile["missing"]["rate"] > 0:
        st.warning(
            f"⚠️ **Missing Data Detected ({profile['missing']['cells']} cells, "
            f"{profile['missing']['rate']:.1%})**\n\n"
            "Hygeia-Graph does not impute missing values. "
            "Please preprocess your data (e.g., using MICE) before modeling."
        )

        with st.expander("Missing Data by Variable"):
            missing_df = pd.DataFrame(profile["missing"]["by_variable"])
            missing_df = missing_df[missing_df["cells"] > 0]  # Only show variables with missing
            if len(missing_df) > 0:
                missing_df["rate"] = missing_df["rate"].apply(lambda x: f"{x:.1%}")
                st.dataframe(missing_df, use_container_width=True)

    # Section 3: Type Inference & Manual Override
    st.subheader("3. Variable Configuration")

    # Auto-infer if not already done
    if st.session_state.variables is None:
        with st.spinner("Inferring variable types..."):
            st.session_state.variables = infer_variables(df)

    # Convert to DataFrame for editing
    var_df = pd.DataFrame(st.session_state.variables)

    # Select columns to display in editor
    edit_columns = ["id", "column", "mgm_type", "measurement_level", "level", "label"]
    display_df = var_df[edit_columns].copy()

    st.info(
        "💡 **Tip**: Review the auto-inferred types below. "
        "You can edit `mgm_type`, `measurement_level`, `level`, and `label` as needed."
    )

    # Editable table
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "id": st.column_config.TextColumn("Variable ID", disabled=True),
            "column": st.column_config.TextColumn("Column Name", disabled=True),
            "mgm_type": st.column_config.SelectboxColumn(
                "MGM Type",
                options=["g", "c", "p"],
                help="g=Gaussian, c=Categorical, p=Poisson",
                required=True,
            ),
            "measurement_level": st.column_config.SelectboxColumn(
                "Measurement Level",
                options=["continuous", "nominal", "ordinal", "count"],
                required=True,
            ),
            "level": st.column_config.NumberColumn("Level", min_value=1, required=True),
            "label": st.column_config.TextColumn("Label"),
        },
        hide_index=True,
    )

    # Update variables with edits
    for i, row in edited_df.iterrows():
        st.session_state.variables[i]["mgm_type"] = row["mgm_type"]
        st.session_state.variables[i]["measurement_level"] = row["measurement_level"]
        st.session_state.variables[i]["level"] = int(row["level"])
        st.session_state.variables[i]["label"] = row["label"]

    # Section 4: Schema Validation & Export
    st.subheader("4. Generate & Export Schema")

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("🔍 Validate Schema", type="primary", use_container_width=True):
            with st.spinner("Validating schema..."):
                try:
                    # Build schema
                    schema_obj = build_schema_json(df, st.session_state.variables)
                    st.session_state.schema_obj = schema_obj

                    # Validate
                    validate_schema_json(schema_obj)
                    st.session_state.schema_valid = True
                    st.success("✅ Schema is valid!")

                except ContractValidationError as e:
                    st.session_state.schema_valid = False
                    st.error("❌ Schema validation failed:")
                    for err in e.errors:
                        st.error(f"  • {err['path']}: {err['message']}")

                except Exception as e:
                    st.session_state.schema_valid = False
                    st.error(f"❌ Unexpected error: {e}")

    with col_b:
        if st.session_state.schema_valid and st.session_state.schema_obj:
            schema_json = json.dumps(st.session_state.schema_obj, indent=2)
            st.download_button(
                label="📥 Download schema.json",
                data=schema_json,
                file_name="schema.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.button(
                "📥 Download schema.json",
                disabled=True,
                use_container_width=True,
                help="Validate schema first",
            )

    # Show schema preview
    if st.session_state.schema_obj:
        with st.expander("📄 Schema Preview (JSON)"):
            st.json(st.session_state.schema_obj)


if __name__ == "__main__":
    main()
