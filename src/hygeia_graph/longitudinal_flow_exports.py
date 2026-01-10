"""Export utilities for Longitudinal Flow analysis."""

from pathlib import Path
from typing import Any

import pandas as pd


def export_transitions_csv(transitions_df: pd.DataFrame, path: Path) -> None:
    """Export transition table to CSV.

    Args:
        transitions_df: Transition DataFrame with source, target, count.
        path: Output file path.
    """
    transitions_df.to_csv(path, index=False)


def export_sankey_html(fig: Any, path: Path) -> None:
    """Export Sankey figure to standalone HTML.

    Args:
        fig: Plotly Figure object.
        path: Output file path.
    """
    html_content = fig.to_html(full_html=True, include_plotlyjs="cdn")
    path.write_text(html_content, encoding="utf-8")


def export_sankey_json(fig: Any, path: Path) -> None:
    """Export Sankey figure to JSON.

    Args:
        fig: Plotly Figure object.
        path: Output file path.
    """
    json_content = fig.to_json()
    path.write_text(json_content, encoding="utf-8")
