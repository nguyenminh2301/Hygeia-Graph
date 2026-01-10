"""Hygeia Graph - Streamlit Application (Sprint A)."""

import streamlit as st

from hygeia_graph.locale import LANGUAGES, t
from hygeia_graph.ui_pages import (
    compute_explore_artifacts,
    init_session_state,
    render_data_schema_page,
    render_explore_page,
    render_model_settings_page,
    render_preprocessing_page,
    render_report_page,
    render_robustness_page,
    render_run_mgm_page,
    render_simulation_page,
    render_introduction_page,
)
from hygeia_graph.ui_state import (
    clear_analysis_cache,
    explore_config_hash,
    get_analysis_id_from_state,
    get_default_explore_config,
    normalize_explore_config,
    set_cached_outputs,
)


def main():
    """Main Streamlit application."""
    st.set_page_config(page_title="Hygeia-Graph", layout="wide")

    # 1. Initialize State
    init_session_state()

    if "lang" not in st.session_state:
        st.session_state.lang = "en"

    # ---------------------------------------------------------
    # SIDEBAR: Control Tower
    # ---------------------------------------------------------
    with st.sidebar:
        st.title(t("app_title", st.session_state.lang))

        # Language
        lang_options = list(LANGUAGES.keys())
        idx = lang_options.index(st.session_state.lang)
        sel_lang = st.selectbox(
            t("language", st.session_state.lang),
            options=lang_options,
            format_func=lambda x: LANGUAGES[x],
            index=idx,
        )
        st.session_state.lang = sel_lang
        lang = st.session_state.lang

        st.divider()

        # A) Session Summary
        st.subheader("Session Summary")
        if st.session_state.df is not None:
            st.caption(
                f"{t('rows', lang)}: {len(st.session_state.df)}, {t('columns', lang)}: {len(st.session_state.df.columns)}"
            )
            st.caption(f"{t('missing_rate', lang)}: {st.session_state.missing_rate:.1%}")
        else:
            st.caption("No data loaded")

        # Analysis ID
        analysis_id = get_analysis_id_from_state(
            st.session_state.schema_obj,
            st.session_state.model_spec_obj,
            st.session_state.results_json,
        )
        if analysis_id:
            st.caption(f"ID: {analysis_id}")

        # Status
        status = "Not run"
        if st.session_state.results_json:
            s_val = st.session_state.results_json.get("status")
            status = "Success" if s_val == "success" else "Failed"
        st.caption(f"Status: {status}")

        from hygeia_graph.ui_flow import clear_all_state
        from hygeia_graph.ui_copy import EPHEMERAL_NOTICE

        st.caption(EPHEMERAL_NOTICE)

        if st.button("🗑️ Clear all data & cache", type="secondary"):
            removed = clear_all_state(st.session_state)
            st.session_state["nav_selection"] = "Data & Schema"
            st.success(f"✅ Cleared {len(removed)} items. No data retained.")
            st.rerun()

        st.divider()

        # Environment Status Panel
        st.subheader("🔧 Environment")
        from hygeia_graph.diagnostics import (
            REQUIRED_PACKAGES,
            build_diagnostics_report,
            check_r_packages,
            check_rscript,
            diagnostics_to_json,
        )

        if "env_check_cache" not in st.session_state:
            r_check = check_rscript()
            pkg_check = check_r_packages(REQUIRED_PACKAGES) if r_check["ok"] else None
            st.session_state.env_check_cache = {
                "rscript": r_check,
                "packages": pkg_check,
            }

        r_status = st.session_state.env_check_cache["rscript"]
        pkg_status = st.session_state.env_check_cache.get("packages")

        if r_status["ok"]:
            st.caption("✅ Rscript: OK")
        else:
            st.caption("❌ Rscript: Not found")

        if pkg_status:
            if pkg_status["ok"]:
                st.caption("✅ Core packages: OK")
            else:
                st.caption(f"⚠️ Missing: {', '.join(pkg_status['missing'])}")
        elif not r_status["ok"]:
            st.caption("⚠️ Cannot check packages")

        if st.button("📥 Download diagnostics.json", key="diag_dl"):
            report = build_diagnostics_report(
                df=st.session_state.df,
                guardrail_triggers=st.session_state.get("guardrail_warnings", []),
            )
            st.download_button(
                "Download",
                diagnostics_to_json(report),
                "diagnostics.json",
                "application/json",
                key="diag_dl_actual",
            )

        st.divider()

        # B) Navigation
        st.subheader("Navigation")
        
        # Define Page Groups
        nav_options_core = {
            "Introduction": t("nav_intro", lang),
            "Data & Schema": t("nav_data_upload", lang),
            "Model Settings": t("model_settings", lang),
            "Run MGM": t("run_mgm", lang),
            "Explore": t("interactive_network", lang),
            "Report & Export": t("nav_publication", lang),
        }
        
        nav_options_advanced = {
            "Preprocessing": t("nav_preprocess", lang),
            "Robustness": t("nav_robustness", lang),
            "Comparison": t("nav_comparison", lang),
            "Simulation": t("nav_simulation", lang),
        }

        # Combine all for selection map
        full_nav_map = {**nav_options_core, **nav_options_advanced}
        
        # Display logic - we can stick to a single radio for simplicity or grouped
        # st.radio doesn't support groups nicely. Let's list them in order.
        
        nav_order = [
            "Introduction",
            "Data & Schema",
            "Preprocessing",  # Moved here as requested (Branch point)
            "Model Settings",
            "Run MGM",
            "Explore",
            "Robustness",
            "Comparison",
            "Simulation",
            "Report & Export",
        ]
        
        nav_labels = [full_nav_map[k] for k in nav_order]
        
        # Default index
        curr_sel = st.session_state.get("nav_selection", "Introduction")
        if curr_sel not in nav_order:
            curr_sel = "Introduction"
            
        nav_idx = nav_order.index(curr_sel)
        
        sel_label = st.radio("Go to:", nav_labels, index=nav_idx)
        
        # Reverse map label to key
        # Use simple zip lookup since labels might be localized and distinct
        sel_key = nav_order[nav_labels.index(sel_label)]
        
        st.session_state["nav_selection"] = sel_key
        nav_selection = sel_key

        st.divider()

        # C) Explore Controls (Only visible on Explore page)
        explore_cfg = {}
        config_hash_val = ""

        if nav_selection == "Explore":
            st.subheader("Explore Controls")

            if "explore_config_cache" not in st.session_state:
                st.session_state.explore_config_cache = get_default_explore_config(
                    st.session_state.results_json
                )

            max_abs = 0.0
            if st.session_state.results_json and st.session_state.results_json.get("edges"):
                max_abs = max(
                    abs(e.get("weight", 0)) for e in st.session_state.results_json["edges"]
                )

            thresh = st.slider(
                t("edge_threshold", lang),
                0.0,
                float(max_abs) if max_abs > 0 else 1.0,
                float(st.session_state.explore_config_cache["threshold"]),
                step=0.01,
            )
            abs_w = st.checkbox(
                t("help_centrality_abs", lang),
                value=st.session_state.explore_config_cache["use_absolute_weights"],
            )
            top_n = st.selectbox(
                "Top edges to render",
                options=[200, 500, 1000, "All"],
                index=[200, 500, 1000, "All"].index(
                    st.session_state.explore_config_cache["top_edges"]
                ),
            )
            labels = st.checkbox(
                "Show labels", value=st.session_state.explore_config_cache["show_labels"]
            )
            phys = st.checkbox("Physics", value=st.session_state.explore_config_cache["physics"])

            from hygeia_graph.ui_state import can_enable_communities, can_enable_predictability

            r_posthoc = st.session_state.get("r_posthoc_json")
            has_pred = can_enable_predictability(r_posthoc)
            has_comm = can_enable_communities(r_posthoc)

            st.caption("Analysis Modules")
            st.checkbox("Strength (Abs)", value=True, disabled=True)
            st.checkbox(
                "Predictability", value=has_pred, disabled=not has_pred, help="Requires R posthoc"
            )
            st.checkbox(
                "Community detection",
                value=has_comm,
                disabled=not has_comm,
                help="Requires R posthoc",
            )

            cfg_raw = {
                "threshold": thresh,
                "use_absolute_weights": abs_w,
                "top_edges": top_n,
                "show_labels": labels,
                "physics": phys,
            }
            st.session_state.explore_config_cache = cfg_raw
            explore_cfg = normalize_explore_config(cfg_raw, st.session_state.results_json)
            config_hash_val = explore_config_hash(explore_cfg, analysis_id or "unknown")

            col_run, col_cache = st.columns([2, 1])
            run_btn = col_run.button(
                "Run selected analyses", type="primary", use_container_width=True
            )

            if run_btn:
                with st.spinner("Computing..."):
                    artifacts = compute_explore_artifacts(
                        st.session_state, lang, explore_cfg, analysis_id
                    )
                    if artifacts:
                        set_cached_outputs(
                            st.session_state, analysis_id, config_hash_val, artifacts
                        )
                        st.success("Updated!")
                    else:
                        st.error("Failed to compute artifacts.")
            
            if st.button("Clear derived cache"):
                clear_analysis_cache(st.session_state, analysis_id or "unknown")
                st.success("Cache cleared.")


    # ---------------------------------------------------------
    # MAIN AREA
    # ---------------------------------------------------------
    
    # Validation flags
    valid_schema = st.session_state.schema_valid
    valid_spec = st.session_state.model_spec_valid
    run_success = (
        st.session_state.results_json is not None
        and st.session_state.results_json.get("status") == "success"
    )
    missing_ok = st.session_state.missing_rate == 0
    LOCKED_MSG = "🔒 This page is locked. Please complete prior steps in order."

    # Router
    if nav_selection == "Introduction":
        render_introduction_page(lang)

    elif nav_selection == "Data & Schema":
        render_data_schema_page(lang)
        
    elif nav_selection == "Preprocessing":
        # Accessible if Schema is ready
        if not valid_schema:
             st.info("💡 Please upload data and generate schema first.")
        render_preprocessing_page(lang)

    elif nav_selection == "Model Settings":
        if not valid_schema:
            st.warning(LOCKED_MSG)
        else:
            render_model_settings_page(lang)

    elif nav_selection == "Run MGM":
        if not (valid_schema and valid_spec and missing_ok):
            st.warning(LOCKED_MSG)
            st.info("Checklist: Is Schema valid? Is Model Spec built? No missing data?")
        else:
            render_run_mgm_page(lang)

    elif nav_selection == "Explore":
        if not run_success:
            st.warning("🔒 Explore is locked. Run MGM successfully first.")
        else:
            render_explore_page(lang, analysis_id or "unknown", config_hash_val)

    elif nav_selection == "Robustness":
        render_robustness_page(lang, analysis_id or "unknown", config_hash_val)

    elif nav_selection == "Comparison":
        st.header(t("nav_comparison", lang))
        st.info("🚧 Module coming soon (Sprint B Agent M/K integration).")
        
    elif nav_selection == "Simulation":
        render_simulation_page(
            lang, st.session_state.get("analysis_id"), st.session_state.get("config_hash")
        )

    elif nav_selection == "Report & Export":
        if st.session_state.schema_obj or st.session_state.results_json:
            render_report_page(lang, analysis_id or "unknown", config_hash_val)
        else:
            st.warning("No analyses to report yet.")
    
    else:
        st.error(f"Unknown page: {nav_selection}")


if __name__ == "__main__":
    main()
