"""Loads Sanad settings from config.yaml and secrets from .env."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
CONFIG_FILE = ROOT / "config.yaml"


@lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    """Return config.yaml as a dict (read once, then cached)."""
    load_dotenv(ROOT / ".env")
    with CONFIG_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_secret(name: str) -> str | None:
    """Read a secret (e.g. ANTHROPIC_API_KEY) from the environment / .env."""
    load_dotenv(ROOT / ".env")
    return os.getenv(name)


def project_path(relative: str) -> Path:
    """Resolve a path from config.yaml relative to the project root."""
    return ROOT / relative
