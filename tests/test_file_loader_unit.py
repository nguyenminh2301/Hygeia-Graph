"""Unit tests for file loader module."""

import io

import pandas as pd

from hygeia_graph.file_loader import (
    SUPPORTED_EXTENSIONS,
    FileLoadError,
    convert_to_standard_format,
    detect_file_type,
    get_supported_extensions,
    load_csv,
    load_text,
)


class TestDetectFileType:
    """Tests for file type detection."""

    def test_csv_detection(self):
        assert detect_file_type("data.csv") == "csv"
        assert detect_file_type("path/to/DATA.CSV") == "csv"

    def test_excel_detection(self):
        assert detect_file_type("data.xlsx") == "excel"
        assert detect_file_type("data.xls") == "excel"

    def test_stata_detection(self):
        assert detect_file_type("data.dta") == "stata"

    def test_spss_detection(self):
        assert detect_file_type("data.sav") == "spss"

    def test_sas_detection(self):
        assert detect_file_type("data.sas7bdat") == "sas"

    def test_text_detection(self):
        assert detect_file_type("data.txt") == "text"
        assert detect_file_type("data.tsv") == "text"

    def test_unsupported_format(self):
        assert detect_file_type("data.json") is None
        assert detect_file_type("data.xml") is None


class TestSupportedExtensions:
    """Tests for supported extensions."""

    def test_extensions_list(self):
        exts = get_supported_extensions()
        assert ".csv" in exts
        assert ".xlsx" in exts
        assert ".dta" in exts

    def test_all_formats_present(self):
        assert len(SUPPORTED_EXTENSIONS) >= 8


class TestLoadCsv:
    """Tests for CSV loading."""

    def test_load_simple_csv(self):
        csv_data = "a,b,c\n1,2,3\n4,5,6"
        file = io.BytesIO(csv_data.encode("utf-8"))
        df = load_csv(file)

        assert len(df) == 2
        assert list(df.columns) == ["a", "b", "c"]


class TestLoadText:
    """Tests for text file loading."""

    def test_load_tab_delimited(self):
        tsv_data = "a\tb\tc\n1\t2\t3"
        file = io.BytesIO(tsv_data.encode("utf-8"))
        df = load_text(file)

        assert len(df) == 1
        assert list(df.columns) == ["a", "b", "c"]


class TestConvertToStandard:
    """Tests for standard format conversion."""

    def test_clean_column_names(self):
        df = pd.DataFrame({" A ": [1], "B  ": [2], "  C": [3]})
        result = convert_to_standard_format(df)

        assert list(result.columns) == ["A", "B", "C"]

    def test_object_to_string(self):
        df = pd.DataFrame({"a": ["x", "y"], "b": [1, 2]})
        result = convert_to_standard_format(df)

        assert result["a"].dtype == "object"


class TestFileLoadError:
    """Tests for error handling."""

    def test_error_attributes(self):
        err = FileLoadError("Test error", details="More info")

        assert err.message == "Test error"
        assert err.details == "More info"
