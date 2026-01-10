"""Unit tests for diagnostics and resource guardrails."""

from unittest.mock import MagicMock, patch

from hygeia_graph.diagnostics import (
    build_diagnostics_report,
    check_r_packages,
    check_rscript,
)
from hygeia_graph.resource_guardrails import (
    check_network_health,
    enforce_explore_config,
    estimate_memory,
    recommend_defaults,
)


class TestDiagnostics:
    """Tests for diagnostics module."""

    def test_check_rscript_found(self):
        """Test when Rscript is found."""
        with patch("shutil.which", return_value="/usr/bin/Rscript"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="R scripting front-end version 4.3.0",
                    stderr="",
                )
                result = check_rscript()
                assert result["ok"] is True
                assert result["path"] == "/usr/bin/Rscript"

    def test_check_rscript_not_found(self):
        """Test when Rscript is not found."""
        with patch("shutil.which", return_value=None):
            result = check_rscript()
            assert result["ok"] is False
            assert result["path"] is None
            assert "not found" in result["message"].lower()

    def test_check_r_packages_no_rscript(self):
        """Test package check when Rscript missing."""
        with patch("shutil.which", return_value=None):
            result = check_r_packages(["mgm"])
            assert result["ok"] is False
            assert "mgm" in result["missing"]
            assert len(result["available"]) == 0

    def test_build_diagnostics_report_structure(self):
        """Test diagnostics report has required keys."""
        with patch("shutil.which", return_value=None):
            report = build_diagnostics_report()

            assert "timestamp" in report
            assert "python" in report
            assert "rscript" in report
            assert "r_packages" in report
            assert "dataset" in report
            assert "guardrail_triggers" in report

    def test_build_diagnostics_with_dataframe(self):
        """Test diagnostics with DataFrame."""
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2, None], "b": [4, 5, 6]})

        with patch("shutil.which", return_value=None):
            report = build_diagnostics_report(df=df)

            assert report["dataset"] is not None
            assert report["dataset"]["n_rows"] == 3
            assert report["dataset"]["n_cols"] == 2
            assert report["dataset"]["missing_cells"] == 1


class TestResourceGuardrails:
    """Tests for resource guardrails module."""

    def test_recommend_defaults_small_network(self):
        """Test recommendations for small network."""
        rec = recommend_defaults(n_nodes=20, n_edges=50)

        assert rec["show_labels"] is True
        assert rec["pyvis_enabled"] is True
        assert rec["top_edges"] is None
        assert len(rec["warnings"]) == 0

    def test_recommend_defaults_medium_network(self):
        """Test recommendations for medium network (hide labels)."""
        rec = recommend_defaults(n_nodes=100, n_edges=500)

        assert rec["show_labels"] is False
        assert rec["pyvis_enabled"] is True
        assert len(rec["warnings"]) >= 1

    def test_recommend_defaults_large_network(self):
        """Test recommendations for large network (limit edges)."""
        rec = recommend_defaults(n_nodes=150, n_edges=2000)

        assert rec["show_labels"] is False
        assert rec["top_edges"] == 1000
        assert len(rec["warnings"]) >= 2

    def test_recommend_defaults_huge_network(self):
        """Test recommendations for huge network (disable PyVis)."""
        rec = recommend_defaults(n_nodes=250, n_edges=10000)

        assert rec["pyvis_enabled"] is False
        assert rec["threshold"] > 0
        assert len(rec["warnings"]) >= 2

    def test_enforce_explore_config_clamping(self):
        """Test config enforcement clamps values."""
        cfg = {"threshold": 0.0, "top_edges": None}

        cfg2, messages = enforce_explore_config(cfg, n_nodes=250, n_edges=8000)

        assert cfg2["threshold"] >= 0.01
        assert cfg2["top_edges"] is not None
        assert len(messages) >= 1

    def test_enforce_explore_config_passthrough(self):
        """Test config enforcement passes small networks."""
        cfg = {"threshold": 0.0, "top_edges": None}

        cfg2, messages = enforce_explore_config(cfg, n_nodes=30, n_edges=100)

        assert cfg2["threshold"] == 0.0
        assert len(messages) == 0

    def test_estimate_memory_small(self):
        """Test memory estimation for small network."""
        mem = estimate_memory(n_nodes=50)

        assert mem["adjacency_mb"] < 1
        assert mem["level"] == "ok"

    def test_estimate_memory_large(self):
        """Test memory estimation for large network."""
        mem = estimate_memory(n_nodes=4000)  # ~122MB adjacency

        assert mem["adjacency_mb"] > 100
        assert mem["level"] in ("warning", "critical")

    def test_check_network_health(self):
        """Test combined health check."""
        health = check_network_health(n_nodes=50, n_edges=100)

        assert "memory" in health
        assert "recommendations" in health
        assert "safe_to_render" in health
        assert health["safe_to_render"] is True
