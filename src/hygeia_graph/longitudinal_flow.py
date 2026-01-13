"""Longitudinal Flow Analysis (V2 Feature).

Detects paired longitudinal variables (T1→T2) and builds
transition tables for Sankey/Alluvial visualization.
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Default suffix pairs to detect
DEFAULT_SUFFIX_PAIRS = [("_T1", "_T2"), ("_t1", "_t2"), ("T1", "T2"), ("_pre", "_post")]


def detect_longitudinal_pairs(
    df: pd.DataFrame,
    *,
    suffix_pairs: Optional[List[Tuple[str, str]]] = None,
) -> List[Dict[str, str]]:
    """Detect longitudinal paired columns in a DataFrame.

    Args:
        df: Input DataFrame.
        suffix_pairs: List of (T1_suffix, T2_suffix) tuples to search for.

    Returns:
        List of detected pairs: [{"base": str, "t1": str, "t2": str}, ...]
    """
    if suffix_pairs is None:
        suffix_pairs = DEFAULT_SUFFIX_PAIRS

    columns = set(df.columns)
    pairs_by_scheme = {}

    for t1_suffix, t2_suffix in suffix_pairs:
        pairs = []
        for col in df.columns:
            if col.endswith(t1_suffix):
                base = col[: -len(t1_suffix)]
                t2_col = base + t2_suffix
                if t2_col in columns:
                    pairs.append({"base": base, "t1": col, "t2": t2_col})

        if pairs:
            pairs_by_scheme[(t1_suffix, t2_suffix)] = pairs

    if not pairs_by_scheme:
        return []

    # Pick the scheme with the most pairs
    best_scheme = max(pairs_by_scheme, key=lambda k: len(pairs_by_scheme[k]))
    return pairs_by_scheme[best_scheme]


def validate_pair_data(
    df: pd.DataFrame,
    pair: Dict[str, str],
    *,
    max_unique: int = 30,
) -> Dict[str, Any]:
    """Validate that a pair is suitable for flow analysis.

    Args:
        df: Input DataFrame.
        pair: Dictionary with "t1" and "t2" column names.
        max_unique: Maximum unique values for categorical treatment.

    Returns:
        Validation result with "ok", "warnings", and counts.
    """
    t1_col = pair["t1"]
    t2_col = pair["t2"]

    warnings = []

    # Check columns exist
    for col in [t1_col, t2_col]:
        if col not in df.columns:
            return {
                "ok": False,
                "warnings": [f"Column '{col}' not found in data."],
                "n_unique_t1": 0,
                "n_unique_t2": 0,
            }

    n_unique_t1 = df[t1_col].nunique()
    n_unique_t2 = df[t2_col].nunique()

    if n_unique_t1 > max_unique:
        warnings.append(
            f"T1 column '{t1_col}' has {n_unique_t1} unique values (>{max_unique}). "
            "Consider discretizing."
        )

    if n_unique_t2 > max_unique:
        warnings.append(
            f"T2 column '{t2_col}' has {n_unique_t2} unique values (>{max_unique}). "
            "Consider discretizing."
        )

    return {
        "ok": len(warnings) == 0,
        "warnings": warnings,
        "n_unique_t1": n_unique_t1,
        "n_unique_t2": n_unique_t2,
    }


def build_transition_table(
    df: pd.DataFrame,
    t1_col: str,
    t2_col: str,
    *,
    drop_missing: bool = True,
) -> pd.DataFrame:
    """Build a transition count table from T1 to T2.

    Args:
        df: Input DataFrame.
        t1_col: Column name for T1 state.
        t2_col: Column name for T2 state.
        drop_missing: Whether to drop rows with missing values.

    Returns:
        DataFrame with columns: source, target, count.
    """
    subset = df[[t1_col, t2_col]].copy()

    if drop_missing:
        subset = subset.dropna()

    # Convert to string labels
    subset["source"] = subset[t1_col].astype(str)
    subset["target"] = subset[t2_col].astype(str)

    # Group and count
    counts = subset.groupby(["source", "target"]).size().reset_index(name="count")

    # Sort by count descending
    counts = counts.sort_values("count", ascending=False).reset_index(drop=True)

    return counts


def build_sankey_nodes_links(
    transitions_df: pd.DataFrame,
    *,
    t1_prefix: str = "T1: ",
    t2_prefix: str = "T2: ",
) -> Dict[str, Any]:
    """Build nodes and links for Sankey diagram.

    Args:
        transitions_df: Transition table with source, target, count columns.
        t1_prefix: Prefix for T1 node labels.
        t2_prefix: Prefix for T2 node labels.

    Returns:
        Dictionary with "nodes" and "links" for Plotly Sankey.
    """
    # Get unique sources and targets
    sources = transitions_df["source"].unique().tolist()
    targets = transitions_df["target"].unique().tolist()

    # Build node labels with time prefixes
    t1_labels = [t1_prefix + s for s in sources]
    t2_labels = [t2_prefix + t for t in targets]
    all_labels = t1_labels + t2_labels

    # Create label -> index mapping
    label_to_idx = {label: idx for idx, label in enumerate(all_labels)}

    # Build links
    source_indices = []
    target_indices = []
    values = []

    for _, row in transitions_df.iterrows():
        s_label = t1_prefix + row["source"]
        t_label = t2_prefix + row["target"]

        source_indices.append(label_to_idx[s_label])
        target_indices.append(label_to_idx[t_label])
        values.append(row["count"])

    return {
        "nodes": {"label": all_labels},
        "links": {
            "source": source_indices,
            "target": target_indices,
            "value": values,
        },
    }


def make_sankey_figure(
    nodes_links: Dict[str, Any],
    *,
    title: str = "Longitudinal Flow (T1 → T2)",
) -> Any:
    """Create a Plotly Sankey figure.

    Args:
        nodes_links: Output from build_sankey_nodes_links.
        title: Figure title.

    Returns:
        Plotly Figure object.
    """
    import plotly.graph_objects as go

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    label=nodes_links["nodes"]["label"],
                ),
                link=dict(
                    source=nodes_links["links"]["source"],
                    target=nodes_links["links"]["target"],
                    value=nodes_links["links"]["value"],
                ),
            )
        ]
    )

    fig.update_layout(title_text=title, font_size=12)

    return fig


def figure_to_html(fig: Any) -> str:
    """Convert Plotly figure to standalone HTML.

    Args:
        fig: Plotly Figure object.

    Returns:
        HTML string.
    """
    return fig.to_html(full_html=True, include_plotlyjs="cdn")


def figure_to_json(fig: Any) -> str:
    """Convert Plotly figure to JSON.

    Args:
        fig: Plotly Figure object.

    Returns:
        JSON string.
    """
    return fig.to_json()
