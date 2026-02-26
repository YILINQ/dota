"""从 OpenDota 对局详情解析选禁并汇总英雄选择/禁用率与胜率。"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..data.models import DraftInfo


def parse_draft_from_match(match: dict[str, Any]) -> DraftInfo | None:
    """从单场 match 字典解析出 DraftInfo。"""
    match_id = match.get("match_id")
    if match_id is None:
        return None
    radiant_win = bool(match.get("radiant_win", False))
    picks_bans = match.get("picks_bans") or []
    picks = []
    bans = []
    for pb in picks_bans:
        hero_id = pb.get("hero_id")
        if hero_id is None:
            continue
        is_pick = pb.get("is_pick", False)
        team = "radiant" if pb.get("team", 0) == 0 else "dire"
        order = pb.get("order", len(picks) + len(bans))
        entry = {"hero_id": hero_id, "team": team, "order": order}
        if is_pick:
            picks.append(entry)
        else:
            bans.append(entry)
    return DraftInfo(
        match_id=match_id,
        radiant_win=radiant_win,
        picks=picks,
        bans=bans,
        radiant_team_id=match.get("radiant_team_id"),
        dire_team_id=match.get("dire_team_id"),
    )


def aggregate_draft_stats(drafts: list[DraftInfo]) -> dict[str, Any]:
    """汇总多场对局的英雄选择/禁用率与胜率。"""
    pick_count: dict[int, int] = defaultdict(int)
    ban_count: dict[int, int] = defaultdict(int)
    pick_wins: dict[int, int] = defaultdict(int)
    total_matches = len(drafts)

    for d in drafts:
        for p in d.picks:
            hid = p["hero_id"]
            pick_count[hid] += 1
            # 该英雄所在队伍是否胜利
            team = p["team"]
            won = (team == "radiant" and d.radiant_win) or (team == "dire" and not d.radiant_win)
            if won:
                pick_wins[hid] += 1
        for b in d.bans:
            ban_count[b["hero_id"]] += 1

    hero_ids = sorted(set(pick_count) | set(ban_count))
    by_hero = {}
    for hid in hero_ids:
        picks = pick_count.get(hid, 0)
        wins = pick_wins.get(hid, 0)
        bans = ban_count.get(hid, 0)
        by_hero[hid] = {
            "hero_id": hid,
            "pick_count": picks,
            "pick_rate": round(picks / total_matches, 4) if total_matches else 0,
            "ban_count": bans,
            "ban_rate": round(bans / total_matches, 4) if total_matches else 0,
            "wins": wins,
            "win_rate": round(wins / picks, 4) if picks else 0,
        }

    return {
        "total_matches": total_matches,
        "heroes": by_hero,
        "summary": {
            "pick_rate_ranking": sorted(by_hero.values(), key=lambda x: -x["pick_rate"])[:30],
            "ban_rate_ranking": sorted(by_hero.values(), key=lambda x: -x["ban_rate"])[:30],
            "win_rate_ranking": sorted(
                [h for h in by_hero.values() if h["pick_count"] >= 5],
                key=lambda x: -x["win_rate"],
            )[:30],
        },
    }
