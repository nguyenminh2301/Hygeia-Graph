"""ZIP export builder for Temporal outputs."""

import io
import json
import zipfile
from typing import Any, Dict

import pandas as pd


def build_temporal_zip(
    meta: Dict[str, Any],
    tables: Dict[str, pd.DataFrame],
    figures_html: Dict[str, str] = None
) -> bytes:
    """
    Build in-memory ZIP for temporal analysis outputs.
    
    Structure:
    /temporal/
      meta.json
      tables/
        PDC.csv
        PCC.csv
        temporal_edges.csv
        contemporaneous_edges.csv
      figures/
        network_temporal.html
        network_contemporaneous.html
    """
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write Meta
        if meta:
            zf.writestr(
                "temporal/meta.json",
                json.dumps(meta, indent=2)
            )

        # Write Tables
        if tables:
            for name, df in tables.items():
                if df is not None:
                    csv_data = df.to_csv(index=False if "edges" in name else True)
                    zf.writestr(f"temporal/tables/{name}.csv", csv_data)

        # Write Figures (HTML strings)
        if figures_html:
            for name, html_content in figures_html.items():
                zf.writestr(f"temporal/figures/{name}.html", html_content)

    buffer.seek(0)
    return buffer.getvalue()
