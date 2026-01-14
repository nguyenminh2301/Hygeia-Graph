import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from hygeia_graph.contracts import (
    ContractValidationError,
    validate_model_spec_json,
    validate_schema_json,
)
from hygeia_graph.data_processor import build_schema_json, infer_variables, profile_df
from hygeia_graph.locale import t
from hygeia_graph.model_spec import build_model_spec, default_model_settings, sanitize_settings
from hygeia_graph.network_metrics import (
    build_graph_from_results,
    make_nodes_meta,
)
from hygeia_graph.plots import (
    build_node_metrics_df,
    compute_edges_filtered_df,
)
from hygeia_graph.posthoc_merge import merge_r_posthoc_into_derived
from hygeia_graph.posthoc_metrics import build_derived_metrics
from hygeia_graph.r_interface import RBackendError, run_mgm_subprocess
from hygeia_graph.ui_state import (
    can_enable_communities,
    can_enable_predictability,
    get_cached_outputs,
    get_community_counts,
    map_community_to_colors,
)
from hygeia_graph.visualizer import (
    build_pyvis_network,
    network_to_html,
    prepare_legend_html,
)
from hygeia_graph.temporal_interface import run_temporal_var_subprocess


def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "df": None,
        "variables": None,
        "schema_obj": None,
        "schema_valid": False,
        "model_settings": default_model_settings(),
        "model_spec_obj": None,
        "model_spec_valid": False,
        "results_json": None,
        "r_process_info": None,
        "missing_rate": 0.0,
        "lang": "en",
        "analysis_id": None,
        "config_hash": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def render_introduction_page(lang: str):
    """Render Introduction page."""
    st.title(t("intro_title", lang))
    st.markdown(f"#### {t('intro_subtitle', lang)}")
    st.markdown(t("intro_description", lang))

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader(t("core_features", lang))
        st.markdown(f"- {t('feat_mgm', lang)}")
        st.markdown(f"- {t('feat_temporal', lang)}")
        st.markdown(f"- {t('feat_flow', lang)}")

    with c2:
        st.subheader(t("advanced_features", lang))
        st.markdown(f"- {t('feat_lasso', lang)}")
        st.markdown(f"- {t('feat_robustness', lang)}")
        st.markdown(f"- {t('feat_comparison', lang)}")

    st.divider()
    st.subheader(t("start_guide", lang))
    st.info(f"👉 **{t('step_1_title', lang)}**: {t('step_1_desc', lang)}")
    st.markdown(f"**{t('step_2_title', lang)}**: {t('step_2_desc', lang)}")
    st.markdown(f"**{t('step_3_title', lang)}**: {t('step_3_desc', lang)}")
    st.markdown(f"**{t('step_4_title', lang)}**: {t('step_4_desc', lang)}")

    st.divider()
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➡️ Start: Data & Schema", type="primary", use_container_width=True):
            st.session_state["nav_selection"] = "Data & Schema"
            st.rerun()


def render_data_schema_page(lang: str):
    """Render Data & Schema page (Steps 1-4)."""
    st.header(t("nav_data_upload", lang))

    # Data format guidance
    from hygeia_graph.example_datasets import (
        EXAMPLES,
        get_example_meta,
        load_example_df,
    )
    from hygeia_graph.file_loader import (
        SUPPORTED_FORMATS_DISPLAY,
        FileLoadError,
        convert_to_standard_format,
        get_supported_extensions,
        load_file,
    )
    from hygeia_graph.ui_guidance import DATA_FORMAT_DETAILS, DATA_FORMAT_SHORT

    st.markdown(DATA_FORMAT_SHORT)
    st.markdown(SUPPORTED_FORMATS_DISPLAY)
    with st.expander("📖 More details on data requirements"):
        st.markdown(DATA_FORMAT_DETAILS)

    # Section 1: Data Source Selection
    st.subheader("1. Load Data")

    data_source = st.radio(
        "Data source:",
        ["Upload file", "Use example dataset"],
        horizontal=True,
        key="data_source_radio",
    )

    if data_source == "Use example dataset":
        # Example selector
        example_options = {ex["key"]: ex["title"] for ex in EXAMPLES}
        selected_key = st.selectbox(
            "Choose example:",
            options=list(example_options.keys()),
            format_func=lambda k: example_options[k],
            key="example_selector",
        )

        meta = get_example_meta(selected_key)
        if meta:
            st.info(f"**Goal:** {meta['goal']}")
            for note in meta.get("notes", []):
                st.caption(f"• {note}")

            if st.button("📂 Load Example Dataset", type="primary", key="load_example_btn"):
                try:
                    df = load_example_df(selected_key)
                    st.session_state.df = df
                    st.session_state["uploaded_filename"] = meta["filename"]

                    # Apply recommended settings
                    if "explore_config" not in st.session_state:
                        st.session_state["explore_config"] = {}
                    rec = meta.get("recommended_settings", {})
                    st.session_state["explore_config"]["threshold"] = rec.get("threshold", 0.0)
                    st.session_state["explore_config"]["top_edges"] = rec.get("top_edges", 500)

                    # Clear downstream artifacts
                    for key in ["schema_obj", "schema_valid", "model_spec_obj", "results_json",
                                "derived_metrics_json", "r_posthoc_json", "derived_cache"]:
                        if key in st.session_state:
                            del st.session_state[key]

                    st.success(f"✅ Loaded **{meta['title']}**: {len(df)} rows × {len(df.columns)} columns")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load example: {e}")

    else:
        # File upload
        supported_ext = [ext.lstrip(".") for ext in get_supported_extensions()]
        uploaded_file = st.file_uploader(
            "Choose a data file (CSV, Excel, Stata, SPSS, SAS, TXT)",
            type=supported_ext,
        )

        if uploaded_file is not None:
            try:
                df, meta = load_file(uploaded_file, uploaded_file.name)
                df = convert_to_standard_format(df)
                st.session_state.df = df

                st.success(
                    f"✅ Loaded **{meta['detected_type'].upper()}** file: "
                    f"{meta['n_rows']} rows × {meta['n_cols']} columns"
                )
                with st.expander("📊 Data Preview", expanded=True):
                    st.dataframe(df.head(10), use_container_width=True)
            except FileLoadError as e:
                st.error(f"❌ {e.message}")
                if e.details:
                    st.caption(e.details)
                return
            except Exception as e:
                st.error(f"❌ Error loading file: {e}")
                return

    if st.session_state.df is None:
        st.info("👆 Please upload a data file or select an example to continue")
        return

    df = st.session_state.df

    # Section 2: Profiling
    st.subheader("2. Data Profiling")
    profile = profile_df(df)
    st.session_state.missing_rate = profile["missing"]["rate"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", profile["row_count"])
    col2.metric("Columns", profile["column_count"])
    col3.metric("Missing Rate", f"{profile['missing']['rate']:.1%}")

    if profile["missing"]["rate"] > 0:
        st.warning(
            f"⚠️ **Missing Data Detected ({profile['missing']['rate']:.1%})**\n\n"
            "Hygeia-Graph does not impute missing values. Please preprocess externally."
        )
        with st.expander("Missing Data by Variable"):
            missing_df = pd.DataFrame(profile["missing"]["by_variable"])
            missing_df = missing_df[missing_df["cells"] > 0]
            if len(missing_df) > 0:
                missing_df["rate"] = missing_df["rate"].apply(lambda x: f"{x:.1%}")
                st.dataframe(missing_df, use_container_width=True)

    # Section 3: Variable Config
    st.subheader("3. Variable Configuration")

    # MGM types explanation
    from hygeia_graph.ui_copy import MGM_TYPES_EXPLANATION
    st.markdown(MGM_TYPES_EXPLANATION)

    if st.session_state.variables is None:
        with st.spinner("Inferring variable types..."):
            st.session_state.variables = infer_variables(df)

    var_df = pd.DataFrame(st.session_state.variables)
    edit_columns = ["id", "column", "mgm_type", "measurement_level", "level", "label"]

    st.info("💡 Review auto-inferred types below.")
    edited_df = st.data_editor(
        var_df[edit_columns].copy(),
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "id": st.column_config.TextColumn("Variable ID", disabled=True),
            "column": st.column_config.TextColumn("Column Name", disabled=True),
            "mgm_type": st.column_config.SelectboxColumn(
                "MGM Type", options=["g", "c", "p"], required=True
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

    for i, row in edited_df.iterrows():
        st.session_state.variables[i].update(
            {
                "mgm_type": row["mgm_type"],
                "measurement_level": row["measurement_level"],
                "level": int(row["level"]),
                "label": row["label"],
            }
        )

    # Section 4: Schema
    st.subheader("4. Generate & Export Schema")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 Validate Schema", type="primary", use_container_width=True):
            try:
                schema_obj = build_schema_json(df, st.session_state.variables)
                st.session_state.schema_obj = schema_obj
                validate_schema_json(schema_obj)
                st.session_state.schema_valid = True
                st.success("✅ Schema is valid!")
            except ContractValidationError as e:
                st.session_state.schema_valid = False
                st.error("❌ Schema validation failed")
                for err in e.errors:
                    st.error(f"• {err['path']}: {err['message']}")
            except Exception as e:
                st.session_state.schema_valid = False
                st.error(f"❌ Error: {e}")

    with c2:
        if st.session_state.schema_valid and st.session_state.schema_obj:
            st.download_button(
                "📥 Download schema.json",
                data=json.dumps(st.session_state.schema_obj, indent=2),
                file_name="schema.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.button("📥 Download schema.json", disabled=True, use_container_width=True)

    # Schema status (no JSON preview)
    if st.session_state.schema_valid and st.session_state.schema_obj:
        from hygeia_graph.ui_copy import STATUS_SCHEMA_READY
        from hygeia_graph.ui_flow import get_schema_summary

        summary = get_schema_summary(st.session_state.schema_obj)
        st.success(f"{STATUS_SCHEMA_READY} ({summary})")

        # Analysis goal selector
        st.divider()
        goal = st.radio(
            "📊 Analysis goal:",
            ["explore", "robustness", "comparison", "publication"],
            format_func=lambda x: {
                "explore": "Explore network (default)",
                "robustness": "Robustness analysis (bootnet)",
                "comparison": "Compare groups (NCT)",
                "publication": "Publication-ready figures",
            }.get(x, x),
            horizontal=True,
            key="analysis_goal_radio",
        )
        st.session_state["analysis_goal"] = goal

        # Next Step button
        st.divider()
        st.success("✅ Schema ready! You can proceed to Model Settings.")
        if st.button("➡️ Next: Model Settings", type="primary", key="next_model_settings"):
            st.session_state["nav_selection"] = "Model Settings"
            st.rerun()


def render_model_settings_page(lang: str):
    """Render Model Settings page (Steps 4 continued)."""
    st.header(t("nav_navigation", lang))  # Using generic header as placeholder? Or "Model Settings"
    st.subheader("Model Settings (EBIC Regularization)")

    if not st.session_state.schema_valid:
        st.info("Please complete Data & Schema step first.")
        return

    # EBIC Settings
    with st.expander("⚙️ EBIC & Regularization Parameters", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            ebic_gamma = st.slider(
                "EBIC Gamma",
                0.0,
                1.0,
                st.session_state.model_settings["mgm"]["regularization"]["ebic_gamma"],
                0.05,
            )
            alpha = st.slider(
                "Alpha (Elastic Net)",
                0.0,
                1.0,
                st.session_state.model_settings["mgm"]["regularization"]["alpha"],
                0.05,
            )
            rule_reg = st.selectbox(
                "Rule Regularization",
                ["AND", "OR"],
                index=0 if st.session_state.model_settings["mgm"]["rule_reg"] == "AND" else 1,
            )
        with c2:
            overparam = st.checkbox(
                "Overparameterize", st.session_state.model_settings["mgm"]["overparameterize"]
            )
            scale_g = st.checkbox(
                "Scale Gaussian", st.session_state.model_settings["mgm"]["scale_gaussian"]
            )
            sign_info = st.checkbox(
                "Sign Info", st.session_state.model_settings["mgm"]["sign_info"]
            )
            seed = st.number_input(
                t("random_seed", lang), 0, value=st.session_state.model_settings["random_seed"]
            )

        # Update
        st.session_state.model_settings["mgm"]["regularization"].update(
            {"ebic_gamma": ebic_gamma, "alpha": alpha}
        )
        st.session_state.model_settings["mgm"].update(
            {
                "rule_reg": rule_reg,
                "overparameterize": overparam,
                "scale_gaussian": scale_g,
                "sign_info": sign_info,
            }
        )
        st.session_state.model_settings["random_seed"] = int(seed)

    # Edge Mapping
    with st.expander("🔗 Edge Mapping Configuration"):
        c1, c2, c3 = st.columns(3)
        with c1:
            agg = st.selectbox(
                "Aggregator",
                ["max_abs", "l2_norm", "mean", "mean_abs", "sum_abs", "max"],
                index=["max_abs", "l2_norm", "mean", "mean_abs", "sum_abs", "max"].index(
                    st.session_state.model_settings["edge_mapping"]["aggregator"]
                ),
            )
        with c2:
            strat = st.selectbox(
                "Sign Strategy",
                ["dominant", "mean", "none"],
                index=["dominant", "mean", "none"].index(
                    st.session_state.model_settings["edge_mapping"]["sign_strategy"]
                ),
            )
        with c3:
            zt = st.number_input(
                "Zero Tolerance",
                min_value=0.0,
                value=st.session_state.model_settings["edge_mapping"]["zero_tolerance"],
                format="%.2e",
            )

        st.session_state.model_settings["edge_mapping"].update(
            {"aggregator": agg, "sign_strategy": strat, "zero_tolerance": float(zt)}
        )

    # Build Spec
    st.subheader("Build & Export Model Specification")
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "🔍 Build & Validate model_spec.json", type="primary", use_container_width=True
        ):
            try:
                clean_settings = sanitize_settings(st.session_state.model_settings)
                model_spec = build_model_spec(st.session_state.schema_obj, clean_settings)
                st.session_state.model_spec_obj = model_spec
                validate_model_spec_json(model_spec)
                st.session_state.model_spec_valid = True
                st.success("✅ Model spec is valid!")
            except ContractValidationError as e:
                st.session_state.model_spec_valid = False
                st.error("❌ Validation failed")
                for err in e.errors:
                    st.error(f"• {err['path']}: {err['message']}")
            except Exception as e:
                st.session_state.model_spec_valid = False
                st.error(f"❌ Error: {e}")

    with c2:
        if st.session_state.model_spec_valid and st.session_state.model_spec_obj:
            st.download_button(
                "📥 Download model_spec.json",
                data=json.dumps(st.session_state.model_spec_obj, indent=2, sort_keys=True),
                file_name="model_spec.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.button("📥 Download model_spec.json", disabled=True, use_container_width=True)

    if st.session_state.model_spec_obj:
        with st.expander("📄 Model Spec Preview"):
            st.json(st.session_state.model_spec_obj)

    if st.session_state.model_spec_valid:
        st.divider()
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success("✅ Model specification ready! You can now run MGM analysis.")
        with col2:
            if st.button("➡️ Go to Run MGM", type="primary", use_container_width=True):
                st.session_state["nav_selection"] = "Run MGM"
                st.rerun()


def render_run_mgm_page(lang: str):
    """Render Run MGM page."""
    st.header("Run MGM Analysis")

    # Checklist
    with st.expander("✅ Pre-run Checklist", expanded=True):
        c1, c2 = st.columns(2)
        data_loaded = st.session_state.df is not None
        schema_valid = st.session_state.schema_valid and st.session_state.schema_obj
        spec_valid = st.session_state.model_spec_valid and st.session_state.model_spec_obj
        missing_ok = st.session_state.missing_rate == 0

        with c1:
            st.write(f"{'✅' if data_loaded else '❌'} Data loaded")
            st.write(f"{'✅' if schema_valid else '❌'} schema.json valid")
        with c2:
            st.write(f"{'✅' if spec_valid else '❌'} model_spec.json valid")
            st.write(
                f"{'✅' if missing_ok else '❌'} Missing rate = {st.session_state.missing_rate:.1%}"
            )

    can_run = data_loaded and schema_valid and spec_valid and missing_ok
    if not missing_ok:
        st.error("⛔ Cannot run MGM: Missing values detected.")

    # Options
    # Options
    with st.expander("⚙️ Advanced Options"):
        c1, c2 = st.columns(2)
        timeout = c1.number_input("Timeout (sec)", 60, 3600, 600, 60)
        debug = c2.checkbox("Debug mode")
        show_output = st.checkbox("Show stdout/stderr on error", True)

        st.divider()
        st.caption("R Posthoc Analysis (Requires local R environment)")
        compute_ph = st.checkbox("Compute R posthoc (Predictability + Communities)")

        comm_algo = "spinglass_neg"
        spins_val = None

        if compute_ph:
            c_a, c_b = st.columns(2)
            comm_algo = c_a.selectbox("Community Algorithm", ["spinglass_neg", "walktrap"], index=0)
            if comm_algo == "spinglass_neg":
                s_in = c_b.number_input("Spins (0 for auto)", min_value=0, value=0)
                spins_val = int(s_in) if s_in > 0 else None

            st.info(
                "ℹ️ Predictability uses R2 (Gaussian/Poisson) or nCC (Categorical). Communities computed via igraph."
            )

    # Run
    col_run, col_status = st.columns([1, 2])
    if col_run.button(
        "🚀 Run MGM (EBIC)", type="primary", disabled=not can_run, use_container_width=True
    ):
        with st.status("Running MGM analysis...", expanded=True) as status:
            try:
                res = run_mgm_subprocess(
                    df=st.session_state.df,
                    schema_json=st.session_state.schema_obj,
                    model_spec_json=st.session_state.model_spec_obj,
                    timeout_sec=int(timeout),
                    quiet=True,
                    debug=debug,
                    compute_r_posthoc=compute_ph,
                    community_algo=comm_algo,
                    spins=spins_val,
                )
                st.session_state.results_json = res["results"]
                st.session_state.r_process_info = res["process"]
                # Store optional r_posthoc
                st.session_state.r_posthoc_json = res.get("r_posthoc")

                if res["results"]["status"] == "success":
                    n_edges = len(res["results"].get("edges", []))

                    # Posthoc status check
                    ph_msg = ""
                    if compute_ph:
                        if res.get("r_posthoc"):
                            ph_msg = " | ✅ R posthoc computed"
                        else:
                            ph_msg = " | ⚠️ R posthoc failed (check logs)"

                    status.update(
                        label=f"✅ MGM Completed ({n_edges} edges){ph_msg}", state="complete"
                    )
                    st.success(f"MGM analysis completed! found {n_edges} edges.{ph_msg}")

                    # Suggest Explore
                    st.info("💡 Analysis complete! Go to the 'Explore' page to visualize results.")
                    
                    st.divider()
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("➡️ Go to Explore", type="primary", use_container_width=True):
                            st.session_state["nav_selection"] = "Explore"
                            st.rerun()
                    with col2:
                        if st.button("📊 Temporal Networks (VAR)", use_container_width=True):
                            st.session_state["nav_selection"] = "Temporal Networks (VAR)"
                            st.rerun()
                else:
                    status.update(label="⚠️ MGM Failed", state="error")
                    st.error("MGM Analysis reported failure.")
                    # Show messages
                    for msg in res["results"].get("messages", []):
                        if msg["level"] == "error":
                            st.error(f"[{msg['code']}] {msg['message']}")
                        elif msg["level"] == "warning":
                            st.warning(f"[{msg['code']}] {msg['message']}")
                        else:
                            st.info(f"[{msg['code']}] {msg['message']}")
            except RBackendError as e:
                status.update(label="❌ R Backend Error", state="error")
                st.error(e.message)
                if show_output:
                    st.code(e.stdout or "", language="text")
                    st.code(e.stderr or "", language="text")
            except Exception as e:
                status.update(label="❌ Unexpected Error", state="error")
                st.error(str(e))


def compute_explore_artifacts(session_state, lang, config, analysis_id):
    """Compute all explore artifacts and return as dict."""
    results = session_state.results_json
    if not results or results.get("status") != "success":
        return None

    use_abs = config["use_absolute_weights"]

    # 1. Pipeline: Build Derived Metrics (Agent B + D)
    derived = build_derived_metrics(results, config)

    # Merge R posthoc if available in session
    # (Analysis checks should be done, but simplified for now)
    r_posthoc = session_state.get("r_posthoc_json")
    if r_posthoc:
        # Check analysis_id match to be safe
        if r_posthoc.get("analysis_id") == results.get("analysis_id"):
            derived = merge_r_posthoc_into_derived(derived, r_posthoc)
        else:
            st.warning("⚠️ R posthoc ID does not match Results ID. Ignoring posthoc.")

    # Save to session (optional, but good for debug)
    session_state["derived_metrics_json"] = derived

    # 2. DataFrames (Agent C)
    # Re-use computations from plots.py/posthoc_metrics.py
    # Filtered edges for table
    edges_df = compute_edges_filtered_df(results, config)

    # Node Metrics Table
    # This now contains Strength, EI, Bridge, AND Predictability
    centrality_df = build_node_metrics_df(derived)

    # 3. Preparation for Visualization (PyVis)
    # We need the filtered edge list for the visualizer
    # filter_edges_for_explore was computed inside build_derived_metrics,
    # but exact object access is via 'derived' which has metrics, not edge list directly.
    # So we recompute it or use the DF?
    # We can invoke filter_edges_by_threshold (old) or filter_edges_for_explore (new).
    # Since we are modifying, let's stick to consistent logic.
    # edges_df is already filtered.

    # Reconstruct edge list for PyVis from edges_df or re-call filter
    # To keep exact objects, re-call (cheap):
    from hygeia_graph.posthoc_metrics import filter_edges_for_explore

    viz_edges = filter_edges_for_explore(results, config)

    nodes_meta = make_nodes_meta(results)

    # Inject Community info into nodes_meta for PyVis coloring
    # If communities enabled
    if can_enable_communities(r_posthoc) and "communities" in derived:
        mem = derived["communities"].get("membership", {})
        colors_map = map_community_to_colors(mem)
        for nid, comm in mem.items():
            if nid in nodes_meta:
                nodes_meta[nid]["community_id"] = comm
                # We can store the color directly or handle in visualizer
                nodes_meta[nid]["_community_color"] = colors_map.get(str(comm))

    # Inject Predictability info into nodes_meta for Tooltips
    if can_enable_predictability(r_posthoc):
        by_node = derived.get("node_metrics", {}).get("predictability", {})
        metric_map = derived.get("node_metrics", {}).get("predictability_metric", {})
        for nid, val in by_node.items():
            if nid in nodes_meta:
                met = metric_map.get(nid, "pred")
                nodes_meta[nid]["_predictability_label"] = f"{met}: {val:.2f}"
                nodes_meta[nid]["_predictability_val"] = val

    G_viz = build_graph_from_results(
        {"nodes": results["nodes"], "edges": viz_edges}, use_absolute_weights=use_abs
    )

    net = build_pyvis_network(
        G_viz,
        nodes_meta=nodes_meta,
        height="600px",
        width="100%",
        show_labels=config["show_labels"],
        physics=config["physics"],
    )
    html = network_to_html(net)

    # Stats
    n_edges_filtered = len(viz_edges)

    return {
        "edges_df": edges_df,
        "centrality_df": centrality_df,
        "pyvis_html": html,
        "edges_count": n_edges_filtered,
        "nodes_count": len(results["nodes"]),
        "derived_metrics": derived,  # Store if needed for Overview tab
    }


def render_explore_page(lang: str, analysis_id: str, config_hash: str):
    """Render Explore page using cached artifacts."""
    st.header("Explore Results")

    if not analysis_id:
        st.warning("No active analysis found. Please run MGM first.")
        return

    # Retrieve from cache
    cached = get_cached_outputs(st.session_state, analysis_id, config_hash)

    if not cached:
        st.info("👆 Please click **'Run selected analyses'** in the sidebar to generate results.")
        return

    # Unpack
    edges_df = cached["edges_df"]
    centrality_df = cached["centrality_df"]
    pyvis_html = cached["pyvis_html"]

    # Tabs
    tab_overview, tab_net, tab_metrics, tab_edges, tab_export = st.tabs(
        ["Overview", "Network", "Node Metrics", "Edges", "Export"]
    )

    with tab_overview:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Nodes", cached["nodes_count"])
        c2.metric("Filtered Edges", cached["edges_count"])
        # c3.metric("Displayed Edges", cached["viz_edges_count"]) # deprecated logic

        derived = cached.get("derived_metrics")

        # Community Summary
        if derived and "communities" in derived and derived["communities"].get("enabled"):
            st.divider()
            c_sum = derived["communities"]
            st.write(f"### Communities ({c_sum.get('algorithm')})")
            st.write(f"Detected **{c_sum.get('n_communities')}** communities")

            mem = c_sum.get("membership", {})
            counts = get_community_counts(mem)
            # Show small table
            c_df = pd.DataFrame(list(counts.items()), columns=["Community", "Size"])
            c_df["Community"] = c_df["Community"].astype(str)
            c_df = c_df.sort_values("Size", ascending=False)
            st.dataframe(c_df.set_index("Community"), height=150)

        st.divider()
        st.write("### Top Nodes (Strength)")
        if not centrality_df.empty:
            st.dataframe(centrality_df.head(10), use_container_width=True)

    with tab_net:
        components.html(pyvis_html, height=650, scrolling=True)
        with st.expander("Legend"):
            st.markdown(prepare_legend_html(), unsafe_allow_html=True)

    with tab_metrics:
        st.write("### Node Centrality (Strength)")
        st.dataframe(centrality_df, use_container_width=True)

    with tab_edges:
        st.write("### Edge Table")
        st.dataframe(edges_df, use_container_width=True)

    with tab_export:
        st.write("### Export Artifacts")
        # Reuse existing files in cache/state
        if st.session_state.results_json:
            st.download_button(
                "Download results.json",
                json.dumps(st.session_state.results_json, indent=2),
                "results.json",
                "application/json",
            )
        if not edges_df.empty:
            st.download_button(
                "Download filtered_edges.csv",
                edges_df.to_csv(index=False),
                "filtered_edges.csv",
                "text/csv",
            )
        if not centrality_df.empty:
            st.download_button(
                "Download centrality.csv",
                centrality_df.to_csv(index=False),
                "centrality.csv",
                "text/csv",
            )
        st.download_button("Download network.html", pyvis_html, "network.html", "text/html")

        st.divider()
        st.write("### Continue Analysis")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("➡️ Next: Report & Export", use_container_width=True):
                st.session_state["nav_selection"] = "Report & Export"
                st.rerun()
        with col2:
            if st.button("📊 Temporal Networks (VAR)", use_container_width=True):
                st.session_state["nav_selection"] = "Temporal Networks (VAR)"
                st.rerun()

        st.divider()
        render_publication_pack_section(
            lang,
            analysis_id,
            config={"threshold": 0.0, "nodes_count": cached.get("nodes_count", 0)},
        )


def render_publication_pack_section(lang: str, analysis_id: str, config: dict):
    """Render the Publication Pack export section."""
    st.write("### 📦 Publication Pack (PDF/SVG Figures)")
    st.caption(
        "Generate publication-ready figures (qgraph network, "
        "predictability pie, community hulls) and download as ZIP."
    )

    with st.expander("⚙️ Publication Pack Settings", expanded=False):
        c1, c2 = st.columns(2)
        thresh = c1.number_input(
            "Threshold (abs)",
            0.0,
            1.0,
            config.get("threshold", 0.0),
            0.05,
            key="pp_thresh",
        )
        top_k = c1.number_input("Top Edges", 0, 10000, 500, 10, key="pp_topk")

        layout = c2.selectbox("Layout", ["spring", "circle"], key="pp_layout")
        show_lbl = c2.checkbox(
            "Show Labels",
            value=True if config.get("nodes_count", 0) < 50 else False,
            key="pp_lbl",
        )
        use_abs = c2.checkbox("Use Abs Filter", value=True, key="pp_abs")

    settings = {
        "threshold": thresh,
        "top_edges": int(top_k) if top_k > 0 else None,
        "layout": layout,
        "show_labels": show_lbl,
        "use_abs_filter": use_abs,
        "width": 10.0,
        "height": 8.0,
    }

    from hygeia_graph.publication_pack_interface import (
        PublicationPackError,
        run_publication_pack_subprocess,
    )
    from hygeia_graph.publication_pack_utils import (
        build_publication_zip,
        pack_settings_hash,
    )

    settings_hash = pack_settings_hash(settings, analysis_id)

    # Caching
    if "publication_cache" not in st.session_state:
        st.session_state["publication_cache"] = {}
    if analysis_id not in st.session_state["publication_cache"]:
        st.session_state["publication_cache"][analysis_id] = {}

    cached_pack = st.session_state["publication_cache"][analysis_id].get(settings_hash)

    # Generate Button
    if st.button("📦 Generate Publication Pack", type="primary", key="gen_pub_pack"):
        with st.status("Generating Publication Pack...", expanded=True) as status:
            try:
                derived = st.session_state.get("derived_metrics_json")
                if not derived:
                    status.write("⚠️ Derived metrics not found, using raw results.")

                status.write("Running R (qgraph)...")

                out = run_publication_pack_subprocess(
                    results_json=st.session_state.results_json,
                    schema_json=st.session_state.schema_obj,
                    derived_metrics_json=derived,
                    **settings,
                    timeout_sec=300,
                )

                status.write("Building ZIP bundle...")

                from hygeia_graph.plots import compute_edges_filtered_df

                pack_cfg = {
                    "threshold": settings["threshold"],
                    "top_edges": settings["top_edges"],
                    "use_absolute_weights": True,
                }
                edges_df = compute_edges_filtered_df(st.session_state.results_json, pack_cfg)

                centrality_df = None
                if derived:
                    from hygeia_graph.plots import build_node_metrics_df

                    centrality_df = build_node_metrics_df(derived)

                import tempfile
                from pathlib import Path

                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                    zip_path = Path(tmp_zip.name)

                build_publication_zip(
                    zip_path=zip_path,
                    analysis_id=analysis_id,
                    schema_json=st.session_state.schema_obj,
                    model_spec_json=st.session_state.model_spec_obj,
                    results_json=st.session_state.results_json,
                    derived_metrics_json=derived,
                    edges_df=edges_df,
                    centrality_df=centrality_df,
                    pack_out_dir=Path(out["paths"]["out_dir"]),
                )

                with open(zip_path, "rb") as f:
                    zip_bytes = f.read()

                zip_path.unlink()

                cached_pack = {
                    "zip_bytes": zip_bytes,
                    "meta": out["meta"],
                    "preview_fig": None,
                }

                figs = out.get("files", {}).get("figures", [])
                net_svg = next((f for f in figs if "network_qgraph.svg" in f), None)
                if net_svg:
                    svg_path = Path(out["paths"]["out_dir"]) / "figures/network_qgraph.svg"
                    if svg_path.exists():
                        with open(svg_path, "r") as f:
                            cached_pack["preview_fig"] = f.read()

                st.session_state["publication_cache"][analysis_id][settings_hash] = cached_pack

                status.update(label="✅ Publication Pack Ready!", state="complete")

            except PublicationPackError as e:
                status.update(label="❌ Generation Failed", state="error")
                st.error(e.message)
                if e.stderr:
                    with st.expander("Error Log"):
                        st.code(e.stderr)
            except Exception as e:
                status.update(label="❌ Unexpected Error", state="error")
                st.error(str(e))

    # Download Section
    if cached_pack:
        st.success("Publication Pack available for download.")

        d1, d2 = st.columns([1, 2])
        d1.download_button(
            "📥 Download Full Pack (.zip)",
            cached_pack["zip_bytes"],
            f"publication_pack_{analysis_id}.zip",
            "application/zip",
            type="primary",
            key="dl_pub_pack",
        )

        if cached_pack.get("preview_fig"):
            with st.expander("👁️ Preview Network Figure"):
                components.html(cached_pack["preview_fig"], height=600, scrolling=True)


def render_simulation_page(lang: str, analysis_id: str, config_hash: str):
    """Render Intervention Simulation page."""
    st.header("🔬 Intervention Simulation (Experimental)")

    st.warning(
        "⚠️ **Disclaimer:** This is an **associational propagation** simulation based on the estimated network. "
        "It is **NOT causal inference** and should not be interpreted as assessing the effect of a randomized intervention. "
        "Intended for hypothesis generation only."
    )

    if not analysis_id:
        st.info("Please run MGM Analysis first.")
        return

    # Check results success
    if not st.session_state.results_json or st.session_state.results_json["status"] != "success":
        st.error("MGM Analysis failed or not found.")
        return

    results = st.session_state.results_json
    df = st.session_state.df

    # Imports
    import plotly.express as px

    from hygeia_graph.intervention_simulation import (
        build_intervention_artifact,
        build_intervention_table,
        build_signed_adjacency,
        simulate_intervention,
    )
    from hygeia_graph.intervention_utils import simulation_settings_hash

    # 1. Controls
    with st.expander("⚙️ Simulation Settings", expanded=True):
        c1, c2 = st.columns(2)

        # Node Selector
        nodes = results.get("nodes", [])
        node_ids = [n["id"] for n in nodes]
        node_map = make_nodes_meta(results)

        # Display labels in selectbox
        def fmt_node(nid):
            return f"{node_map[nid].get('label', nid)} ({nid})"

        if not node_ids:
            st.warning("No nodes available for simulation. Please run MGM analysis first.")
            return
            
        target_node = c1.selectbox("Intervention Node", node_ids, format_func=fmt_node)

        # Delta
        delta_type = c2.radio("Delta Units", ["Standardized (SD)", "Raw Units"], horizontal=True)
        is_sd = delta_type == "Standardized (SD)"

        if is_sd:
            delta = st.slider("Delta (SD)", -2.0, 2.0, 1.0, 0.1)
            delta_val = float(delta)
            st.caption(f"Simulating a {delta} SD change in {target_node}.")
        else:
            delta = st.number_input("Delta (Raw)", value=1.0)
            delta_val = float(delta)
            st.caption(
                "⚠️ Raw units assumes edge weights are compatible (standardized edges require standardized inputs)."
            )

        # Advanced
        st.divider()
        ac1, ac2, ac3 = st.columns(3)
        steps = ac1.slider("Propagation Steps", 1, 5, 2)
        damping = ac2.slider("Damping Factor", 0.1, 1.0, 0.6, 0.1)

        # Filtering
        use_explore_cfg = st.checkbox("Use 'Explore' thresholds?", value=True)

        thresh = 0.0
        top_k = None

        if use_explore_cfg and "explore_config" in st.session_state:
            cfg = st.session_state["explore_config"]
            thresh = cfg.get("threshold", 0.0)
            top_k = cfg.get("top_edges", None)
            st.caption(f"Using Threshold >= {thresh}, Top Edges = {top_k if top_k else 'All'}")

    # 2. Key for Caching
    settings = {
        "intervene_node": target_node,
        "delta": delta_val,
        "delta_units": "sd" if is_sd else "raw",
        "steps": int(steps),
        "damping": float(damping),
        "threshold": thresh,
        "top_edges": top_k,
    }

    sim_hash = simulation_settings_hash(settings, analysis_id)

    # Cache container
    if "simulation_cache" not in st.session_state:
        st.session_state["simulation_cache"] = {}
    if analysis_id not in st.session_state["simulation_cache"]:
        st.session_state["simulation_cache"][analysis_id] = {}

    cached_sim = st.session_state["simulation_cache"][analysis_id].get(sim_hash)

    # Run
    if st.button("🚀 Run Simulation", type="primary"):
        with st.spinner("Computing propagation..."):
            # Build Matrix based on settings
            sim_ids, A_signed = build_signed_adjacency(results, threshold=thresh, top_edges=top_k)

            # Simulate
            sim_out = simulate_intervention(
                sim_ids,
                A_signed,
                intervene_node=target_node,
                delta=delta_val,
                steps=int(steps),
                damping=float(damping),
            )

            # Table
            df_table = build_intervention_table(
                df, sim_ids, sim_out["effects"], input_node=target_node, node_map=node_map, top_n=50
            )

            # Artifact
            artifact = build_intervention_artifact(results, sim_out, df_table, settings)

            # Store
            cached_sim = {"artifact": artifact, "table": df_table}
            st.session_state["simulation_cache"][analysis_id][sim_hash] = cached_sim
            st.success("Simulation complete.")

    # 3. Results
    if cached_sim:
        st.divider()

        tbl = cached_sim["table"]

        if tbl.empty:
            st.warning("No nodes affected (check threshold or connectivity).")
        else:
            # Summary
            top_row = tbl.iloc[0]
            st.markdown(
                f"### Result: Strongest impact on **{top_row['label']}** ({top_row['effect']:.3f})"
            )

            c_plot, c_data = st.columns([2, 1])

            with c_plot:
                # Plotly Bar Chart
                # Sort for plotting (ascending so top is at top)
                plot_df = tbl.head(20).copy()
                plot_df["color"] = plot_df["effect"] > 0

                fig = px.bar(
                    plot_df.sort_values("abs_effect", ascending=True),
                    x="effect",
                    y="label",
                    color="direction",
                    orientation="h",
                    title=f"Top Affected Nodes by {target_node} (Δ={delta_val})",
                    color_discrete_map={
                        "increase": "#2ecc71",
                        "decrease": "#e74c3c",
                        "neutral": "#95a5a6",
                    },
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

            with c_data:
                st.dataframe(
                    tbl[["label", "effect", "direction"]].head(20),
                    use_container_width=True,
                    height=500,
                )

            # Exports
            st.subheader("Exports")
            e1, e2 = st.columns(2)

            e1.download_button(
                "📥 Simulation Report (JSON)",
                json.dumps(cached_sim["artifact"], indent=2),
                "simulation_report.json",
                "application/json",
            )

            e2.download_button(
                "📥 Effect Table (CSV)",
                tbl.to_csv(index=False),
                "simulation_effects.csv",
                "text/csv",
            )

        st.divider()
        st.write("### Continue Analysis")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("➡️ Next: Report & Export", type="primary", use_container_width=True):
                st.session_state["nav_selection"] = "Report & Export"
                st.rerun()
        with col2:
            if st.button("🔗 Go to Explore", use_container_width=True):
                st.session_state["nav_selection"] = "Explore"
                st.rerun()


def render_preprocessing_page(lang: str):
    """Render Preprocessing (Feature Selection) page."""
    st.header("Preprocessing: Feature Selection")

    if st.session_state.df is None:
        st.info("Please upload a dataset first.")
        return

    # Imports locally to avoid top-level cost if unused
    from hygeia_graph.heavy_guardrails import (
        LASSO_HARD_MAX_FEATURES,
        LASSO_HARD_MAX_NFOLDS,
        LASSO_SAFE_MAX_FEATURES,
        normalize_lasso_settings,
        render_messages_to_markdown,
    )
    from hygeia_graph.preprocess_interface import PreprocessError, run_lasso_select_subprocess
    from hygeia_graph.preprocess_utils import compute_dataset_hash, lasso_settings_hash

    # 1. Settings
    df = st.session_state.df
    cols = df.columns.tolist()

    with st.expander("⚙️ LASSO Settings", expanded=True):
        c1, c2 = st.columns(2)
        target = c1.selectbox("Target Variable (Outcome)", cols, index=0)
        family = c2.selectbox("Family", ["auto", "gaussian", "binomial", "multinomial"], index=0)

        c3, c4 = st.columns(2)
        max_feat = c3.number_input(
            "Max Features to Keep", 1, LASSO_HARD_MAX_FEATURES, 30
        )
        lambda_rule = c4.selectbox("Lambda Rule", ["lambda.1se", "lambda.min"], index=0)

        # Advanced
        st.caption("Advanced")
        ac1, ac2, ac3 = st.columns(3)
        nfolds = ac1.number_input("CV Folds", 3, LASSO_HARD_MAX_NFOLDS, 5)
        alpha = ac2.number_input("Alpha (1=Lasso)", 0.0, 1.0, 1.0)
        seed = ac3.number_input("Seed", value=1)
        standardize = st.checkbox("Standardize predictors", True)

    # Advanced unlock for LASSO
    st.caption(
        f"⚙️ Safe limits: nfolds≤10, max_features≤{LASSO_SAFE_MAX_FEATURES}."
    )
    lasso_advanced = st.checkbox(
        "🔓 Advanced unlock (allow larger LASSO settings)",
        value=False,
        key="lasso_advanced",
    )

    # 2. Run
    raw_settings = {
        "target": target,
        "family": family,
        "max_features": int(max_feat),
        "lambda_rule": lambda_rule,
        "nfolds": int(nfolds),
        "alpha": float(alpha),
        "seed": int(seed),
        "standardize": standardize,
    }

    # Normalize LASSO settings with guardrails
    norm_lasso, lasso_msgs = normalize_lasso_settings(
        raw_settings,
        advanced_unlocked=lasso_advanced,
        n_rows=len(df),
        n_cols=len(df.columns),
    )

    # Show guardrail messages
    if lasso_msgs:
        lasso_md = render_messages_to_markdown(lasso_msgs)
        st.warning(lasso_md)

    # Use normalized settings
    settings = norm_lasso
    st.session_state["lasso_settings_effective"] = settings

    # Caching key
    # Helper to store in custom cache
    if "preprocess_cache" not in st.session_state:
        st.session_state["preprocess_cache"] = {}

    ds_hash = compute_dataset_hash(df)
    s_hash = lasso_settings_hash(settings, ds_hash)

    cached_res = st.session_state["preprocess_cache"].get(ds_hash, {}).get(s_hash)

    if st.button("🔬 Run LASSO Selection", type="primary"):
        if cached_res:
            st.success("Loaded from cache!")
        else:
            with st.status("Running LASSO (glmnet)...", expanded=True) as status:
                try:
                    res = run_lasso_select_subprocess(df, **settings)
                    status.update(label="✅ LASSO Completed", state="complete")

                    if ds_hash not in st.session_state["preprocess_cache"]:
                        st.session_state["preprocess_cache"][ds_hash] = {}

                    st.session_state["preprocess_cache"][ds_hash][s_hash] = res
                    cached_res = res
                    st.success(f"Selected {res['meta']['selected']['n_selected']} features.")

                except PreprocessError as e:
                    status.update(label="❌ LASSO Failed", state="error")
                    st.error(e.message)
                    if e.stdout:
                        with st.expander("Logs"):
                            st.text(e.stdout)
                            st.text(e.stderr)
                except ValueError as e:
                    status.update(label="❌ Validation Error", state="error")
                    st.error(str(e))
                except Exception as e:
                    status.update(label="❌ Unexpected Error", state="error")
                    st.error(str(e))

    # 3. Results
    if cached_res:
        st.divider()
        meta = cached_res["meta"]
        sel = meta.get("selected", {})

        st.subheader(f"Results: {sel.get('n_selected', 0)} Features Selected")

        tab_list, tab_coef, tab_preview = st.tabs(
            ["Selected Columns", "Coefficients", "Preview Filtered Data"]
        )

        with tab_list:
            st.write(sel.get("columns", []))
            st.caption(f"Family used: {meta.get('settings', {}).get('family_used')}")

        with tab_coef:
            if cached_res["coeff_table"] is not None:
                st.dataframe(cached_res["coeff_table"], use_container_width=True)
            else:
                st.info("No coefficient table available.")

        with tab_preview:
            fdf = cached_res["filtered_df"]
            if fdf is not None:
                st.dataframe(fdf.head(10), use_container_width=True)
                st.caption(f"Filtered Shape: {fdf.shape}")

                # Apply Action
                st.divider()
                st.write("### Apply to Analysis")
                st.warning(
                    "⚠️ This will overwrite your current dataset and reset any existing analysis (Schema, Model, Results)."
                )

                # Option to keep target in network
                keep_target = st.checkbox(
                    "Include Target variable in MGM network?",
                    value=False,
                    help="If checked, the target column is kept in the main analysis. If unchecked, it is used only for selection and removed.",
                )

                if st.button("🚀 Use this Filtered Dataset"):
                    # Logic to apply
                    new_df = fdf.copy()
                    if not keep_target and target in new_df.columns:
                        new_df = new_df.drop(columns=[target])

                    # Update State
                    st.session_state.df = new_df
                    st.session_state.missing_rate = (
                        0.0  # Assumption: filtered DF comes from complete cases check passed?
                    )
                    # Actually checkLASSO enforced no missing. So new DF is clean.

                    # Clear artifacts
                    st.session_state.variables = None
                    st.session_state.schema_obj = None
                    st.session_state.schema_valid = False
                    st.session_state.model_spec_obj = None
                    st.session_state.model_spec_valid = False
                    st.session_state.results_json = None

                    # Clear caches
                    # We might want to keep preprocess cache? Yes.
                    st.session_state.get("derived_cache", {}).clear()
                    st.session_state.get("robustness_cache", {}).clear()
                    st.session_state.get("report_cache", {}).clear()

                    st.success(
                        f"Dataset updated! New shape: {new_df.shape}. Please go to 'Data & Schema' to rebuild schema."
                    )
                    st.session_state["_flash_msg"] = (
                        "Dataset filtered via LASSO. Please rebuild schema."
                    )
                    # Force rerun? Or user clicks manually.
            else:
                st.error("Filtered dataframe missing.")

        # Exports
        st.subheader("Downloads")
        d1, d2, d3 = st.columns(3)
        d1.download_button(
            "📥 Lasso Meta (JSON)",
            json.dumps(meta, indent=2),
            "lasso_meta.json",
            "application/json",
        )
        if cached_res["coeff_table"] is not None:
            d2.download_button(
                "📥 Coefficients (CSV)",
                cached_res["coeff_table"].to_csv(index=False),
                "lasso_coeffs.csv",
                "text/csv",
            )
        if cached_res["filtered_df"] is not None:
            d3.download_button(
                "📥 Filtered Data (CSV)",
                cached_res["filtered_df"].to_csv(index=False),
                "filtered_data.csv",
                "text/csv",
            )

        st.divider()
        st.write("### Continue Analysis")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("➡️ Next: Model Settings", type="primary", use_container_width=True):
                st.session_state["nav_selection"] = "Model Settings"
                st.rerun()
        with col2:
            if st.button("📊 Go to Report & Export", use_container_width=True):
                st.session_state["nav_selection"] = "Report & Export"
                st.rerun()

    """Render Report & Export page."""
    st.header("Report & Export")

    if not st.session_state.results_json:
        st.info("No results available to export.")
        return

    st.success("✅ Analysis artifacts available.")

    st.subheader("Reproducibility Notes")
    analysis_id = st.session_state.results_json.get("analysis_id", "N/A")
    st.code(f"Analysis ID: {analysis_id}", language="text")

    st.subheader("Automated Insights Report")

    # Imports
    from hygeia_graph.insights_report import generate_insights_report
    from hygeia_graph.insights_report_utils import report_settings_hash

    # Settings
    with st.expander("📝 Report Settings", expanded=True):
        c1, c2 = st.columns(2)
        style = c1.selectbox("Narrative Style", ["paper", "thesis", "concise"], index=0)
        top_n = c2.number_input("Top N Nodes to list", 3, 20, 10)

        st.write("**Include Sections:**")
        rc1, rc2, rc3, rc4 = st.columns(4)
        # Check inputs availability
        res = st.session_state.results_json
        der = st.session_state.get("derived_metrics_json")
        boot_meta = st.session_state.get("bootnet_meta")
        # NCT summary would be here in future

        has_pred = False
        has_comm = False
        if der:
            if der.get("node_metrics", {}).get("predictability"):
                has_pred = True
            if der.get("communities", {}).get("enabled"):
                has_comm = True

        inc_pred = rc1.checkbox("Predictability", value=has_pred, disabled=not has_pred)
        inc_comm = rc2.checkbox("Communities", value=has_comm, disabled=not has_comm)
        inc_rob = rc3.checkbox(
            "Robustness", value=(boot_meta is not None), disabled=(boot_meta is None)
        )
        inc_comp = rc4.checkbox(
            "Comparison", value=False, disabled=True, help="Run Comparison (NCT) first"
        )

    # Generate
    settings = {
        "style": style,
        "top_n": int(top_n),
        "include_predictability": inc_pred,
        "include_communities": inc_comm,
        "include_robustness": inc_rob,
        "include_comparison": inc_comp,
    }

    # Caching
    analysis_id = res.get("analysis_id", "unknown")
    settings_hash = report_settings_hash(settings, analysis_id)

    if "report_cache" not in st.session_state:
        st.session_state["report_cache"] = {}

    cached_report = st.session_state["report_cache"].get(analysis_id, {}).get(settings_hash)

    if st.button("📄 Generate Insights Report", type="primary"):
        if not der:
            st.warning(
                "Please visit the Explore page to compute derived metrics first (or Run selected analyses)."
            )
        else:
            with st.spinner("Writing report..."):
                rep = generate_insights_report(
                    results_json=res,
                    derived_metrics_json=der,
                    explore_cfg=getattr(
                        st.session_state, "explore_config_cache", {}
                    ),  # Best effort config
                    bootnet_meta=st.session_state.get("bootnet_meta"),
                    bootnet_tables=st.session_state.get(
                        "bootnet_tables"
                    ),  # Assuming loaded into session by robustness page
                    nct_summary=st.session_state.get("nct_summary"),
                    settings=settings,
                )

                # Cache
                if analysis_id not in st.session_state["report_cache"]:
                    st.session_state["report_cache"][analysis_id] = {}
                st.session_state["report_cache"][analysis_id][settings_hash] = rep
                cached_report = rep
                st.session_state["insights_report_md"] = rep["markdown"]
                st.success("Report generated!")

    # Display & Export
    if cached_report:
        st.divider()
        md_text = cached_report["markdown"]
        payload = cached_report["payload"]

        tab_view, tab_raw = st.tabs(["📄 Preview", "RAW Markdown"])
        with tab_view:
            st.markdown(md_text)
        with tab_raw:
            st.text_area("Copy Markdown", md_text, height=300)

        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "📥 Download Report.md", md_text, f"report_{analysis_id}.md", "text/markdown"
        )
        c2.download_button(
            "📥 Download Report.txt", md_text, f"report_{analysis_id}.txt", "text/plain"
        )
        c3.download_button(
            "📥 Download Payload.json",
            json.dumps(payload, indent=2),
            f"report_payload_{analysis_id}.json",
            "application/json",
        )

    st.subheader("Raw Artifact Downloads")
    c1, c2 = st.columns(2)
    with c1:
        st.json(st.session_state.results_json, expanded=False)
        st.download_button(
            "📥 Download results.json",
            json.dumps(st.session_state.results_json, indent=2),
            "results.json",
            "application/json",
            key="dl_res_json",
        )
    with c2:
        if st.session_state.schema_obj:
            st.download_button(
                "📥 Download schema.json",
                json.dumps(st.session_state.schema_obj, indent=2),
                "schema.json",
                "application/json",
                key="dl_schema_json",
            )
        if st.session_state.model_spec_obj:
            st.download_button(
                "📥 Download model_spec.json",
                json.dumps(st.session_state.model_spec_obj, indent=2),
                "model_spec.json",
                "application/json",
                key="dl_spec_json",
            )


def render_report_page(lang: str, analysis_id: str, config_hash: str):
    """Render Report & Export page."""
    st.header("📊 Report & Export")

    if not st.session_state.results_json:
        st.warning("Please run MGM analysis first.")
        return

    # Report generation
    st.subheader("📝 Insights Report")

    from hygeia_graph.insights_report import (
        build_report_payload,
        generate_insights_report,
    )

    if st.button("Generate Insights Report", type="primary"):
        derived = st.session_state.get("derived_metrics_json")
        bootnet = st.session_state.get("bootnet_cache", {}).get(analysis_id)

        payload = build_report_payload(
            results_json=st.session_state.results_json,
            derived_metrics_json=derived,
            explore_cfg=st.session_state.get("explore_config"),
            bootnet_meta=bootnet.get("meta") if bootnet else None,
            bootnet_tables=bootnet.get("tables") if bootnet else None,
            nct_meta=None,
            nct_summary=None,
            nct_edge_table=None,
            settings={"top_n": 10, "style": "paper"},
        )

        report = generate_insights_report(
            results_json=st.session_state.results_json,
            derived_metrics_json=derived,
            explore_cfg=st.session_state.get("explore_config"),
            bootnet_meta=bootnet.get("meta") if bootnet else None,
            bootnet_tables=bootnet.get("tables") if bootnet else None,
            settings={"top_n": 10, "style": "paper"},
        )
        st.session_state["insights_report"] = report["markdown"]

    if "insights_report" in st.session_state:
        st.markdown(st.session_state["insights_report"])
        st.download_button(
            "📥 Download Report",
            st.session_state["insights_report"],
            f"insights_report_{analysis_id}.md",
            "text/markdown",
        )

    # Descriptive Statistics section
    st.divider()
    st.subheader("📈 Dataset Descriptive Statistics")

    from hygeia_graph.descriptives import (
        build_categorical_levels_table,
        build_descriptives_payload,
        build_variable_summary_table,
        classify_variables,
        compute_missing_summary,
    )

    df = st.session_state.get("df")
    if df is None:
        st.info("Upload a dataset to compute descriptive statistics.")
    else:
        with st.expander("⚙️ Settings", expanded=False):
            use_schema = st.checkbox(
                "Use schema types if available",
                value=True,
                key="desc_use_schema",
            )
            run_normality = st.checkbox(
                "Run normality tests for continuous variables",
                value=True,
                key="desc_normality",
            )
            st.caption("Normality tests are sensitive at large n; interpret with caution.")

        if st.button("🔬 Compute Descriptives", type="primary", key="compute_desc"):
            # Compute
            schema_json = st.session_state.schema_obj if use_schema else None
            variables = classify_variables(df, schema_json)
            missing_summary = compute_missing_summary(df)
            var_summary_df = build_variable_summary_table(df, variables, run_normality)
            cat_levels_df = build_categorical_levels_table(df, variables)
            payload = build_descriptives_payload(missing_summary, var_summary_df)

            # Store in session state
            st.session_state["descriptives_payload"] = payload
            st.session_state["descriptives_var_summary"] = var_summary_df
            st.session_state["descriptives_cat_levels"] = cat_levels_df

            st.success("✅ Descriptive statistics computed!")

        # Display if computed
        if "descriptives_payload" in st.session_state:
            payload = st.session_state["descriptives_payload"]
            var_summary_df = st.session_state["descriptives_var_summary"]
            cat_levels_df = st.session_state["descriptives_cat_levels"]

            # KPIs
            cols = st.columns(5)
            cols[0].metric("Rows", payload["n_rows"])
            cols[1].metric("Columns", payload["n_cols"])
            cols[2].metric("Missing Rate", f"{payload['missing_rate']:.1%}")
            cols[3].metric("Continuous", payload["variables"]["n_continuous"])
            cols[4].metric("Categorical", payload["variables"]["n_nominal"] + payload["variables"]["n_ordinal"])

            # Table preview
            st.dataframe(var_summary_df.head(20), use_container_width=True)

            # Downloads
            c1, c2, c3 = st.columns(3)
            c1.download_button(
                "📥 variable_summary.csv",
                var_summary_df.to_csv(index=False),
                "variable_summary.csv",
                "text/csv",
                key="dl_var_summary",
            )
            c2.download_button(
                "📥 categorical_levels.csv",
                cat_levels_df.to_csv(index=False),
                "categorical_levels.csv",
                "text/csv",
                key="dl_cat_levels",
            )
            c3.download_button(
                "📥 descriptives.json",
                json.dumps(payload, indent=2),
                "descriptives.json",
                "application/json",
                key="dl_desc_json",
            )

    # Exports section
    st.divider()
    st.subheader("📦 Exports")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "📥 results.json",
            json.dumps(st.session_state.results_json, indent=2),
            "results.json",
            "application/json",
            key="dl_results_exp",
        )
    with c2:
        if st.session_state.schema_obj:
            st.download_button(
                "📥 schema.json",
                json.dumps(st.session_state.schema_obj, indent=2),
                "schema.json",
                "application/json",
                key="dl_schema_exp",
            )
    with c3:
        if st.session_state.model_spec_obj:
            st.download_button(
                "📥 model_spec.json",
                json.dumps(st.session_state.model_spec_obj, indent=2),
                "model_spec.json",
                "application/json",
                key="dl_spec_exp",
            )


def render_robustness_page(lang: str, analysis_id: str, config_hash: str):
    """Render Robustness Analysis (Bootnet) page."""
    st.header("🔒 Robustness Analysis")

    if not st.session_state.results_json:
        st.warning("Please run MGM analysis first.")
        return

    st.info(
        "This page runs bootstrap analysis using bootnet to assess "
        "network stability. Requires R environment."
    )

    from hygeia_graph.heavy_guardrails import (
        BOOTNET_HARD_MAX_BOOTS,
        BOOTNET_SAFE_MAX_BOOTS,
        normalize_bootnet_settings,
        render_messages_to_markdown,
    )

    with st.expander("⚙️ Bootnet Settings", expanded=True):
        c1, c2 = st.columns(2)
        n_boots_np = c1.number_input(
            "Nonparametric bootstraps",
            50,
            BOOTNET_HARD_MAX_BOOTS,
            200,
            50,
            key="boot_np",
        )
        n_boots_case = c2.number_input(
            "Case-dropping bootstraps",
            50,
            BOOTNET_HARD_MAX_BOOTS,
            200,
            50,
            key="boot_case",
        )

        c3, c4 = st.columns(2)
        case_min = c3.slider("Case drop min", 0.1, 0.5, 0.25, 0.05, key="case_min")
        case_max = c4.slider("Case drop max", 0.5, 0.95, 0.75, 0.05, key="case_max")

        n_cores = st.selectbox("Cores", [1, 2], index=0, key="boot_cores")

    # Advanced unlock
    st.caption(
        "⚙️ Defaults optimised for Hugging Face Free CPU. "
        f"Safe limits: boots≤{BOOTNET_SAFE_MAX_BOOTS}."
    )
    advanced_unlock = st.checkbox(
        "🔓 Advanced unlock (I understand this may take a long time)",
        value=False,
        key="boot_advanced",
    )

    # Normalize settings
    raw_settings = {
        "n_boots_np": int(n_boots_np),
        "n_boots_case": int(n_boots_case),
        "n_cores": int(n_cores),
        "caseMin": case_min,
        "caseMax": case_max,
    }

    norm, msgs = normalize_bootnet_settings(raw_settings, advanced_unlocked=advanced_unlock)

    # Show effective settings
    if norm != raw_settings:
        st.info(
            f"**Effective settings:** boots_np={norm['n_boots_np']}, "
            f"boots_case={norm['n_boots_case']}, cores={norm['n_cores']}"
        )

    # Show guardrail messages
    if msgs:
        md_msgs = render_messages_to_markdown(msgs)
        st.warning(md_msgs)

    # Store effective settings
    st.session_state["bootnet_settings_effective"] = norm

    st.divider()
    st.write("### Continue Analysis")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➡️ Next: Report & Export", type="primary", use_container_width=True):
            st.session_state["nav_selection"] = "Report & Export"
            st.rerun()
    with col2:
        if st.button("🔗 Go to Explore", use_container_width=True):
            st.session_state["nav_selection"] = "Explore"
            st.rerun()


def render_temporal_page(lang: str):
    """Render Temporal Networks (VAR) analysis page."""
    st.header("🔬 Temporal Networks (VAR)")
    
    # Data validation
    if st.session_state.df is None:
        st.warning("Please upload data first.")
        return
    
    # Check required packages
    from hygeia_graph.diagnostics import check_r_packages
    r_packages = check_r_packages(["graphicalVAR"])
    if not r_packages["ok"]:
        st.error(f"Missing required packages: {r_packages['missing']}")
        st.info("Install with: install.packages('graphicalVAR')")
        return
    
    # Temporal data validation
    from hygeia_graph.temporal_validation import validate_temporal_inputs
    df = st.session_state.df
    
    # Settings
    with st.expander("⚙️ Temporal Analysis Settings", expanded=True):
        # Time column selection
        # Handle both string (column name) and integer (index) for backwards compatibility
        time_col_idx = st.session_state.get('temporal_time_col', 0)
        if isinstance(time_col_idx, str):
            # Convert column name to index
            try:
                time_col_idx = df.columns.tolist().index(time_col_idx)
            except (ValueError, AttributeError):
                time_col_idx = 0
        
        time_col = st.selectbox(
            "Time Column",
            options=df.columns.tolist(),
            index=time_col_idx
        )
        
        # Group/ID column selection
        group_cols = st.multiselect(
            "Group/ID Columns (Optional)",
            options=df.columns.tolist(),
            default=getattr(st.session_state, 'temporal_group_cols', [])
        )
        
        # Advanced settings
        st.subheader("Advanced Settings")
        allow_unequal = st.checkbox(
            "Allow Unequal Time Intervals",
            value=getattr(st.session_state, 'temporal_unequal_intervals', False)
        )
        
        advanced_unlock = st.checkbox(
            "Advanced Mode (Bypass Validations)",
            value=getattr(st.session_state, 'temporal_advanced', False)
        )
    
    # Validate inputs
    if 'temporal_time_col' not in st.session_state or st.session_state.get('temporal_time_col') != time_col:
        st.session_state.temporal_time_col = time_col
        st.session_state.temporal_group_cols = group_cols
        st.session_state.temporal_unequal_intervals = allow_unequal
        st.session_state.temporal_advanced = advanced_unlock
        
        # Run validation
        ok, messages, temporal_info = validate_temporal_inputs(
            df=df,
            time_col=time_col,
            id_col=group_cols[0] if group_cols else None,
            vars=df.columns.tolist(),
            unequal_ok=allow_unequal,
            advanced_unlock=advanced_unlock
        )
        
        if not ok:
            for msg in messages:
                st.error(f"❌ {msg}")
            st.info("💡 Consider adjusting settings or using Advanced Mode to bypass validations.")
    
    # Run analysis button
    st.divider()
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔬 Run Temporal VAR Analysis", type="primary"):
            with st.spinner("Running temporal VAR analysis... This may take several minutes..."):
                try:
                    result = run_temporal_var_subprocess(
                        df=df,
                        time_col=time_col,
                        id_col=group_cols[0] if group_cols else None,
                        vars=df.columns.tolist(),
                        timeout_sec=600
                    )
                    
                    if result["results"]["status"] == "success":
                        st.session_state.temporal_results = result["results"]
                        st.session_state.temporal_tables = result["tables"]
                        st.success("✅ Temporal VAR analysis completed successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Temporal VAR analysis failed")
                        for msg in result["results"].get("messages", []):
                            st.error(f"• {msg}")
                except Exception as e:
                    st.error(f"❌ Error running temporal analysis: {e}")
    
    with col2:
        if st.button("🗑️ Clear Results"):
            if "temporal_results" in st.session_state:
                del st.session_state.temporal_results
            if "temporal_tables" in st.session_state:
                del st.session_state.temporal_tables
            st.success("✅ Results cleared")
            st.rerun()
    
    # Results display
    if "temporal_results" in st.session_state and st.session_state.temporal_results["status"] == "success":
        st.divider()
        st.subheader("📊 Temporal VAR Analysis Results")
        
        results = st.session_state.temporal_results
        tables = st.session_state.get("temporal_tables", {})
        
        # Results summary
        meta = results.get("meta", {})
        if meta:
            st.info(f"📈 Analysis completed with {meta.get('n_subjects', 'unknown')} subjects "
                    f"and {meta.get('n_timepoints', 'unknown')} time points")
        
        # Display results in tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "🔗 Temporal Edges", 
            "⚡ Contemporaneous Edges", 
            "📈 PDC/PCC Matrices",
            "📥 Export Results"
        ])
        
        with tab1:
            st.markdown("### 🔗 Temporal (Lag) Edges")
            if "temporal_edges" in tables and tables["temporal_edges"] is not None:
                temporal_edges = tables["temporal_edges"]
                st.dataframe(temporal_edges, use_container_width=True)
                st.info("These represent cross-lagged effects from time t to t+1")
            else:
                st.info("No temporal edges found")
        
        with tab2:
            st.markdown("### ⚡ Contemporaneous Edges")
            if "contemporaneous_edges" in tables and tables["contemporaneous_edges"] is not None:
                cont_edges = tables["contemporaneous_edges"]
                st.dataframe(cont_edges, use_container_width=True)
                st.info("These represent within-time-point associations")
            else:
                st.info("No contemporaneous edges found")
        
        with tab3:
            st.markdown("### 📈 Predictive Causality Measures")
            
            subtab1, subtab2 = st.tabs(["PDC Matrix", "PCC Matrix"])
            
            with subtab1:
                if "PDC" in tables and tables["PDC"] is not None:
                    st.dataframe(tables["PDC"], use_container_width=True)
                    st.caption("Partial Directed Coherence - frequency-domain causality")
                else:
                    st.info("PDC matrix not available")
            
            with subtab2:
                if "PCC" in tables and tables["PCC"] is not None:
                    st.dataframe(tables["PCC"], use_container_width=True)
                    st.caption("Partial Correlation Coefficients")
                else:
                    st.info("PCC matrix not available")
        
        with tab4:
            st.markdown("### 📥 Export Temporal Results")
            st.info("Export temporal analysis results for further analysis")
            
            # Create download buttons for each result
            export_col1, export_col2 = st.columns(2)
            
            with export_col1:
                if "temporal_edges" in tables and tables["temporal_edges"] is not None:
                    st.download_button(
                        "📥 Download Temporal Edges",
                        data=tables["temporal_edges"].to_csv(index=False),
                        file_name="temporal_edges.csv",
                        mime="text/csv"
                    )
                
                if "contemporaneous_edges" in tables and tables["contemporaneous_edges"] is not None:
                    st.download_button(
                        "📥 Download Contemporaneous Edges",
                        data=tables["contemporaneous_edges"].to_csv(index=False),
                        file_name="contemporaneous_edges.csv",
                        mime="text/csv"
                    )
            
            with export_col2:
                if "PDC" in tables and tables["PDC"] is not None:
                    st.download_button(
                        "📥 Download PDC Matrix",
                        data=tables["PDC"].to_csv(index=False),
                        file_name="pdc_matrix.csv",
                        mime="text/csv"
                    )
                
                if "PCC" in tables and tables["PCC"] is not None:
                    st.download_button(
                        "📥 Download PCC Matrix",
                        data=tables["PCC"].to_csv(index=False),
                        file_name="pcc_matrix.csv",
                        mime="text/csv"
                    )
            
            # Export all results as ZIP
            if st.button("📦 Export All Results as ZIP"):
                with st.spinner("Creating ZIP file..."):
                    from hygeia_graph.temporal_exports import build_temporal_zip
                    zip_bytes = build_temporal_zip(results, tables)
                    
                    st.download_button(
                        "📥 Download Complete ZIP",
                        data=zip_bytes,
                        file_name="temporal_var_results.zip",
                        mime="application/zip"
                    )

        st.divider()
        st.write("### Continue Analysis")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("➡️ Go to Report & Export", type="primary", use_container_width=True):
                st.session_state["nav_selection"] = "Report & Export"
                st.rerun()
        with col2:
            if st.button("🔗 Go to Explore", use_container_width=True):
                st.session_state["nav_selection"] = "Explore"
                st.rerun()

    if st.button("Run Bootnet Analysis", type="primary"):
        st.warning("Bootnet integration requires R environment. Please ensure R is installed.")
        # Placeholder for actual bootnet integration
        # from hygeia_graph.robustness_interface import run_bootnet_subprocess
        # result = run_bootnet_subprocess(..., **norm)

