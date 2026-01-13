"""Multi-format file loader for Hygeia-Graph.

Supports: CSV, Excel (XLS/XLSX), TXT (tab/comma), Stata (DTA), SPSS (SAV), SAS (SAS7BDAT).
"""

from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Tuple, Union

import pandas as pd

# Supported file extensions and their types
SUPPORTED_EXTENSIONS = {
    ".csv": "csv",
    ".txt": "text",
    ".tsv": "text",
    ".xls": "excel",
    ".xlsx": "excel",
    ".dta": "stata",
    ".sav": "spss",
    ".sas7bdat": "sas",
}

SUPPORTED_FORMATS_DISPLAY = """
**📁 Supported File Formats:**
- **CSV** (.csv) - Comma-separated values (UTF-8 recommended)
- **Excel** (.xls, .xlsx) - Uses first sheet by default
- **Text** (.txt, .tsv) - Tab or comma-delimited
- **Stata** (.dta) - Stata data files
- **SPSS** (.sav) - SPSS data files
- **SAS** (.sas7bdat) - SAS data files
"""


class FileLoadError(Exception):
    """Error loading data file."""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)


def detect_file_type(filename: str) -> Optional[str]:
    """Detect file type from filename extension.

    Args:
        filename: Name or path of the file.

    Returns:
        File type string or None if unsupported.
    """
    ext = Path(filename).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(ext)


def get_supported_extensions() -> list:
    """Get list of supported file extensions for file uploader."""
    return list(SUPPORTED_EXTENSIONS.keys())


def load_csv(file: BinaryIO, **kwargs) -> pd.DataFrame:
    """Load CSV file."""
    try:
        return pd.read_csv(file, encoding="utf-8", **kwargs)
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(file, encoding="latin-1", **kwargs)


def load_text(file: BinaryIO, **kwargs) -> pd.DataFrame:
    """Load text file (auto-detect delimiter)."""
    # Read first few lines to detect delimiter
    file.seek(0)
    sample = file.read(4096).decode("utf-8", errors="replace")
    file.seek(0)

    # Detect delimiter
    if "\t" in sample:
        sep = "\t"
    elif ";" in sample:
        sep = ";"
    else:
        sep = ","

    try:
        return pd.read_csv(file, sep=sep, encoding="utf-8", **kwargs)
    except UnicodeDecodeError:
        file.seek(0)
        return pd.read_csv(file, sep=sep, encoding="latin-1", **kwargs)


def load_excel(file: BinaryIO, sheet_name: Union[str, int] = 0, **kwargs) -> pd.DataFrame:
    """Load Excel file (XLS or XLSX)."""
    try:
        return pd.read_excel(file, sheet_name=sheet_name, engine=None, **kwargs)
    except Exception as e:
        raise FileLoadError(f"Failed to load Excel file: {e}")


def load_stata(file: BinaryIO, **kwargs) -> pd.DataFrame:
    """Load Stata DTA file."""
    try:
        import pyreadstat
        df, meta = pyreadstat.read_dta(file, **kwargs)
        return df
    except ImportError:
        raise FileLoadError(
            "pyreadstat package required for Stata files",
            details="Install with: pip install pyreadstat"
        )
    except Exception as e:
        raise FileLoadError(f"Failed to load Stata file: {e}")


def load_spss(file: BinaryIO, **kwargs) -> pd.DataFrame:
    """Load SPSS SAV file."""
    try:
        import pyreadstat
        df, meta = pyreadstat.read_sav(file, **kwargs)
        return df
    except ImportError:
        raise FileLoadError(
            "pyreadstat package required for SPSS files",
            details="Install with: pip install pyreadstat"
        )
    except Exception as e:
        raise FileLoadError(f"Failed to load SPSS file: {e}")


def load_sas(file: BinaryIO, **kwargs) -> pd.DataFrame:
    """Load SAS SAS7BDAT file."""
    try:
        import pyreadstat
        df, meta = pyreadstat.read_sas7bdat(file, **kwargs)
        return df
    except ImportError:
        raise FileLoadError(
            "pyreadstat package required for SAS files",
            details="Install with: pip install pyreadstat"
        )
    except Exception as e:
        raise FileLoadError(f"Failed to load SAS file: {e}")


def load_file(
    file: BinaryIO,
    filename: str,
    **kwargs
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load data file with auto-detection.

    Args:
        file: File-like object.
        filename: Original filename (for extension detection).
        **kwargs: Additional arguments passed to loader.

    Returns:
        Tuple of (DataFrame, metadata dict).

    Raises:
        FileLoadError: If file cannot be loaded.
    """
    file_type = detect_file_type(filename)

    if file_type is None:
        ext = Path(filename).suffix
        raise FileLoadError(
            f"Unsupported file format: {ext}",
            details=f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )

    meta = {
        "original_filename": filename,
        "detected_type": file_type,
    }

    loaders = {
        "csv": load_csv,
        "text": load_text,
        "excel": load_excel,
        "stata": load_stata,
        "spss": load_spss,
        "sas": load_sas,
    }

    loader = loaders.get(file_type)
    if loader is None:
        raise FileLoadError(f"No loader for type: {file_type}")

    try:
        df = loader(file, **kwargs)
    except FileLoadError:
        raise
    except Exception as e:
        raise FileLoadError(f"Error loading {file_type} file: {e}")

    meta["n_rows"] = len(df)
    meta["n_cols"] = len(df.columns)
    meta["columns"] = df.columns.tolist()

    return df, meta


def convert_to_standard_format(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame to standard format for MGM analysis.

    - Ensures column names are strings
    - Removes leading/trailing whitespace from column names
    - Converts categorical columns to string type
    """
    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Convert object columns to string (handles mixed types)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).replace("nan", pd.NA)

    return df
