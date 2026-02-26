"""加载 config.yaml 与默认配置。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

_CONFIG: dict[str, Any] | None = None


def _default_config() -> dict[str, Any]:
    return {
        "opendota": {
            "base_url": "https://api.opendota.com/api",
            "api_key": "",
            "rate_limit_delay": 1.0,
        },
        "matches": {
            "pro_matches_limit": 100,
            "league_id": "",
        },
        "output": {
            "dir": "output",
            "ward_map_file": "ward_map.png",
            "heatmap_file": "heatmap_{player_slot}.png",
            "draft_stats_file": "draft_stats.json",
        },
        "replay_dir": "replays",
    }


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """加载配置；若未提供路径则从项目根查找 config.yaml。"""
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG

    base = _default_config()

    if config_path is None:
        for root in [Path.cwd(), Path(__file__).resolve().parent.parent.parent]:
            p = root / "config.yaml"
            if p.is_file():
                config_path = p
                break

    if config_path and Path(config_path).is_file():
        if yaml is None:
            raise ImportError("PyYAML is required to load config.yaml. Install with: pip install pyyaml")
        with open(config_path, encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
        for key, value in user.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                base[key] = {**base[key], **value}
            else:
                base[key] = value

    _CONFIG = base
    return _CONFIG


def get_output_dir() -> Path:
    cfg = load_config()
    out = Path(cfg["output"]["dir"])
    out.mkdir(parents=True, exist_ok=True)
    return out
