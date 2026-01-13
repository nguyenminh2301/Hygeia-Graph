"""Unit tests for diagnostics module."""

import unittest.mock as mock

from hygeia_graph.diagnostics import check_rscript, get_rscript_path


class TestDiagnosticsRscript:
    """Test Rscript detection and diagnostics."""

    def test_check_rscript_not_found(self):
        """Test that check_rscript returns ok=False when Rscript not found."""
        with mock.patch('hygeia_graph.diagnostics.shutil.which', return_value=None), \
             mock.patch('hygeia_graph.diagnostics.Path.exists', return_value=False):
            result = check_rscript()
            assert result["ok"] is False
            assert result["path"] is None
            assert result["version"] is None
            assert "not found" in result["message"]

    def test_check_rscript_found(self):
        """Test that check_rscript returns ok=True when Rscript found."""
        mock_version = "Rscript (R) version 4.3.3 (2024-02-29)"
        with mock.patch('hygeia_graph.diagnostics.get_rscript_path', return_value='C:\\R\\Rscript.exe'), \
             mock.patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = mock_version
            mock_run.return_value.stderr = ""

            result = check_rscript()
            assert result["ok"] is True
            assert result["path"] == 'C:\\R\\Rscript.exe'
            assert result["version"] == mock_version
            assert "found at" in result["message"]

    def test_get_rscript_path_from_path(self):
        """Test get_rscript_path finds Rscript in PATH."""
        with mock.patch('hygeia_graph.diagnostics.shutil.which', return_value='C:\\R\\Rscript.exe'):
            path = get_rscript_path()
            assert path == 'C:\\R\\Rscript.exe'

    def test_get_rscript_path_from_custom(self):
        """Test get_rscript_path finds Rscript in custom paths."""
        with mock.patch('hygeia_graph.diagnostics.shutil.which', return_value=None), \
             mock.patch('hygeia_graph.diagnostics.Path.exists') as mock_exists:
            mock_exists.return_value = True  # Custom path exists
            path = get_rscript_path()
            assert path == r"C:\Program Files\R\R-4.3.3\bin\Rscript.exe"

    def test_get_rscript_path_not_found(self):
        """Test get_rscript_path returns None when Rscript not found."""
        with mock.patch('hygeia_graph.diagnostics.shutil.which', return_value=None), \
             mock.patch('hygeia_graph.diagnostics.Path.exists', return_value=False):
            path = get_rscript_path()
            assert path is None
