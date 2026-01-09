"""Hygeia Graph - Streamlit Application."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from hygeia_graph.contracts import (
    ContractValidationError,
    validate_model_spec_json,
    validate_schema_json,
)
from hygeia_graph.data_processor import build_schema_json, infer_variables, load_csv, profile_df
from hygeia_graph.model_spec import build_model_spec, default_model_settings, sanitize_settings

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
    if "model_settings" not in st.session_state:
        st.session_state.model_settings = default_model_settings()
    if "model_spec_obj" not in st.session_state:
        st.session_state.model_spec_obj = None
    if "model_spec_valid" not in st.session_state:
        st.session_state.model_spec_valid = False

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

    # Section 5: Model Settings (EBIC)
    st.divider()
    st.subheader("5. Model Settings (EBIC Regularization)")

    # Only show if schema is available
    if not st.session_state.schema_valid or not st.session_state.schema_obj:
        st.info("⬆️ Please upload data and generate a valid schema first")
        return

    # EBIC / Regularization Section
    with st.expander("⚙️ EBIC & Regularization Parameters", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            ebic_gamma = st.slider(
                "EBIC Gamma",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.model_settings["mgm"]["regularization"]["ebic_gamma"],
                step=0.05,
                help="EBIC hyperparameter for model selection (0=BIC, 0.5=default, 1=more penalty)",
            )

            alpha = st.slider(
                "Alpha (Elastic Net)",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.model_settings["mgm"]["regularization"]["alpha"],
                step=0.05,
                help="Elastic net mixing (0=Ridge, 0.5=default, 1=Lasso)",
            )

            rule_reg = st.selectbox(
                "Rule Regularization",
                options=["AND", "OR"],
                index=0 if st.session_state.model_settings["mgm"]["rule_reg"] == "AND" else 1,
                help="Regularization rule for pairwise interactions",
            )

        with col2:
            overparameterize = st.checkbox(
                "Overparameterize",
                value=st.session_state.model_settings["mgm"]["overparameterize"],
                help="Use overparameterized model",
            )

            scale_gaussian = st.checkbox(
                "Scale Gaussian",
                value=st.session_state.model_settings["mgm"]["scale_gaussian"],
                help="Standardize Gaussian variables",
            )

            sign_info = st.checkbox(
                "Sign Info",
                value=st.session_state.model_settings["mgm"]["sign_info"],
                help="Include sign information in edge weights",
            )

            random_seed = st.number_input(
                "Random Seed",
                min_value=0,
                value=st.session_state.model_settings["random_seed"],
                step=1,
                help="Random seed for reproducibility",
            )

        # Update settings
        st.session_state.model_settings["mgm"]["regularization"]["ebic_gamma"] = ebic_gamma
        st.session_state.model_settings["mgm"]["regularization"]["alpha"] = alpha
        st.session_state.model_settings["mgm"]["rule_reg"] = rule_reg
        st.session_state.model_settings["mgm"]["overparameterize"] = overparameterize
        st.session_state.model_settings["mgm"]["scale_gaussian"] = scale_gaussian
        st.session_state.model_settings["mgm"]["sign_info"] = sign_info
        st.session_state.model_settings["random_seed"] = int(random_seed)

    # Edge Mapping Section
    with st.expander("🔗 Edge Mapping Configuration"):
        col1, col2, col3 = st.columns(3)

        with col1:
            aggregator = st.selectbox(
                "Aggregator",
                options=["max_abs", "l2_norm", "mean", "mean_abs", "sum_abs", "max"],
                index=["max_abs", "l2_norm", "mean", "mean_abs", "sum_abs", "max"].index(
                    st.session_state.model_settings["edge_mapping"]["aggregator"]
                ),
                help="Method for aggregating pairwise parameters to single edge weight",
            )

        with col2:
            sign_strategy = st.selectbox(
                "Sign Strategy",
                options=["dominant", "mean", "none"],
                index=["dominant", "mean", "none"].index(
                    st.session_state.model_settings["edge_mapping"]["sign_strategy"]
                ),
                help="Strategy for determining edge sign",
            )

        with col3:
            zero_tolerance = st.number_input(
                "Zero Tolerance",
                min_value=0.0,
                value=st.session_state.model_settings["edge_mapping"]["zero_tolerance"],
                format="%.2e",
                help="Threshold for treating values as zero",
            )

        # Update settings
        st.session_state.model_settings["edge_mapping"]["aggregator"] = aggregator
        st.session_state.model_settings["edge_mapping"]["sign_strategy"] = sign_strategy
        st.session_state.model_settings["edge_mapping"]["zero_tolerance"] = float(zero_tolerance)

    # Visualization & Centrality (Optional)
    with st.expander("📊 Visualization & Centrality (Optional)"):
        col1, col2 = st.columns(2)

        with col1:
            edge_threshold = st.number_input(
                "Edge Threshold",
                min_value=0.0,
                value=st.session_state.model_settings["visualization"]["edge_threshold"],
                step=0.01,
                help="Minimum edge weight to display",
            )

            layout = st.selectbox(
                "Layout Algorithm",
                options=["force", "circle", "random"],
                index=["force", "circle", "random"].index(
                    st.session_state.model_settings["visualization"]["layout"]
                ),
                help="Graph layout algorithm",
            )

        with col2:
            compute_centrality = st.checkbox(
                "Compute Centrality",
                value=st.session_state.model_settings["centrality"]["compute"],
                help="Calculate centrality metrics",
            )

            weighted = st.checkbox(
                "Weighted Centrality",
                value=st.session_state.model_settings["centrality"]["weighted"],
                help="Use edge weights in centrality calculation",
            )

            use_absolute = st.checkbox(
                "Use Absolute Weights",
                value=st.session_state.model_settings["centrality"]["use_absolute_weights"],
                help="Use absolute values of edge weights",
            )

        # Update settings
        st.session_state.model_settings["visualization"]["edge_threshold"] = float(edge_threshold)
        st.session_state.model_settings["visualization"]["layout"] = layout
        st.session_state.model_settings["centrality"]["compute"] = compute_centrality
        st.session_state.model_settings["centrality"]["weighted"] = weighted
        st.session_state.model_settings["centrality"]["use_absolute_weights"] = use_absolute

    # Build & Export Model Spec
    st.subheader("6. Build & Export Model Specification")

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button(
            "🔍 Build & Validate model_spec.json", type="primary", use_container_width=True
        ):
            with st.spinner("Building and validating model spec..."):
                try:
                    # Sanitize settings
                    clean_settings = sanitize_settings(st.session_state.model_settings)

                    # Build model spec
                    model_spec = build_model_spec(st.session_state.schema_obj, clean_settings)
                    st.session_state.model_spec_obj = model_spec

                    # Validate
                    validate_model_spec_json(model_spec)
                    st.session_state.model_spec_valid = True
                    st.success("✅ Model spec is valid!")

                    # Show locked fields info
                    st.info(
                        "🔒 **Locked settings enforced:**\n"
                        "- Lambda selection: EBIC\n"
                        "- Missing policy: warn_and_abort"
                    )

                except ContractValidationError as e:
                    st.session_state.model_spec_valid = False
                    st.error("❌ Model spec validation failed:")
                    for err in e.errors:
                        st.error(f"  • {err['path']}: {err['message']}")

                except Exception as e:
                    st.session_state.model_spec_valid = False
                    st.error(f"❌ Unexpected error: {e}")

    with col_b:
        if st.session_state.model_spec_valid and st.session_state.model_spec_obj:
            model_spec_json = json.dumps(st.session_state.model_spec_obj, indent=2, sort_keys=True)
            st.download_button(
                label="📥 Download model_spec.json",
                data=model_spec_json,
                file_name="model_spec.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.button(
                "📥 Download model_spec.json",
                disabled=True,
                use_container_width=True,
                help="Build & validate model spec first",
            )

    # Show model spec preview
    if st.session_state.model_spec_obj:
        with st.expander("📄 Model Spec Preview (JSON)"):
            st.json(st.session_state.model_spec_obj)


if __name__ == "__main__":
    main()
