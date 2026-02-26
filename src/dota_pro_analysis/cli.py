#!/usr/bin/env python3
"""命令行入口：拉取职业比赛、生成选禁统计、眼位图、热力图。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .api import OpenDotaClient
from .analyzers import aggregate_draft_stats, parse_draft_from_match
from .analyzers.match_maps import extract_match_player_maps
from .config import load_config, get_output_dir
from .parsers import ReplayParser
from .viz import draw_ward_map, draw_heatmap, export_draft_stats
from .viz.map_loader import ensure_map_downloaded


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
    match_ids: list[int] = []

    if getattr(args, "match_id", None) is not None:
        match_ids = [args.match_id]
        print(f"指定比赛: {args.match_id}")
    elif getattr(args, "team_id", None) is not None:
        print(f"正在获取战队 {args.team_id} 的比赛...")
        team_matches = client.get_team_matches(args.team_id, limit=limit)
        match_ids = [m["match_id"] for m in team_matches]
        print(f"获取到 {len(match_ids)} 场")
    elif getattr(args, "player", None) is not None:
        print(f"正在获取选手 {args.player} 的比赛...")
        player_matches = client.get_player_matches(args.player, limit=limit)
        match_ids = [m["match_id"] for m in player_matches]
        print(f"获取到 {len(match_ids)} 场")
    else:
        print("正在获取职业比赛列表...")
        pro = client.get_pro_matches(limit=limit, league_id=league_id)
        if not pro:
            print("未获取到比赛。")
            return 1
        match_ids = [m["match_id"] for m in pro]
        print(f"获取到 {len(match_ids)} 场")

    if not match_ids:
        print("没有可用的比赛 ID。")
        return 1
    print("正在拉取对局详情...")

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


def cmd_match_maps(args: argparse.Namespace) -> int:
    """根据 match_id 拉取 OpenDota 数据，输出两队共 10 人的眼位图+热力图（20 张 PNG）到 output/{match_id}/。"""
    match_id = getattr(args, "match_id", None)
    if match_id is None:
        print("请指定 --match-id")
        return 1
    out_dir = get_output_dir() / str(match_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = OpenDotaClient()
    print(f"正在获取比赛 {match_id} 详情...")
    try:
        match = client.get_match(match_id)
    except Exception as e:
        print(f"获取失败: {e}")
        return 1
    players_data = extract_match_player_maps(match)
    if len(players_data) != 10:
        print(f"警告: 仅解析到 {len(players_data)} 名选手，将只生成已有数据对应的图")

    saved: list[Path] = []
    for data in players_data:
        is_radiant = data["is_radiant"]
        slot = data["player_slot"]
        if is_radiant:
            idx = slot + 1
            side = "radiant"
        else:
            idx = slot - 128 + 1
            side = "dire"
        label = f"{side}_{idx}"

        wards = data["wards"]
        wards_path = out_dir / f"{label}_wards.png"
        draw_ward_map(wards, output_path=wards_path, title=f"Wards {label}")
        saved.append(wards_path)

        positions = data["positions"]
        heat_path = out_dir / f"{label}_heatmap.png"
        draw_heatmap(positions, output_path=heat_path, title=f"Heatmap {label}")
        saved.append(heat_path)

    print(f"已保存 {len(saved)} 张图到: {out_dir.resolve()}")
    return 0


def cmd_list_teams(args: argparse.Namespace) -> int:
    """列出战队（可按名称搜索），用于查 team_id。"""
    client = OpenDotaClient()
    teams = client.get_teams()
    query = (getattr(args, "search", None) or "").strip().lower()
    if query:
        teams = [t for t in teams if query in (t.get("name") or "").lower()]
    if not teams:
        print("未找到战队。" if query else "未获取到战队列表。")
        return 0 if query else 1
    print("team_id\tname\ttag")
    for t in teams[:100]:
        print(f"{t.get('team_id', '')}\t{t.get('name', '')}\t{t.get('tag', '')}")
    if len(teams) > 100:
        print(f"... 共 {len(teams)} 支，仅显示前 100")
    return 0


def cmd_download_map(args: argparse.Namespace) -> int:
    """下载 Dota 2 小地图底图到 assets/dota_minimap.png。"""
    path = ensure_map_downloaded(force=args.force, resolution=args.resolution)
    if path:
        print(f"地图已保存: {path.resolve()}")
        return 0
    print("下载失败（请检查网络）。也可手动将地图 PNG 放入项目 assets/ 目录，命名为 dota_minimap.png。")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Dota 2 职业比赛分析：选禁统计、眼位图、热力图")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", help="子命令")

    # draft
    p_draft = sub.add_parser("draft", help="拉取职业比赛并生成选禁/胜率统计")
    p_draft.add_argument("--match-id", type=int, default=None, help="指定单场比赛 ID")
    p_draft.add_argument("--team-id", type=int, default=None, help="指定战队 ID")
    p_draft.add_argument("--player", type=int, default=None, help="指定选手 account_id")
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

    p_map = sub.add_parser("download-map", help="下载 Dota 2 地图底图到 assets/")
    p_map.add_argument("--force", action="store_true", help="强制重新下载")
    p_map.add_argument("--resolution", type=int, default=1440, choices=[1080, 1440], help="分辨率 1440 更清晰")
    p_map.set_defaults(run=cmd_download_map)

    p_teams = sub.add_parser("list-teams", help="列出战队并查 team_id（可选 --search 按名称过滤）")
    p_teams.add_argument("--search", type=str, default=None, help="按战队名称关键词搜索")
    p_teams.set_defaults(run=cmd_list_teams)

    p_match_maps = sub.add_parser("match-maps", help="按 match_id 生成两队 10 人眼位图+热力图（20 张 PNG）")
    p_match_maps.add_argument("--match-id", type=int, required=True, help="比赛 ID")
    p_match_maps.set_defaults(run=cmd_match_maps)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
