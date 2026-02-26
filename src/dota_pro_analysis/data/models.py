"""通用数据模型：选禁、眼位、位置等。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class WardPlacement:
    """单个眼位记录。"""
    x: float  # 游戏内 x（或映射后）
    y: float
    ward_type: Literal["observer", "sentry"]
    team: Literal["radiant", "dire"]
    game_time_sec: float = 0.0
    match_id: int | None = None


@dataclass
class DraftInfo:
    """单场对局的选禁与胜负。"""
    match_id: int
    radiant_win: bool
    picks: list[dict] = field(default_factory=list)   # [{"hero_id": 1, "team": "radiant", "order": 0}, ...]
    bans: list[dict] = field(default_factory=list)    # 同上
    radiant_team_id: int | None = None
    dire_team_id: int | None = None
