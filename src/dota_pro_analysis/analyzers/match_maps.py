"""从 OpenDota match JSON 提取每位选手的眼位与位置（用于眼位图/热力图）。"""
from __future__ import annotations

from typing import Any

from ..data.models import WardPlacement
from ..parsers.replay import MAP_SIZE_X, MAP_SIZE_Y, to_world_coords

# 每路大致的归一化中心 (nx, ny)，用于 lane_pos 近似热力
# lane: 0=bot, 1=mid, 2=top (radiant 视角)；对 dire 镜像
LANE_CENTERS_RADIANT = {
    0: (0.22, 0.22),   # bot
    1: (0.50, 0.50),   # mid
    2: (0.78, 0.78),   # top
}
LANE_CENTERS_DIRE = {
    0: (0.78, 0.78),
    1: (0.50, 0.50),
    2: (0.22, 0.22),
}


def _lane_to_game_xy(lane: int, is_radiant: bool) -> tuple[float, float]:
    """将 lane 转为游戏坐标 (x, y)。"""
    centers = LANE_CENTERS_RADIANT if is_radiant else LANE_CENTERS_DIRE
    nx, ny = centers.get(lane, (0.5, 0.5))
    return nx * MAP_SIZE_X, ny * MAP_SIZE_Y


def _parse_ward_entry(
    entry: Any,
    ward_type: str,
    team: str,
    match_id: int | None,
) -> WardPlacement | None:
    if not isinstance(entry, dict):
        return None
    x = entry.get("x") or entry.get("position_x")
    y = entry.get("y") or entry.get("position_y")
    if x is None or y is None:
        return None
    x, y = to_world_coords(float(x), float(y))
    t = float(entry.get("t") or entry.get("time") or entry.get("game_time") or 0)
    return WardPlacement(
        x=x,
        y=y,
        ward_type=ward_type,
        team=team,
        game_time_sec=t,
        match_id=match_id,
    )


def extract_match_player_maps(match: dict[str, Any]) -> list[dict[str, Any]]:
    """
    从 OpenDota GET /matches/{id} 的返回中提取 10 名选手各自的眼位与位置序列。
    返回长度为 10 的列表，每项：
    {
        "player_slot": int,
        "is_radiant": bool,
        "wards": list[WardPlacement],
        "positions": list[(x, y)]  # 游戏坐标，来自 lane_pos 近似或 runes 等
    }
    """
    match_id = match.get("match_id")
    players = match.get("players") or []
    result: list[dict[str, Any]] = []

    for p in players:
        player_slot = p.get("player_slot", 0)
        is_radiant = player_slot < 128
        team = "radiant" if is_radiant else "dire"

        wards: list[WardPlacement] = []
        for raw in p.get("obs_log") or []:
            w = _parse_ward_entry(raw, "observer", team, match_id)
            if w:
                wards.append(w)
        for raw in p.get("sen_log") or []:
            w = _parse_ward_entry(raw, "sentry", team, match_id)
            if w:
                wards.append(w)

        positions: list[tuple[float, float]] = []
        lane_pos = p.get("lane_pos")
        if isinstance(lane_pos, dict):
            for k, v in lane_pos.items():
                try:
                    lane = int(v) if isinstance(v, (int, float)) else 1
                    x, y = _lane_to_game_xy(lane, is_radiant)
                    positions.append((x, y))
                except (TypeError, ValueError):
                    continue
        elif isinstance(lane_pos, list):
            for lane in lane_pos:
                try:
                    lane = int(lane) if isinstance(lane, (int, float)) else 1
                    x, y = _lane_to_game_xy(lane, is_radiant)
                    positions.append((x, y))
                except (TypeError, ValueError):
                    continue

        result.append({
            "player_slot": player_slot,
            "is_radiant": is_radiant,
            "wards": wards,
            "positions": positions,
        })

    return result
