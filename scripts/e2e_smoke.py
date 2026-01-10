#!/usr/bin/env python
"""E2E Smoke Test - Headless Pipeline Verification.

Usage:
    python scripts/e2e_smoke.py [--skip-r] [--fast]

Options:
    --skip-r    Skip R-dependent steps (MGM, posthoc, publication pack)
    --fast      Use minimal bootstraps/permutations for R tests

Exit Code:
    0 = PASS
    1 = FAIL
"""

import argparse
import sys
import traceback
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def log(msg: str, level: str = "INFO"):
    """Simple logger."""
    print(f"[{level}] {msg}")


def run_smoke(skip_r: bool = False, fast: bool = False) -> bool:
    """Run full smoke test pipeline."""

    log("=" * 60)
    log("Hygeia-Graph E2E Smoke Test")
    log("=" * 60)

    # Step 1: Load Example Data
    log("Step 1: Loading example data...")
    try:
        from hygeia_graph.data_processor import infer_variables, load_csv, profile_df

        data_path = Path(__file__).parent.parent / "assets" / "example_data.csv"
        if not data_path.exists():
            log(f"FAIL: {data_path} not found", "ERROR")
            return False

        with open(data_path, "r") as f:
            df = load_csv(f)

        log(f"  Loaded {len(df)} rows, {len(df.columns)} columns")

        profile = profile_df(df)
        missing_rate = profile["missing"]["rate"]
        log(f"  Missing rate: {missing_rate:.2%}")

        if missing_rate > 0:
            log("  WARNING: Missing values detected. MGM will fail.", "WARN")

    except Exception as e:
        log(f"FAIL: {e}", "ERROR")
        traceback.print_exc()
        return False

    # Step 2: Infer Variables and Build Schema
    log("Step 2: Building schema...")
    try:
        from hygeia_graph.contracts import validate_schema_json
        from hygeia_graph.data_processor import build_schema_json

        variables = infer_variables(df)
        schema_json = build_schema_json(df, variables)
        validate_schema_json(schema_json)

        log(f"  Schema valid with {len(schema_json['variables'])} variables")

    except Exception as e:
        log(f"FAIL: {e}", "ERROR")
        traceback.print_exc()
        return False

    # Step 3: Build Model Spec
    log("Step 3: Building model spec...")
    try:
        from hygeia_graph.contracts import validate_model_spec_json
        from hygeia_graph.model_spec import build_model_spec, default_model_settings

        settings = default_model_settings()
        settings["random_seed"] = 42  # Deterministic

        model_spec = build_model_spec(schema_json, settings)
        validate_model_spec_json(model_spec)

        log("  Model spec valid")

    except Exception as e:
        log(f"FAIL: {e}", "ERROR")
        traceback.print_exc()
        return False

    # Step 4: Run MGM (R-dependent)
    results_json = None
    r_posthoc = None

    if skip_r:
        log("Step 4: SKIP (--skip-r)", "WARN")
    else:
        log("Step 4: Running MGM via R subprocess...")
        try:
            from hygeia_graph.r_interface import run_mgm_subprocess

            res = run_mgm_subprocess(
                df=df,
                schema_json=schema_json,
                model_spec_json=model_spec,
                timeout_sec=300,
                quiet=True,
                compute_r_posthoc=True,
            )

            results_json = res["results"]
            r_posthoc = res.get("r_posthoc")

            # Validate
            from hygeia_graph.contracts import validate_results_json

            validate_results_json(results_json)

            n_edges = len(results_json.get("edges", []))
            log(f"  MGM success: {n_edges} edges")

            if r_posthoc:
                log("  R posthoc computed (predictability + communities)")

        except Exception as e:
            log(f"FAIL: {e}", "ERROR")
            traceback.print_exc()
            return False

    # Step 5: Derived Metrics
    if results_json:
        log("Step 5: Computing derived metrics...")
        try:
            from hygeia_graph.posthoc_merge import merge_r_posthoc_into_derived
            from hygeia_graph.posthoc_metrics import build_derived_metrics

            config = {"threshold": 0.0, "top_edges": None, "use_absolute_weights": True}
            derived = build_derived_metrics(results_json, config)

            if r_posthoc:
                derived = merge_r_posthoc_into_derived(derived, r_posthoc)

            log("  Derived metrics computed")

        except Exception as e:
            log(f"FAIL: {e}", "ERROR")
            traceback.print_exc()
            return False
    else:
        log("Step 5: SKIP (no results)")
        derived = None

    # Step 6: Plots (Python-only)
    if results_json and derived:
        log("Step 6: Building plots...")
        try:
            from hygeia_graph.plots import build_node_metrics_df, compute_edges_filtered_df

            edges_df = compute_edges_filtered_df(
                results_json, {"threshold": 0.0, "top_edges": None, "use_absolute_weights": True}
            )
            centrality_df = build_node_metrics_df(derived)

            log(f"  Edges table: {len(edges_df)} rows")
            log(f"  Centrality table: {len(centrality_df)} rows")

        except Exception as e:
            log(f"FAIL: {e}", "ERROR")
            traceback.print_exc()
            return False
    else:
        log("Step 6: SKIP (no results)")

    # Step 7: Publication Pack (R-dependent)
    if not skip_r and results_json:
        log("Step 7: Generating Publication Pack...")
        try:
            from hygeia_graph.publication_pack_interface import run_publication_pack_subprocess

            pack_out = run_publication_pack_subprocess(
                results_json=results_json,
                schema_json=schema_json,
                derived_metrics_json=derived,
                threshold=0.1,
                top_edges=50,
                timeout_sec=180,
            )

            if pack_out["meta"]["status"] == "success":
                log("  Publication pack success")
            else:
                log(f"  Publication pack failed: {pack_out['meta'].get('messages')}", "WARN")

        except Exception as e:
            log(f"WARN: Publication pack error (non-fatal): {e}", "WARN")
    else:
        log("Step 7: SKIP")

    # Summary
    log("=" * 60)
    log("E2E SMOKE TEST PASSED", "SUCCESS")
    log("=" * 60)

    return True


def main():
    parser = argparse.ArgumentParser(description="Hygeia-Graph E2E Smoke Test")
    parser.add_argument("--skip-r", action="store_true", help="Skip R-dependent steps")
    parser.add_argument("--fast", action="store_true", help="Use minimal R params")

    args = parser.parse_args()

    success = run_smoke(skip_r=args.skip_r, fast=args.fast)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
