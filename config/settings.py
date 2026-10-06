from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULT_CONFIG = {
    "api": {
        "host": "127.0.0.1",
        "port": 8000,
        "debug": False,
    },
    "paths": {
        "raw": "data/raw/AirQualityUCI.csv",
        "processed": "data/processed",
        "output": "data/output",
    },
}


def load_config() -> dict:
    config = deepcopy(DEFAULT_CONFIG)
    if not CONFIG_FILE.exists():
        return config

    with CONFIG_FILE.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if isinstance(loaded, dict):
        for section, values in loaded.items():
            if isinstance(values, dict) and isinstance(config.get(section), dict):
                config[section].update(values)
            else:
                config[section] = values

    return config


PROJECT_CONFIG = load_config()


def _configured_path(value: str | Path) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else BASE_DIR / path).resolve()


PATH_CONFIG = PROJECT_CONFIG.get("paths", {})
if not isinstance(PATH_CONFIG, dict):
    raise ValueError("The 'paths' section in config.yaml must be an object")

DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = _configured_path(PATH_CONFIG.get("raw", "data/raw/AirQualityUCI.csv"))
PROCESSED_DIR = _configured_path(PATH_CONFIG.get("processed", "data/processed"))
OUTPUT_DIR = _configured_path(PATH_CONFIG.get("output", "data/output"))


def ensure_project_directories() -> None:
    for directory in (DATA_DIR, RAW_DATA_PATH.parent, PROCESSED_DIR, OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def resolve_data_path(relative_path: str | Path) -> Path:
    return _configured_path(relative_path)
