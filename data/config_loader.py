"""Carga de configuración del proyecto."""
from __future__ import annotations
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    cfg_path = ROOT / "config.yaml"
    if not cfg_path.exists():
        example = ROOT / "config.yaml.example"
        raise FileNotFoundError(
            f"No existe {cfg_path}. Copia {example} a config.yaml y rellena tu API key de FMP."
        )
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cache_dir() -> Path:
    cfg = load_config()
    d = ROOT / cfg.get("cache", {}).get("dir", "cache")
    d.mkdir(parents=True, exist_ok=True)
    return d
