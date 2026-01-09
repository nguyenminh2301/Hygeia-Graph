"""Hygeia Graph - Streamlit Application."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from hygeia_graph.contracts import (
    ContractValidationError,
    validate_model_spec_json,
    validate_schema_json,
)
from hygeia_graph.data_processor import build_schema_json, infer_variables, load_csv, profile_df
from hygeia_graph.i18n import LANGUAGES, t
from hygeia_graph.model_spec import build_model_spec, default_model_settings, sanitize_settings
from hygeia_graph.network_metrics import (
    build_graph_from_results,
    compute_centrality_table,
    edges_to_dataframe,
    filter_edges_by_threshold,
    make_nodes_meta,
)
from hygeia_graph.r_interface import RBackendError, run_mgm_subprocess
from hygeia_graph.visualizer import (
    build_pyvis_network,
    network_to_html,
    prepare_legend_html,
)

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

    # Initialize language in session state
    if "lang" not in st.session_state:
        st.session_state.lang = "en"

    # Language selector in sidebar
    lang_options = list(LANGUAGES.keys())
    current_idx = lang_options.index(st.session_state.lang)

    selected_lang = st.sidebar.selectbox(
        "🌐 Language / Ngôn ngữ",
        options=lang_options,
        format_func=lambda x: LANGUAGES[x],
        index=current_idx,
        key="lang_select",
    )
    st.session_state.lang = selected_lang
    lang = st.session_state.lang

    st.title(t("app_title", lang))
    st.markdown(t("app_description", lang))

    # Sidebar navigation
    nav_options = ["home", "data_upload"]
    nav_labels = [t("nav_home", lang), t("nav_data_upload", lang)]

    page_idx = st.sidebar.radio(
        t("nav_navigation", lang),
        range(len(nav_options)),
        format_func=lambda i: nav_labels[i],
        index=0,
    )
    page = nav_options[page_idx]

    if page == "home":
        show_home_page(lang)
    elif page == "data_upload":
        show_data_page(lang)


def show_home_page(lang: str = "en"):
    """Display home page with project info and contract validation."""
    # About section
    st.header(t("home_about", lang))
    st.markdown(t("home_description", lang))

    # Key Features
    st.header(t("home_features", lang))
    st.markdown(t("feature_mixed_types", lang))
    st.markdown(t("feature_ebic", lang))
    st.markdown(t("feature_visualization", lang))
    st.markdown(t("feature_centrality", lang))
    st.markdown(t("feature_reproducible", lang))
    st.markdown(t("feature_validation", lang))

    # Quick Start
    st.header(t("home_quickstart", lang))
    st.markdown(t("quickstart_steps", lang))

    # Methods
    with st.expander(t("home_methods", lang), expanded=False):
        st.markdown(t("methods_description", lang))

    # Disclaimer
    with st.expander(t("home_disclaimer", lang), expanded=False):
        st.warning(t("disclaimer_text", lang))

    # Contract validation
    st.header(t("contract_validation", lang))
    found, missing = check_contracts()

    if not missing:
        st.success(t("contracts_found", lang))
        st.write(f"**{t('found_schemas', lang)}**")
        for contract in found:
            st.write(f"- {contract}")
    else:
        st.error(t("contracts_missing", lang))
        st.write(f"**{t('missing_schemas', lang)}**")
        for contract in missing:
            st.write(f"- {contract}")
        if found:
            st.write(f"**{t('found_schemas', lang)}**")
            for contract in found:
                st.write(f"- {contract}")


def show_data_page(lang: str = "en"):
    """Display data upload and schema builder page."""
    st.header(t("nav_data_upload", lang))

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
    if "results_json" not in st.session_state:
        st.session_state.results_json = None
    if "r_process_info" not in st.session_state:
        st.session_state.r_process_info = None
    if "missing_rate" not in st.session_state:
        st.session_state.missing_rate = 0.0

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

    # Store missing rate for Run MGM checks
    st.session_state.missing_rate = profile["missing"]["rate"]

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

    # Section 7: Run MGM (R backend)
    st.divider()
    st.subheader("7. Run MGM (R Backend)")

    # Pre-run checks
    with st.expander("✅ Pre-run Checklist", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            # Check data loaded
            data_loaded = st.session_state.df is not None
            if data_loaded:
                st.success("✅ Data loaded")
            else:
                st.error("❌ Data not loaded")

            # Check schema valid
            schema_valid = st.session_state.schema_valid and st.session_state.schema_obj
            if schema_valid:
                st.success("✅ schema.json valid")
            else:
                st.error("❌ schema.json not valid")

        with col2:
            # Check model spec valid
            spec_valid = st.session_state.model_spec_valid and st.session_state.model_spec_obj
            if spec_valid:
                st.success("✅ model_spec.json valid")
            else:
                st.error("❌ model_spec.json not valid")

            # Check missing rate
            missing_ok = st.session_state.missing_rate == 0
            if missing_ok:
                st.success("✅ Missing rate = 0%")
            else:
                st.error(f"❌ Missing rate = {st.session_state.missing_rate:.1%}")

    # Block run if missing data
    can_run = data_loaded and schema_valid and spec_valid
    if not missing_ok:
        st.error(
            "⛔ **Cannot run MGM**: Missing values detected. "
            "Hygeia-Graph does not impute; please preprocess externally (e.g., MICE) and re-run."
        )
        can_run = False

    # Run controls
    with st.expander("⚙️ Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            timeout_sec = st.number_input(
                "Timeout (seconds)",
                min_value=60,
                max_value=3600,
                value=600,
                step=60,
                help="Maximum time to wait for R process",
            )
        with col2:
            debug_mode = st.checkbox(
                "Debug mode",
                value=False,
                help="Include raw parameter blocks in output",
            )
        show_output = st.checkbox(
            "Show stdout/stderr on error",
            value=True,
            help="Display R process output if execution fails",
        )

    # Run button
    col_run, col_status = st.columns([1, 2])

    with col_run:
        run_clicked = st.button(
            "🚀 Run MGM (EBIC)",
            type="primary",
            disabled=not can_run,
            use_container_width=True,
        )

    if run_clicked and can_run:
        with st.status("Running MGM analysis...", expanded=True) as status:
            try:
                st.write("📦 Preparing input artifacts...")
                st.write("🔧 Starting R subprocess...")

                result = run_mgm_subprocess(
                    df=st.session_state.df,
                    schema_json=st.session_state.schema_obj,
                    model_spec_json=st.session_state.model_spec_obj,
                    timeout_sec=int(timeout_sec),
                    quiet=True,
                    debug=debug_mode,
                )

                st.session_state.results_json = result["results"]
                st.session_state.r_process_info = result["process"]

                # Check status
                if result["results"]["status"] == "success":
                    n_edges = len(result["results"].get("edges", []))
                    status.update(
                        label=f"✅ MGM completed successfully ({n_edges} edges)",
                        state="complete",
                    )
                    st.success(f"MGM analysis completed! Found {n_edges} edges.")
                else:
                    status.update(label="⚠️ MGM completed with status: failed", state="error")
                    st.warning("MGM completed but status is 'failed'. Check messages below.")

            except RBackendError as e:
                st.session_state.results_json = None
                st.session_state.r_process_info = None
                status.update(label="❌ MGM execution failed", state="error")
                st.error(f"❌ R backend error: {e.message}")

                if show_output:
                    if e.stdout:
                        with st.expander("📄 R stdout"):
                            st.code(e.stdout, language="text")
                    if e.stderr:
                        with st.expander("📄 R stderr"):
                            st.code(e.stderr, language="text")

            except Exception as e:
                st.session_state.results_json = None
                st.session_state.r_process_info = None
                status.update(label="❌ Unexpected error", state="error")
                st.error(f"❌ Unexpected error: {e}")

    # Results viewer
    if st.session_state.results_json:
        st.divider()
        st.subheader("📊 Results")

        results = st.session_state.results_json

        # Status and summary
        col1, col2, col3 = st.columns(3)
        with col1:
            status_val = results.get("status", "unknown")
            if status_val == "success":
                st.metric("Status", "✅ Success")
            else:
                st.metric("Status", "❌ Failed")
        with col2:
            st.metric("Nodes", len(results.get("nodes", [])))
        with col3:
            st.metric("Edges", len(results.get("edges", [])))

        # Engine info
        engine = results.get("engine", {})
        if engine:
            with st.expander("🔧 Engine Info"):
                st.write(f"**Engine**: {engine.get('name', 'unknown')}")
                st.write(f"**R Version**: {engine.get('r_version', 'unknown')}")
                pkg_versions = engine.get("package_versions", {})
                if pkg_versions:
                    st.write("**Package Versions**:")
                    for pkg, ver in pkg_versions.items():
                        st.write(f"  - {pkg}: {ver}")

        # Messages
        messages = results.get("messages", [])
        if messages:
            with st.expander(f"📝 Messages ({len(messages)})"):
                msg_df = pd.DataFrame(messages)
                if not msg_df.empty:
                    st.dataframe(
                        msg_df[["level", "code", "message"]],
                        use_container_width=True,
                        hide_index=True,
                    )

        # Download button
        col_dl, _ = st.columns([1, 2])
        with col_dl:
            results_str = json.dumps(results, indent=2, sort_keys=True)
            st.download_button(
                label="📥 Download results.json",
                data=results_str,
                file_name="results.json",
                mime="application/json",
                use_container_width=True,
            )

        # Raw JSON
        with st.expander("📄 Raw JSON"):
            st.json(results)

    # Section 8: Network Tables & Centrality
    st.divider()
    st.subheader("8. Network Tables & Centrality")

    # Check if we have valid results
    if not st.session_state.results_json:
        st.info("⬆️ Run MGM first to see network tables")
        return

    results = st.session_state.results_json
    if results.get("status") != "success":
        st.warning("⚠️ Model run failed; network tables are unavailable.")
        return

    edges = results.get("edges", [])
    nodes = results.get("nodes", [])

    if not edges:
        st.info("No edges found in results. Network tables are empty.")
        return

    # Compute max weight for slider
    max_abs_weight = max(abs(e.get("weight", 0)) for e in edges) if edges else 0

    # Controls
    with st.expander("⚙️ Table Controls", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            use_absolute = st.checkbox(
                "Use absolute edge weights",
                value=True,
                help="Use |weight| for filtering and centrality",
            )

            # Edge threshold slider
            step_val = max(0.01, max_abs_weight / 100) if max_abs_weight > 0 else 0.01
            threshold = st.slider(
                "Edge threshold",
                min_value=0.0,
                max_value=float(max_abs_weight) if max_abs_weight > 0 else 1.0,
                value=0.0,
                step=step_val,
                help="Minimum weight to include edges",
            )

        with col2:
            compute_betweenness = st.checkbox(
                "Compute betweenness centrality",
                value=True,
                help="Betweenness centrality (may be slow for large networks)",
            )

            compute_closeness = st.checkbox(
                "Compute closeness centrality",
                value=False,
                help="Closeness centrality (requires weight-to-distance conversion)",
            )

            max_rows = st.number_input(
                "Max rows to display",
                min_value=10,
                max_value=1000,
                value=200,
                step=50,
                help="Limit table display for performance",
            )

    # Filter edges
    filtered_edges = filter_edges_by_threshold(
        results, threshold, use_absolute_weights=use_absolute
    )

    # Summary metrics
    st.write("### 📊 Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Nodes", len(nodes))
    with col2:
        st.metric("Total Edges", len(edges))
    with col3:
        st.metric("Filtered Edges", len(filtered_edges))
    with col4:
        n = len(nodes)
        density = 2 * len(filtered_edges) / (n * (n - 1)) if n > 1 else 0
        st.metric("Density", f"{density:.3f}")

    # Edge table
    st.write("### 🔗 Edge Table")

    if len(filtered_edges) > 5000:
        st.warning(f"⚠️ Large number of edges ({len(filtered_edges)}). Showing top {max_rows}.")

    nodes_meta = make_nodes_meta(results)
    edges_df = edges_to_dataframe(filtered_edges[: int(max_rows)], nodes_meta)

    if not edges_df.empty:
        st.dataframe(
            edges_df,
            use_container_width=True,
            hide_index=True,
        )

        # Download button for full filtered edges
        full_edges_df = edges_to_dataframe(filtered_edges, nodes_meta)
        csv_edges = full_edges_df.to_csv(index=False)
        st.download_button(
            label=f"📥 Download edges_filtered.csv ({len(filtered_edges)} edges)",
            data=csv_edges,
            file_name="edges_filtered.csv",
            mime="text/csv",
        )
    else:
        st.info("No edges meet the threshold criteria.")

    # Centrality table
    st.write("### 📈 Centrality Table")

    # Build graph with current settings
    G = build_graph_from_results(results, use_absolute_weights=use_absolute)

    # Compute centrality
    centrality_df = compute_centrality_table(
        G,
        compute_betweenness=compute_betweenness,
        compute_closeness=compute_closeness,
    )

    if not centrality_df.empty:
        # Show top rows
        display_df = centrality_df.head(int(max_rows))

        # Format for display
        format_cols = ["strength"]
        if compute_betweenness:
            format_cols.append("betweenness")
        if compute_closeness:
            format_cols.append("closeness")

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

        # Download button
        csv_centrality = centrality_df.to_csv(index=False)
        st.download_button(
            label=f"📥 Download centrality.csv ({len(centrality_df)} nodes)",
            data=csv_centrality,
            file_name="centrality.csv",
            mime="text/csv",
        )
    else:
        st.info("No nodes to compute centrality.")

    # Section 9: Interactive Network (PyVis)
    st.divider()
    st.subheader("9. Interactive Network (PyVis)")

    # Check if we have valid results
    if not st.session_state.results_json:
        st.info("⬆️ Run MGM first to see the network visualization")
        return

    results = st.session_state.results_json
    if results.get("status") != "success":
        st.warning("⚠️ Model run failed; network visualization is unavailable.")
        return

    edges = results.get("edges", [])
    nodes = results.get("nodes", [])

    if not edges:
        st.info("No edges found in results. Network visualization is empty.")
        return

    # Compute max weight for slider
    max_abs_weight = max(abs(e.get("weight", 0)) for e in edges) if edges else 0

    # Visualization controls
    with st.expander("⚙️ Visualization Controls", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            viz_use_absolute = st.checkbox(
                "Use absolute edge weights (visualization)",
                value=True,
                key="viz_abs_weights",
                help="Use |weight| for edge thickness",
            )

            # Edge threshold slider
            viz_step = max(0.01, max_abs_weight / 100) if max_abs_weight > 0 else 0.01
            viz_threshold = st.slider(
                "Edge threshold (visualization)",
                min_value=0.0,
                max_value=float(max_abs_weight) if max_abs_weight > 0 else 1.0,
                value=0.0,
                step=viz_step,
                key="viz_threshold",
                help="Minimum weight to display edges",
            )

        with col2:
            show_labels = st.checkbox(
                "Show node labels",
                value=True,
                help="Display node labels on the graph",
            )

            physics_enabled = st.checkbox(
                "Enable physics simulation",
                value=True,
                help="Allow nodes to move and settle",
            )

            max_edges_viz = st.number_input(
                "Max edges to display",
                min_value=10,
                max_value=5000,
                value=1000,
                step=100,
                help="Limit edges for browser performance",
            )

    # Filter edges for visualization
    viz_filtered_edges = filter_edges_by_threshold(
        results, viz_threshold, use_absolute_weights=viz_use_absolute
    )

    # Limit edges if too many
    if len(viz_filtered_edges) > max_edges_viz:
        st.warning(
            f"⚠️ {len(viz_filtered_edges)} edges exceed limit. "
            f"Showing top {max_edges_viz} by |weight|."
        )
        viz_filtered_edges = viz_filtered_edges[: int(max_edges_viz)]

    # Performance warning
    if len(nodes) > 500 or len(viz_filtered_edges) > 5000:
        st.warning(
            "⚠️ Large network detected. Consider increasing the threshold "
            "for better browser performance."
        )

    # Show counts
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Nodes Displayed", len(nodes))
    with col2:
        st.metric("Edges Displayed", len(viz_filtered_edges))

    # Build graph from filtered edges
    if viz_filtered_edges:
        # Create a results dict with only filtered edges for graph building
        filtered_results = {
            "nodes": results["nodes"],
            "edges": viz_filtered_edges,
        }
        G_viz = build_graph_from_results(filtered_results, use_absolute_weights=viz_use_absolute)

        # Build PyVis network
        nodes_meta = make_nodes_meta(results)
        net = build_pyvis_network(
            G_viz,
            nodes_meta=nodes_meta,
            height="650px",
            width="100%",
            show_labels=show_labels,
            physics=physics_enabled,
        )

        # Generate HTML
        html = network_to_html(net)

        # Show legend
        with st.expander("📖 Legend"):
            st.markdown(prepare_legend_html(), unsafe_allow_html=True)

        # Render network
        components.html(html, height=700, scrolling=True)

        # Export options
        st.write("### 📥 Exports")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.download_button(
                label="Download network.html",
                data=html,
                file_name="network.html",
                mime="text/html",
            )

        with col2:
            # Edges CSV
            nodes_meta_full = make_nodes_meta(results)
            edges_df_export = edges_to_dataframe(viz_filtered_edges, nodes_meta_full)
            csv_edges = edges_df_export.to_csv(index=False)
            st.download_button(
                label="Download edges.csv",
                data=csv_edges,
                file_name="edges_filtered.csv",
                mime="text/csv",
            )

        with col3:
            # Results JSON
            results_str = json.dumps(results, indent=2, sort_keys=True)
            st.download_button(
                label="Download results.json",
                data=results_str,
                file_name="results.json",
                mime="application/json",
            )
    else:
        st.info("No edges above threshold to display.")


if __name__ == "__main__":
    main()
