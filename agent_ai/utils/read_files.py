import json
from pathlib import Path
from typing import Any, Dict


# =============================================================================
# File Utilities
# =============================================================================
class FileUtils:
    """
    Utility class for reading text and JSON files from disk.

    This class provides static helper methods to load content from files with
    proper validation, predictable error handling, and UTF-8 encoding by default.

    Notes
    -----
    - All methods expect a `Path` object, not a string.
    - All read operations validate whether the path exists and is a file.
    """

    @staticmethod
    def read_text(file_path: Path) -> str:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return file_path.read_text(encoding="utf-8")

    @staticmethod
    def read_json(file_path: Path) -> Dict[str, Any]:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return json.loads(file_path.read_text(encoding="utf-8"))
