"""Integration tests for R Posthoc Metrics.

Skipped if R environment is not available or missing packages.
"""

import shutil
import subprocess

import pandas as pd
import pytest

from hygeia_graph.r_interface import run_mgm_subprocess

# Check for Rscript
HAS_RSCRIPT = shutil.which("Rscript") is not None


def check_r_packages():
    """Check if required R packages are installed."""
    if not HAS_RSCRIPT:
        return False
    # Quick check for igraph/mgm
    cmd = [
        "Rscript",
        "-e",
        "if(!all(c('mgm','jsonlite','digest','igraph') %in% installed.packages()[,'Package'])) quit(status=1)",
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


HAS_PACKAGES = check_r_packages()


@pytest.mark.skipif(not HAS_RSCRIPT, reason="Rscript not found")
@pytest.mark.skipif(not HAS_PACKAGES, reason="Missing R packages (mgm/igraph)")
def test_r_posthoc_integration(tmp_path):
    """Test full R runner with posthoc metrics enabled."""

    # Create valid inputs
    df = pd.DataFrame(
        {
            "X1": [1.0, 2.0, 3.0, 4.0, 5.0] * 10,
            "X2": [5.0, 4.0, 3.0, 2.0, 1.0] * 10,
        }
    )

    schema = {
        "schema_version": "1.0.0",
        "analysis_id": "test-uuid",
        "created_at": "2023-01-01T00:00:00Z",
        "dataset": {"name": "test", "row_count": 50, "column_count": 2},
        "variables": [
            {
                "id": "X1",
                "column": "X1",
                "mgm_type": "g",
                "measurement_level": "continuous",
                "level": 1,
            },
            {
                "id": "X2",
                "column": "X2",
                "mgm_type": "g",
                "measurement_level": "continuous",
                "level": 1,
            },
        ],
    }

    spec = {
        "analysis_id": "test-uuid",
        "mgm": {
            "type": "pairwise",
            "k": 2,
            "regularization": {"lambda_selection": "EBIC", "ebic_gamma": 0.25, "alpha": [1.0]},
            "rule_reg": "AND",
            "overparameterize": False,
            "scale_gaussian": True,
            "sign_info": True,
        },
        "edge_mapping": {"aggregator": "mean", "sign_strategy": "mean", "zero_tolerance": 0.01},
        "random_seed": 42,
    }

    # Run
    output = run_mgm_subprocess(
        df,
        schema,
        spec,
        workdir=tmp_path,
        compute_r_posthoc=True,
        community_algo="walktrap",  # use walktrap to be safe on tiny graph
    )

    # Verify basics
    assert output["process"]["returncode"] == 0
    assert "r_posthoc" in output
    posthoc = output["r_posthoc"]

    # Verify structure
    assert posthoc["predictability"]["enabled"] is True
    assert "X1" in posthoc["predictability"]["by_node"]
    assert posthoc["predictability"]["metric_by_node"]["X1"] == "R2"

    assert posthoc["communities"]["enabled"] is True
    assert len(posthoc["communities"]["membership"]) == 2
    assert "walktrap" in posthoc["communities"]["algorithm"]
