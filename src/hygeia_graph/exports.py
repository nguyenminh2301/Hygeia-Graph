"""Export utilities for Hygeia-Graph.

This module provides helper functions to convert data structures (DataFrames,
dicts, plots) into bytes for download in the Streamlit UI.
"""

import json
from typing import Any

import pandas as pd


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame to CSV bytes (UTF-8).

    Args:
        df: The pandas DataFrame to convert.

    Returns:
        Bytes object containing the CSV data.
    """
    return df.to_csv(index=False).encode("utf-8")


def df_to_csv_bytes_with_index(df: pd.DataFrame) -> bytes:
    """Convert a DataFrame to CSV bytes including the index (UTF-8).

    Useful for adjacency matrices where the index matters.

    Args:
        df: The pandas DataFrame to convert.

    Returns:
        Bytes object containing the CSV data.
    """
    return df.to_csv(index=True).encode("utf-8")


def json_to_bytes(obj: dict[str, Any]) -> bytes:
    """Convert a dictionary to pretty-printed JSON bytes (UTF-8).

    Args:
        obj: The dictionary object.

    Returns:
        Bytes object containing the JSON data.
    """
    return json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")


def plot_to_html_bytes(plot_obj: Any) -> bytes:
    """Convert a Plotly figure to HTML bytes.

    Args:
        plot_obj: A plotly.graph_objects.Figure object.

    Returns:
        Bytes object containing the HTML representation.
    """
    # Assuming Plotly figure. to_html returns a string.
    # include_plotlyjs="cdn" ensures the plot is standalone but loads JS from CDN.
    # full_html=True makes it a complete page.
    if hasattr(plot_obj, "to_html"):
        html_str = plot_obj.to_html(full_html=True, include_plotlyjs="cdn")
        return html_str.encode("utf-8")
    return b""
