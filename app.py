"""Hygeia Graph - Streamlit Application (Sprint A)."""

import streamlit as st

from hygeia_graph.i18n import LANGUAGES
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

    # Language selector (Top of sidebar? or just before nav)
    # Keeping minimal as requested
    if "lang" not in st.session_state:
        st.session_state.lang = "en"

    # ---------------------------------------------------------
    # SIDEBAR: Control Tower
    # ---------------------------------------------------------
    with st.sidebar:
        st.title("Hygeia-Graph")

        # Language
        lang_options = list(LANGUAGES.keys())
        idx = lang_options.index(st.session_state.lang)
        sel_lang = st.selectbox(
            "🌐 Language", options=lang_options, format_func=lambda x: LANGUAGES[x], index=idx
        )
        st.session_state.lang = sel_lang
        lang = st.session_state.lang

        st.divider()

        # A) Session Summary
        st.subheader("Session Summary")
        if st.session_state.df is not None:
            st.caption(
                f"Rows: {len(st.session_state.df)}, Cols: {len(st.session_state.df.columns)}"
            )
            st.caption(f"Missing: {st.session_state.missing_rate:.1%}")
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

        # Cache check results in session to avoid repeated subprocess calls
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

        # Diagnostics download
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
        # Options
        nav_map = {
            "Data & Schema": "Data & Schema",
            "Model Settings": "Model Settings",
            "Run MGM": "Run MGM",
            "Explore": "Explore",
            "Robustness": "Robustness",
            "Comparison": "Comparison (Coming Soon)",
            "Simulation": "Simulation (Experimental)",
            "Preprocessing": "Preprocessing",
            "Report & Export": "Report & Export",
        }

        # Gating logic
        valid_schema = st.session_state.schema_valid
        valid_spec = st.session_state.model_spec_valid
        run_success = (
            st.session_state.results_json is not None
            and st.session_state.results_json.get("status") == "success"
        )
        missing_ok = st.session_state.missing_rate == 0

        # Determine accessible pages (visual cue only, or strict blocking?)
        # Spec says "Behavior: Only show content... Gating: ..."
        # I'll rely on radio logic but maybe filter options?
        # Better: keep options but show disabled or redirect if selected?
        # Radio doesn't support disabling individual options easily.
        # I will check selection in main area and show "Locked".

        nav_selection = st.radio("Navigation", list(nav_map.keys()))

        st.divider()

        # C) Explore Controls
        explore_cfg = {}
        config_hash_val = ""

        if nav_selection == "Explore" and run_success:
            st.subheader("Explore Controls")

            # Defaults
            if "explore_config_cache" not in st.session_state:
                st.session_state.explore_config_cache = get_default_explore_config(
                    st.session_state.results_json
                )

            # Compute max weight
            max_abs = 0.0
            if st.session_state.results_json.get("edges"):
                max_abs = max(
                    abs(e.get("weight", 0)) for e in st.session_state.results_json["edges"]
                )

            # Controls
            thresh = st.slider(
                "Edge threshold",
                0.0,
                float(max_abs),
                float(st.session_state.explore_config_cache["threshold"]),
                step=0.01,
            )
            abs_w = st.checkbox(
                "Use absolute weights",
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

            # Module selection
            r_posthoc = st.session_state.get("r_posthoc_json")
            has_pred = can_enable_predictability(r_posthoc)
            has_comm = can_enable_communities(r_posthoc)

            st.caption("Analysis Modules")
            st.checkbox("Strength (Abs)", value=True, disabled=True)
            st.checkbox(
                "Expected Influence", value=True, disabled=True, help="Always computed (Sprint B)"
            )
            st.checkbox(
                "Predictability", value=has_pred, disabled=not has_pred, help="Requires R posthoc"
            )
            st.checkbox(
                "Community detection",
                value=has_comm,
                disabled=not has_comm,
                help="Requires R posthoc",
            )

            # Run Button
            cfg_raw = {
                "threshold": thresh,
                "use_absolute_weights": abs_w,
                "top_edges": top_n,
                "show_labels": labels,
                "physics": phys,
            }
            # Update cache var for persistence
            st.session_state.explore_config_cache = cfg_raw

            # Normalize config
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
                    else:
                        st.error("Failed to compute artifacts.")

            if st.button("Clear derived cache"):
                clear_analysis_cache(st.session_state, analysis_id or "unknown")
                st.success("Cache cleared.")

    # ---------------------------------------------------------
    # MAIN AREA
    # ---------------------------------------------------------

    # Gating Check
    LOCKED_MSG = "🔒 This page is locked. Please complete previous steps."

    if nav_selection == "Data & Schema":
        render_data_schema_page(lang)

    elif nav_selection == "Model Settings":
        if not valid_schema:
            st.warning(LOCKED_MSG)
        else:
            render_model_settings_page(lang)

    elif nav_selection == "Run MGM":
        if not (valid_schema and valid_spec and missing_ok):
            st.warning(LOCKED_MSG)
            st.info("Checklist: Data Clean? Schema Valid? Model Spec Valid?")
        else:
            render_run_mgm_page(lang)

    elif nav_selection == "Explore":
        if not run_success:
            st.warning("🔒 Explore is locked. Run MGM successfully first.")
        else:
            render_explore_page(lang, analysis_id or "unknown", config_hash_val)

    elif nav_selection == "Robustness":
        # Check if R available (optional benefit)
        render_robustness_page(lang, analysis_id or "unknown", config_hash_val)

    elif nav_selection == "Report & Export":
        # Accessible if any artifact exists
        if st.session_state.schema_obj or st.session_state.results_json:
            render_report_page(lang, analysis_id or "unknown", config_hash_val)
        else:
            st.warning(LOCKED_MSG)

    elif nav_selection == "Simulation":
        # Pass explore config hash if available
        render_simulation_page(
            lang, st.session_state.get("analysis_id"), st.session_state.get("config_hash")
        )

    elif nav_selection == "Preprocessing":
        render_preprocessing_page(lang)

    else:
        # Placeholders
        st.header(nav_map[nav_selection])
        st.info("🚧 Coming soon in future sprints.")


if __name__ == "__main__":
    main()
