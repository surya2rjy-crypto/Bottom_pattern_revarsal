"""Load YAML configuration and paths."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "settings.yaml"
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"


def load_settings(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or CONFIG_PATH
    with open(cfg_path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return settings
