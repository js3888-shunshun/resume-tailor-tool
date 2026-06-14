"""Step 1: read/write/validate the materials library JSON.

Kept dependency-free of FastAPI so it can be unit-tested in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import get_settings
from .schemas import MaterialsLibrary


def load_materials(path: Path | None = None) -> MaterialsLibrary:
    """Load and validate the materials library.

    Falls back to the bundled sample file if the real one does not exist yet,
    so development can proceed before the user authors their own data.
    """
    settings = get_settings()
    target = path or settings.materials_path
    if not target.exists():
        target = settings.sample_materials_path
    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)
    return MaterialsLibrary.model_validate(data)


def save_materials(library: MaterialsLibrary, path: Path | None = None) -> Path:
    """Validate and persist the materials library, returning the written path."""
    settings = get_settings()
    target = path or settings.materials_path
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(library.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    return target


def validate_materials_file(path: Path) -> MaterialsLibrary:
    """Validate an arbitrary JSON file against the schema; raises on failure."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return MaterialsLibrary.model_validate(data)
