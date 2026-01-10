"""Unit tests for Publication Pack."""

import tempfile
import zipfile
from pathlib import Path

from hygeia_graph.publication_pack_utils import build_publication_zip, pack_settings_hash


def test_pack_settings_hash():
    s1 = {"thresh": 0.1, "layout": "spring"}
    h1 = pack_settings_hash(s1, "id1")
    h2 = pack_settings_hash(s1, "id1")
    h3 = pack_settings_hash(s1, "id2")
    assert h1 == h2
    assert h1 != h3


def test_build_publication_zip_structure():
    """Test ZIP file creation and directory structure."""
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        # Mock R output
        pack_out = base / "pack_out"
        (pack_out / "meta").mkdir(parents=True)
        (pack_out / "figures").mkdir(parents=True)
        (pack_out / "tables").mkdir(parents=True)

        with open(pack_out / "meta" / "publication_pack_meta.json", "w") as f:
            f.write("{}")
        with open(pack_out / "figures" / "fig1.svg", "w") as f:
            f.write("<svg></svg>")
        with open(pack_out / "tables" / "adjacency_matrix.csv", "w") as f:
            f.write("A,B\n0,1")

        zip_path = base / "test.zip"

        build_publication_zip(
            zip_path,
            analysis_id="test_id",
            schema_json={"s": 1},
            model_spec_json=None,
            results_json={"r": 1},
            derived_metrics_json=None,
            edges_df=None,
            centrality_df=None,
            pack_out_dir=pack_out,
        )

        assert zip_path.exists()

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "publication_pack/meta/publication_pack_meta.json" in names
            assert "publication_pack/artifacts/results.json" in names
            assert "publication_pack/artifacts/schema.json" in names
            assert "publication_pack/figures/fig1.svg" in names
            assert "publication_pack/tables/adjacency_matrix.csv" in names
