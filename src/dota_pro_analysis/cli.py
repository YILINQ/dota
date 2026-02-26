#!/usr/bin/env python3
"""命令行入口：拉取职业比赛、生成选禁统计、眼位图、热力图。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .api import OpenDotaClient
from .analyzers import aggregate_draft_stats, parse_draft_from_match
from .config import load_config
from .parsers import ReplayParser
from .viz import draw_ward_map, draw_heatmap, export_draft_stats


def cmd_draft(args: argparse.Namespace) -> int:
    """从 OpenDota 拉取职业比赛并生成选禁/胜率统计。"""
    cfg = load_config()
    limit = args.limit or cfg["matches"].get("pro_matches_limit", 100)
    league_id = args.league_id
    if league_id is None and cfg["matches"].get("league_id"):
        try:
            league_id = int(cfg["matches"]["league_id"])
        except (TypeError, ValueError):
            league_id = None

    client = OpenDotaClient()
    print("正在获取职业比赛列表...")
    pro = client.get_pro_matches(limit=limit, league_id=league_id)
    if not pro:
        print("未获取到比赛。")
        return 1
    match_ids = [m["match_id"] for m in pro]
    print(f"获取到 {len(match_ids)} 场，正在拉取对局详情...")

    matches = client.get_matches_batch(match_ids)
    drafts = []
    for m in matches:
        d = parse_draft_from_match(m)
        if d and (d.picks or d.bans):
            drafts.append(d)
    if not drafts:
        print("没有可用的选禁数据。")
        return 1

    stats = aggregate_draft_stats(drafts)
    out_path = export_draft_stats(stats, args.output)
    print(f"选禁统计已写入: {out_path}")
    print(f"  总场次: {stats['total_matches']}")
    return 0


def cmd_wards(args: argparse.Namespace) -> int:
    """从 replay_dir 下的 JSON 或指定文件解析眼位并生成眼位图。"""
    parser = ReplayParser(args.replay_dir)
    if args.file:
        wards = parser.load_wards_from_json_file(args.file)
    else:
        wards = parser.load_all_wards()
    if not wards:
        print("没有眼位数据。请在 config 的 replay_dir 下放置眼位 JSON，或使用 --file 指定。")
        return 1
    out_path = draw_ward_map(wards, args.output)
    print(f"眼位图已生成: {out_path} (共 {len(wards)} 个眼位)")
    return 0


def cmd_heatmap(args: argparse.Namespace) -> int:
    """从 JSON 位置数据生成热力图。格式: {\"0\": [[x,y],[x,y],...], \"1\": [...]} 或单列表 [[x,y],...]。"""
    import json
    positions_by_slot: dict[int, list[tuple[float, float]]] = {}
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k, v in data.items():
                try:
                    slot = int(k)
                except ValueError:
                    continue
                if isinstance(v, list):
                    positions_by_slot[slot] = [(float(p[0]), float(p[1])) for p in v if len(p) >= 2]
        elif isinstance(data, list):
            positions_by_slot[0] = [(float(p[0]), float(p[1])) for p in data if len(p) >= 2]
    if not positions_by_slot:
        print("没有位置数据。请使用 --file 指定 JSON（按 slot 或单列表）。")
        return 1
    from .viz.heatmap import draw_heatmaps_by_slot
    if len(positions_by_slot) == 1 and 0 in positions_by_slot:
        out_path = draw_heatmap(positions_by_slot[0], args.output, title=args.title or "Player Heatmap")
        print(f"热力图已生成: {out_path}")
    else:
        out_dir = None
        if args.output:
            p = Path(args.output)
            out_dir = p.parent if p.suffix else p
        paths = draw_heatmaps_by_slot(positions_by_slot, out_dir)
        print(f"热力图已生成: {len(paths)} 个文件")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Dota 2 职业比赛分析：选禁统计、眼位图、热力图")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", help="子命令")

    # draft
    p_draft = sub.add_parser("draft", help="拉取职业比赛并生成选禁/胜率统计")
    p_draft.add_argument("--limit", type=int, default=None, help="比赛场数")
    p_draft.add_argument("--league-id", type=int, default=None, help="联赛 ID 过滤")
    p_draft.add_argument("-o", "--output", type=str, default=None, help="输出 JSON 路径")
    p_draft.set_defaults(run=cmd_draft)

    # wards
    p_wards = sub.add_parser("wards", help="从 JSON 眼位数据生成眼位图")
    p_wards.add_argument("--replay-dir", type=str, default=None, help="眼位 JSON 所在目录")
    p_wards.add_argument("--file", type=str, default=None, help="单个眼位 JSON 文件")
    p_wards.add_argument("-o", "--output", type=str, default=None, help="输出图片路径")
    p_wards.set_defaults(run=cmd_wards)

    # heatmap
    p_heat = sub.add_parser("heatmap", help="从位置 JSON 生成热力图")
    p_heat.add_argument("--file", type=str, required=True, help="位置 JSON 文件")
    p_heat.add_argument("-o", "--output", type=str, default=None, help="输出图片或目录")
    p_heat.add_argument("--title", type=str, default=None, help="图标题")
    p_heat.set_defaults(run=cmd_heatmap)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
