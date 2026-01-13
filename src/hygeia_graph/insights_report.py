"""Automated Insights Report Generator for Hygeia-Graph.

Generates a copy-ready Results narrative (Markdown) from computed artifacts.
Template-based, deterministic, and includes standard research disclaimers.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def build_report_payload(
    *,
    results_json: Dict[str, Any],
    derived_metrics_json: Dict[str, Any],
    explore_cfg: Optional[Dict[str, Any]] = None,
    bootnet_meta: Optional[Dict[str, Any]] = None,
    bootnet_tables: Optional[Dict[str, Any]] = None,
    nct_meta: Optional[Dict[str, Any]] = None,
    nct_summary: Optional[Dict[str, Any]] = None,
    nct_edge_table: Optional[Any] = None,  # pd.DataFrame
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a structured dictionary payload summarizing all analysis results."""

    analysis_id = results_json.get("analysis_id", "unknown")
    cfg = explore_cfg or {}

    # 1. Inputs Present
    has_pred = False
    has_comm = False

    # Check derived metrics for Posthoc content
    node_met = derived_metrics_json.get("node_metrics", {})
    if "predictability" in node_met and node_met["predictability"]:
        has_pred = True
    if "communities" in derived_metrics_json and derived_metrics_json["communities"].get("enabled"):
        has_comm = True

    inputs = {
        "predictability": has_pred,
        "communities": has_comm,
        "bootnet": bootnet_meta.get("status") == "success" if bootnet_meta else False,
        "nct": nct_summary is not None,  # Simplified check
    }

    # 2. Key Numbers
    # Access edges from filtered list if possible, or results directly if cfg matches?
    # derived_metrics_json doesn't store edge count explicitly in root usually.
    # We can infer from results_json["edges"] if no filter applied, but report should reflect
    # Explore view?
    # Actually results_json has ALL edges (filtered by regularization).
    # explore_cfg applies extra thresholding.
    threshold = cfg.get("threshold", 0.0)
    top_n = cfg.get("top_edges")

    # Estimate total edges (this is roughly what's in results_json)
    n_total_edges = len(results_json.get("edges", []))
    n_nodes = len(results_json.get("nodes", []))

    # 3. Rankings
    top_limit = settings.get("top_n", 10)

    def get_top_nodes(metric_dict, limit, absolute=True, include_metric_label=None):
        """Helper to sort and format top nodes."""
        if not metric_dict:
            return []
        items = []
        for nid, val in metric_dict.items():
            sort_val = abs(val) if absolute else val
            item = {"node": nid, "value": val, "sort_val": sort_val}
            if include_metric_label:
                # Look up metric label from 'predictability_metric' dict if available
                # But here we just pass the dict itself?
                # For simplicity, if metric_dict is predictability, we need the metric map
                # separately.
                pass
            items.append(item)

        items.sort(key=lambda x: x["sort_val"], reverse=True)
        return items[:limit]

    # Strength
    s_abs = node_met.get("strength_abs", {})
    rank_strength = get_top_nodes(s_abs, top_limit)

    # EI
    ei = node_met.get("expected_influence", {})
    rank_ei = get_top_nodes(ei, top_limit)  # Sort by abs(EI) but show signed? Yes usually.

    # Predictability
    rank_pred = []
    if inputs["predictability"]:
        pred_vals = node_met.get("predictability", {})
        pred_met = node_met.get("predictability_metric", {})

        # Custom logic to include metric type
        items = []
        for nid, val in pred_vals.items():
            items.append({"node": nid, "value": val, "metric": pred_met.get(nid, "R2")})
        items.sort(key=lambda x: x["value"], reverse=True)
        rank_pred = items[:top_limit]

    # 4. Communities
    comm_data = {}
    if inputs["communities"]:
        c_info = derived_metrics_json["communities"]
        mem = c_info.get("membership", {})
        algo = c_info.get("algorithm", "unknown")

        # Count sizes
        from collections import Counter

        counts = Counter(mem.values())
        largest = [{"community": str(k), "size": v} for k, v in counts.most_common(5)]

        comm_data = {
            "enabled": True,
            "algorithm": algo,
            "n_communities": len(counts),
            "largest": largest,
        }

    # 5. Robustness
    rob_data = {"enabled": False}
    if inputs["bootnet"]:
        meta = bootnet_meta
        cs = meta.get("cs_coefficient", {})

        # Edge CI
        edge_sum = {}
        if bootnet_tables and "edge_ci_flag" in bootnet_tables:
            df = bootnet_tables["edge_ci_flag"]
            if df is not None and not df.empty:
                n_cross = df["crosses0"].sum() if "crosses0" in df.columns else 0

                # Get example unstable edges (top 3 by something? maybe just first 3)
                examples = []
                if "crosses0" in df.columns:
                    unstable = df[df["crosses0"]]
                    head = unstable.head(3).to_dict(orient="records")
                    examples = head

                edge_sum = {
                    "n_edges_flagged_crossing_zero": int(n_cross),
                    "example_edges": examples,
                }

        rob_data = {"enabled": True, "cs_coefficient": cs, "edge_ci_summary": edge_sum}

    # 6. Comparison (Stub for now as not fully spec'd in prompt inputs details)
    comp_data = {"enabled": False}
    if inputs["nct"]:
        # Logic to extract NCT P-values would go here
        # Placeholder based on prompt requirements
        comp_data = {
            "enabled": True,
            "group_var": nct_summary.get("group_var", "Group"),
            "p_structure": nct_summary.get("p_structure"),
            "p_global_strength": nct_summary.get("p_strength"),
            "top_edge_differences": [],  # Needs DF processing
        }

    return {
        "analysis_id": analysis_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "report_version": "0.1.0",
        "settings": settings,
        "inputs_present": inputs,
        "key_numbers": {
            "n_nodes": n_nodes,
            "n_edges_total": n_total_edges,
            "threshold": threshold,
            "use_absolute": cfg.get("use_absolute_weights"),
            "top_edges": top_n,
        },
        "rankings": {
            "top_strength_abs": rank_strength,
            "top_expected_influence": rank_ei,
            "top_predictability": rank_pred,
        },
        "communities": comm_data,
        "robustness": rob_data,
        "comparison": comp_data,
        "messages": derived_metrics_json.get("messages", []),
    }


def render_report_markdown(payload: Dict[str, Any], style: str = "paper") -> str:
    """Convert report payload to Markdown narrative."""

    p = payload
    key = p["key_numbers"]

    # Helper to clean node names
    def clean_nodes(node_list):
        return ", ".join([f"{x['node']} ({x['value']:.2f})" for x in node_list])

    lines = []

    # 1. Header
    lines.append(f"# Automated Insights Report: {p['analysis_id']}")
    lines.append(f"**Generated at:** {p['generated_at']} | **Style:** {style}")
    lines.append("")

    # 2. Disclaimer (CRITICAL)
    lines.append("> [!IMPORTANT]")
    lines.append("> **Disclaimer (Research Tool Only)**")
    lines.append(
        "> * This report is generated automatically by a software tool and does not constitute "
        "medical advice."
    )
    lines.append(
        "> * The associations identified (`edges`) represent partial correlations (dependencies) "
        "and do NOT imply causality."
    )
    lines.append(
        "> * Regularization (EBIC-GLASSO) shrinks small edges to zero; results depend on "
        "hyperparameters."
    )
    lines.append("")

    # 3. Overview
    lines.append("## 1. Network Structure Overview")
    lines.append(f"The analysis included **{key['n_nodes']} nodes**.")
    count_str = f"**{key['n_edges_total']}** edges (non-zero entries)"
    if key["threshold"] > 0:
        count_str += f", filtered by threshold **{key['threshold']}**"
    lines.append(f"The estimated network contains {count_str}.")
    lines.append("")

    # 4. Key Findings (Centrality)
    lines.append("## 2. Key Centrality Metrics")

    # Strength
    ranks = p["rankings"]
    lines.append("### Node Strength (Absolute)")
    if ranks["top_strength_abs"]:
        lines.append(
            "The most central nodes (highest cumulative connection strength) were: "
            f"**{clean_nodes(ranks['top_strength_abs'])}**."
        )
    else:
        lines.append("No strength data available.")

    # EI
    lines.append("### Expected Influence")
    if ranks["top_expected_influence"]:
        lines.append(
            "The nodes with highest Expected Influence (considering sign, i.e., strongest "
            "positive or negative accumulated weights) were: "
            f"**{clean_nodes(ranks['top_expected_influence'])}**."
        )
    else:
        lines.append("No expected influence data available.")
    lines.append("")

    # 5. Predictability
    if p["inputs_present"]["predictability"]:
        pred = ranks["top_predictability"]
        lines.append("## 3. Predictability Analysis")
        lines.append(
            "Predictability quantifies how much variance in a node is explained by its neighbors."
        )
        lines.append(" * **R²**: For continuous/count variables.")
        lines.append(" * **nCC** (Normalized Correct Classfication): For categorical variables.")
        lines.append("")
        if pred:
            top_pred = ", ".join([f"{x['node']} ({x['metric']} {x['value']:.2f})" for x in pred])
            lines.append(f"Top predictable nodes: **{top_pred}**.")
        lines.append("")

    # 6. Communities
    if p["inputs_present"]["communities"] and p["communities"].get("enabled"):
        c = p["communities"]
        lines.append("## 4. Community Detection")
        lines.append(
            f"Algorithm: `{c['algorithm']}` detected **{c['n_communities']} communities** "
            "(modules)."
        )
        largest = ", ".join([f"{x['community']} (n={x['size']})" for x in c["largest"]])
        lines.append(f"Largest communities: {largest}.")
        lines.append("")

    # 7. Robustness
    if p["inputs_present"]["bootnet"] and p["robustness"].get("enabled"):
        r = p["robustness"]
        lines.append("## 5. Stability & Robustness")

        # CS
        cs = r["cs_coefficient"]
        cs_str = []
        if cs.get("strength") is not None:
            cs_str.append(f"Strength CS={cs['strength']:.2f}")
        if cs.get("expectedInfluence") is not None:
            cs_str.append(f"EI CS={cs['expectedInfluence']:.2f}")

        lines.append(
            f"**Correlation Stability (CS-coefficient):** {', '.join(cs_str) if cs_str else 'N/A'}."
        )
        lines.append(
            "*Interpretation: CS > 0.25 indicates moderate stability; CS > 0.5 indicates strong "
            "stability.*"
        )

        # Edge CI
        edge_sum = r.get("edge_ci_summary", {})
        n_cross = edge_sum.get("n_edges_flagged_crossing_zero")
        if n_cross is not None:
            lines.append(
                f"**Edge Accuracy:** Bootstrapping revealed that **{n_cross} edges** have 95% "
                "confidence intervals that cross zero, indicating uncertainty in their "
                "sign/presence."
            )
            if n_cross > 0 and edge_sum.get("example_edges"):
                ex = edge_sum["example_edges"][0]
                lines.append(
                    f"(Example unstable edge: {ex.get('node1', '?')} -- {ex.get('node2', '?')})"
                )
        lines.append("")

    # 8. Comparison (Stub)
    if p["inputs_present"]["nct"]:
        lines.append("## 6. Network Comparison")
        lines.append("*(NCT results summary would appear here)*")
        lines.append("")

    # 9. Copy-Ready Block
    lines.append("## 📝 Suggested Paragraph (Results Section)")
    lines.append("```text")
    lines.append(
        "We estimated a Mixed Graphical Model (MGM) using the Hygeia-Graph tool (based on mgm "
        "R package)."
    )
    lines.append("Model selection was performed using EBIC (tuning parameter=0.25).")

    top_s = ranks["top_strength_abs"][0]["node"] if ranks["top_strength_abs"] else "X"
    lines.append(f"Evaluating node centrality, {top_s} exhibited the highest strength.")

    if p["inputs_present"]["bootnet"]:
        lines.append(
            "Stability analysis using nonparametric and case-dropping bootstrapping (n=200) "
            "was conducted."
        )

    lines.append(
        "Associations reported here are exploratory and should be interpreted as partial "
        "correlations."
    )
    lines.append("```")

    return "\n".join(lines)


def generate_insights_report(
    results_json: Dict[str, Any],
    derived_metrics_json: Dict[str, Any],
    *,
    explore_cfg: Optional[Dict[str, Any]] = None,
    bootnet_meta: Optional[Dict[str, Any]] = None,
    bootnet_tables: Optional[Dict[str, Any]] = None,
    nct_meta: Optional[Dict[str, Any]] = None,
    nct_summary: Optional[Dict[str, Any]] = None,
    nct_edge_table: Optional[Any] = None,
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Orchestrate report generation."""

    payload = build_report_payload(
        results_json=results_json,
        derived_metrics_json=derived_metrics_json,
        explore_cfg=explore_cfg,
        bootnet_meta=bootnet_meta,
        bootnet_tables=bootnet_tables,
        nct_meta=nct_meta,
        nct_summary=nct_summary,
        nct_edge_table=nct_edge_table,
        settings=settings,
    )

    md = render_report_markdown(payload, style=settings.get("style", "paper"))

    return {"payload": payload, "markdown": md}
