"""选禁统计导出为 JSON。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import get_output_dir


def export_draft_stats(stats: dict[str, Any], output_path: str | Path | None = None) -> Path:
    """将 aggregate_draft_stats 的结果写入 JSON。"""
    if output_path is None:
        from ..config import load_config
        cfg = load_config()
        out_dir = get_output_dir()
        out_path = out_dir / cfg["output"].get("draft_stats_file", "draft_stats.json")
    else:
        out_path = Path(output_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return out_path
