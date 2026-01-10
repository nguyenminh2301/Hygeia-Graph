"""Utilities for Publication Pack (Hashing, Zip)."""

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


def pack_settings_hash(settings: Dict[str, Any], analysis_id: str) -> str:
    """Deterministic hash for pack settings."""
    dump = json.dumps({"analysis_id": str(analysis_id), "settings": settings}, sort_keys=True)
    return hashlib.sha256(dump.encode("utf-8")).hexdigest()


def build_publication_zip(
    zip_path: Path,
    *,
    analysis_id: str,
    schema_json: Optional[Dict[str, Any]],
    model_spec_json: Optional[Dict[str, Any]],
    results_json: Dict[str, Any],
    derived_metrics_json: Optional[Dict[str, Any]],
    edges_df: Optional[pd.DataFrame],
    centrality_df: Optional[pd.DataFrame],
    # Pre-generated content from R
    pack_out_dir: Path,
) -> Path:
    """Create the publication ZIP bundle."""

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Meta (from R output)
        meta_src = pack_out_dir / "meta" / "publication_pack_meta.json"
        if meta_src.exists():
            zf.write(meta_src, "publication_pack/meta/publication_pack_meta.json")

        # 2. Artifacts
        def add_json(obj, name):
            if obj:
                s = json.dumps(obj, indent=2)
                zf.writestr(f"publication_pack/artifacts/{name}", s)

        add_json(results_json, "results.json")
        add_json(schema_json, "schema.json")
        add_json(model_spec_json, "model_spec.json")
        add_json(derived_metrics_json, "derived_metrics.json")

        # 3. Tables
        def add_df(df, name):
            if df is not None and not df.empty:
                s = df.to_csv(index=False)
                zf.writestr(f"publication_pack/tables/{name}", s)

        add_df(edges_df, "edges_filtered.csv")
        add_df(centrality_df, "centrality.csv")

        # Adjacency from R
        adj_src = pack_out_dir / "tables" / "adjacency_matrix.csv"
        if adj_src.exists():
            zf.write(adj_src, "publication_pack/tables/adjacency_matrix.csv")

        # 4. Figures (from R)
        fig_dir = pack_out_dir / "figures"
        if fig_dir.exists():
            for p in fig_dir.glob("*.*"):
                # e.g. figures/network_qgraph.pdf
                zf.write(p, f"publication_pack/figures/{p.name}")

    return zip_path
