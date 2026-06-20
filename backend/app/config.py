"""Application configuration, loaded from environment / `.env`."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Project root = .../job application tool
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Load .env from project root if present (no error if missing).
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Lightweight settings holder (no external deps beyond python-dotenv)."""

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    # Default to the latest capable model; override via env if needed.
    model: str = os.getenv("RESUME_TAILOR_MODEL", "claude-opus-4-8")

    # Simple shared login for the deployed app. When APP_PASSWORD is unset, auth
    # is disabled (local/dev). APP_USERNAME is optional (any user if blank).
    app_username: str = os.getenv("APP_USERNAME", "")
    app_password: str = os.getenv("APP_PASSWORD", "")

    data_dir: Path = Path(os.getenv("RESUME_TAILOR_DATA_DIR", str(BACKEND_ROOT / "data")))
    materials_path: Path = Path(
        os.getenv("RESUME_TAILOR_MATERIALS", str(BACKEND_ROOT / "data" / "materials.json"))
    )
    sample_materials_path: Path = BACKEND_ROOT / "data" / "materials.sample.json"

    templates_dir: Path = BACKEND_ROOT / "templates"
    output_dir: Path = Path(os.getenv("RESUME_TAILOR_OUTPUT_DIR", str(BACKEND_ROOT / "output")))

    @property
    def has_api_key(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
