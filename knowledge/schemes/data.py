"""Runtime scheme loader reading directly from JSON files (single source of truth)."""

import json
from pathlib import Path
from typing import Optional
from shared.config import SCHEMES_DIR
from shared.schemas import Scheme
from scripts.export_schemes import SCHEMES_DATA


def load_all_schemes(directory: Optional[Path] = None) -> list[Scheme]:
    """Loads all Scheme models from JSON files in the specified directory (defaults to SCHEMES_DIR).

    Raises ValueError naming the file and specific problem if any JSON fails
    parsing or schema validation, ensuring corrupted files never fail silently.
    """
    target_dir = directory or SCHEMES_DIR
    schemes: list[Scheme] = []

    json_files = sorted(target_dir.glob("*.json"))
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON in '{json_file.name}': {e}") from e

        try:
            scheme = Scheme.model_validate(data)
            schemes.append(scheme)
        except Exception as e:
            raise ValueError(f"Scheme validation failed for '{json_file.name}': {e}") from e

    return schemes
