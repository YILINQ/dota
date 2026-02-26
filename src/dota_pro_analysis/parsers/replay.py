"""录像解析：眼位与选手位置。支持从 JSON（OpenDota/Stratz 等）或占位 .dem 接口。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from ..data.models import WardPlacement


# Dota 2 地图常用范围（游戏单位），用于归一化到 0-1
MAP_SIZE_X = 17664.0
MAP_SIZE_Y = 16643.0


def game_to_normalized(x: float, y: float) -> tuple[float, float]:
    """游戏坐标 -> 归一化 [0,1]（左下角原点）。"""
    nx = max(0.0, min(1.0, x / MAP_SIZE_X))
    ny = max(0.0, min(1.0, y / MAP_SIZE_Y))
    return nx, ny


def parse_wards_from_json(
    data: list[dict[str, Any]] | dict[str, Any],
    match_id: int | None = None,
) -> list[WardPlacement]:
    """
    从 JSON 解析眼位。支持格式示例：
    - [{"x": 1200, "y": 3400, "ward_type": "observer", "team": "radiant", "game_time": 600}, ...]
    - {"wards": [...]} 或 match 对象中的 object_wards / ward_log 等字段
    """
    wards: list[WardPlacement] = []
    if isinstance(data, dict):
        raw = data.get("wards") or data.get("object_wards") or data.get("ward_log") or []
    else:
        raw = data

    for w in raw:
        if not isinstance(w, dict):
            continue
        x = w.get("x") or w.get("position_x") or 0
        y = w.get("y") or w.get("position_y") or 0
        wt = (w.get("ward_type") or w.get("type") or "observer").lower()
        if "sentry" in wt:
            ward_type = "sentry"
        else:
            ward_type = "observer"
        team = (w.get("team") or "radiant").lower()
        if "dire" in team:
            team = "dire"
        else:
            team = "radiant"
        t = float(w.get("game_time") or w.get("game_time_sec") or 0)
        wards.append(
            WardPlacement(
                x=float(x),
                y=float(y),
                ward_type=ward_type,
                team=team,
                game_time_sec=t,
                match_id=match_id,
            )
        )
    return wards


class ReplayParser:
    """
    录像解析器。当前支持：
    - 从 JSON 文件或字典解析眼位（见 parse_wards_from_json）。
    - 若后续接入 smoke/clarity 等 .dem 解析，可在此扩展。
    """

    def __init__(self, replay_dir: str | Path | None = None):
        from ..config import load_config
        cfg = load_config()
        self.replay_dir = Path(replay_dir or cfg.get("replay_dir", "replays"))

    def iter_ward_json_files(self) -> Iterator[Path]:
        """遍历 replay_dir 下所有 .json 眼位数据文件。"""
        if not self.replay_dir.is_dir():
            return
        for p in self.replay_dir.rglob("*.json"):
            yield p

    def load_wards_from_json_file(self, path: str | Path) -> list[WardPlacement]:
        """从单个 JSON 文件加载眼位。"""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        match_id = None
        if isinstance(data, dict) and "match_id" in data:
            match_id = data["match_id"]
        return parse_wards_from_json(data, match_id=match_id)

    def load_all_wards(self) -> list[WardPlacement]:
        """从 replay_dir 下所有支持的 JSON 文件加载眼位。"""
        all_wards: list[WardPlacement] = []
        for p in self.iter_ward_json_files():
            try:
                all_wards.extend(self.load_wards_from_json_file(p))
            except (json.JSONDecodeError, OSError):
                continue
        return all_wards

    def parse_dem_wards(self, dem_path: str | Path) -> list[WardPlacement]:
        """
        从 .dem 文件解析眼位。占位实现；实际需接入 smoke 或外部解析器。
        可先使用第三方工具将 .dem 转为 JSON 再调用 load_wards_from_json_file。
        """
        # TODO: 使用 smoke 或 clarity 解析 entity 中的 ward 实体
        return []

    def parse_dem_positions(self, dem_path: str | Path) -> dict[int, list[tuple[float, float]]]:
        """
        从 .dem 解析各玩家（slot）的位置时间序列，用于热力图。
        返回: { player_slot: [(x,y), ...] }
        占位实现。
        """
        # TODO: 使用 smoke 读取 DT_DOTA_BaseNPC 的 m_cellX/Y + m_vecOrigin
        return {}
