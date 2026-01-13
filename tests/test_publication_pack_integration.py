"""Integration tests for Publication Pack (R)."""

import shutil
import subprocess

import pytest

from hygeia_graph.publication_pack_interface import run_publication_pack_subprocess


def has_r_qgraph():
    if not shutil.which("Rscript"):
        return False
    # Check packages
    cmd = [
        "Rscript",
        "-e",
        "if(!all(c('qgraph','svglite','jsonlite') %in% installed.packages()[,'Package'])) "
        "quit(status=1)",
    ]
    ret = subprocess.call(cmd)
    return ret == 0


@pytest.mark.skipif(not has_r_qgraph(), reason="R or required packages not installed")
def test_run_publication_pack_end_to_end():
    # Simple inputs
    res = {
        "analysis_id": "test_123",
        "status": "success",
        "nodes": [
            {"id": "A", "domain_group": "G1", "mgm_type": "g"},
            {"id": "B", "domain_group": "G1", "mgm_type": "g"},
        ],
        "edges": [{"source": "A", "target": "B", "weight": 0.5}],
    }
    schema = {"dummy": True}

    out = run_publication_pack_subprocess(
        res, schema, None, threshold=0.0, show_labels=True, keep_workdir=False
    )

    assert out["meta"]["status"] == "success"

    files = out["files"]
    assert any("network_qgraph.svg" in f for f in files["figures"])
    assert any("adjacency_heatmap.svg" in f for f in files["figures"])
    assert any("adjacency_matrix.csv" in f for f in files["tables"])

    assert out["process"]["returncode"] == 0
