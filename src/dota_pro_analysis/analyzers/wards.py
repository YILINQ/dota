"""眼位聚合：多场眼位归一化并按阵营/类型统计。"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..data.models import WardPlacement
from ..parsers.replay import game_to_normalized


def aggregate_wards(
    wards: list[WardPlacement],
) -> dict[str, Any]:
    """将眼位归一化到 [0,1] 并按 observer/sentry、radiant/dire 分组。"""
    obs_radiant: list[tuple[float, float]] = []
    obs_dire: list[tuple[float, float]] = []
    sent_radiant: list[tuple[float, float]] = []
    sent_dire: list[tuple[float, float]] = []

    for w in wards:
        nx, ny = game_to_normalized(w.x, w.y)
        pt = (nx, ny)
        if w.ward_type == "sentry":
            if w.team == "radiant":
                sent_radiant.append(pt)
            else:
                sent_dire.append(pt)
        else:
            if w.team == "radiant":
                obs_radiant.append(pt)
            else:
                obs_dire.append(pt)

    return {
        "observer": {"radiant": obs_radiant, "dire": obs_dire},
        "sentry": {"radiant": sent_radiant, "dire": sent_dire},
        "total_count": len(wards),
    }
