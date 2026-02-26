# Dota 2 职业比赛分析工具

通过分析 Dota 2 职业比赛录像/数据，解析并可视化：

- **眼位图**：真眼/假眼在地图上的分布（天辉/夜魇）
- **选手热力图**：选手在地图上的出现频率
- **战队英雄选择/禁用率与胜率**：基于 OpenDota 职业比赛数据的选禁统计

## 安装

```bash
cd /path/to/dota
pip install -e .
# 或
pip install -r requirements.txt
```

可选：若使用 `config.yaml`，需安装 PyYAML：`pip install PyYAML`。

## 配置

在项目根目录放置 `config.yaml`（可选），用于 API、输出路径和录像目录：

```yaml
opendota:
  base_url: "https://api.opendota.com/api"
  api_key: ""   # 可选，提高限额
  rate_limit_delay: 1.0

matches:
  pro_matches_limit: 100
  league_id: ""   # 例如 15194 = TI

output:
  dir: "output"
  ward_map_file: "ward_map.png"
  heatmap_file: "heatmap_{player_slot}.png"
  draft_stats_file: "draft_stats.json"

replay_dir: "replays"
```

## 使用

### 地图底图（眼位图 / 热力图）

眼位图和热力图会使用 **Dota 2 真实小地图** 作为底图，更直观。首次使用前请先下载地图：

```bash
python -m dota_pro_analysis.cli download-map
```

会将地图保存到项目目录下的 `assets/dota_minimap.png`。默认使用 **1440 高分辨率** 底图，眼位图/热力图输出也为 1440px，更清晰。可选分辨率：

```bash
python -m dota_pro_analysis.cli download-map --resolution 1440   # 默认，更清晰
python -m dota_pro_analysis.cli download-map --resolution 1080 # 文件更小
python -m dota_pro_analysis.cli download-map --force            # 重新下载
```

当前默认图源为社区资源 [dotaMinimapCovers](https://github.com/KaiSforza/dotaMinimapCovers)（dota700 小地图）。若需与游戏内完全一致的最新地图，可从游戏或 [Liquipedia Commons](https://liquipedia.net/commons/Category:Dota_2_minimap_event_images) 等获取 PNG 后放入 `assets/` 并命名为 `dota_minimap.png`。

### 1. 选禁统计与胜率（无需录像，仅用 OpenDota API）

拉取最近职业比赛并生成英雄选择/禁用率与胜率 JSON：

```bash
python -m dota_pro_analysis.cli draft --limit 200 -o output/draft_stats.json
# 指定联赛（如 TI）
python -m dota_pro_analysis.cli draft --league-id 15194 -o output/ti_draft.json
# 指定某一场比赛
python -m dota_pro_analysis.cli draft --match-id 7123456789 -o output/match.json
# 指定战队（先查 team_id，见下方「如何找 match_id / team_id / 选手 ID」）
python -m dota_pro_analysis.cli draft --team-id 8260983 --limit 50 -o output/team_draft.json
# 指定选手（account_id）
python -m dota_pro_analysis.cli draft --player 86745912 --limit 100 -o output/player_draft.json
```

**如何找 match_id / team_id / 选手 ID**

- **比赛 ID (match_id)**：打开 [OpenDota 某场比赛页](https://www.opendota.com/matches)，URL 里的数字即为 `match_id`；或从 [Stratz](https://stratz.com/)、[Liquipedia](https://liquipedia.net/dota2/) 比赛页链接到 OpenDota 获取。
- **战队 ID (team_id)**：运行 `python -m dota_pro_analysis.cli list-teams` 列出所有战队；用 `--search 关键词` 按名称搜索，例如 `list-teams --search OG`。表里的 `team_id` 即用于 `--team-id`。
- **选手 ID (account_id)**：在 [OpenDota 选手页](https://www.opendota.com/players) 搜索或从比赛页点进选手，URL 中的数字即为 `account_id`（Steam 32 位 ID 也可，OpenDota 会识别）。

输出在 `output/draft_stats.json`，包含：

- `total_matches`：场次
- `heroes`：各英雄的 `pick_count`、`pick_rate`、`ban_count`、`ban_rate`、`wins`、`win_rate`
- `summary`：选人率/禁用率/胜率排行（至少出场 5 次的英雄参与胜率排行）

### 按比赛生成两队 10 人眼位图+热力图（20 张 PNG）

给定一场比赛的 `match_id`，从 OpenDota 拉取该场详情（需该场已被 OpenDota 解析过），为**两队共 10 名选手**每人生成一张眼位图、一张热力图，共 20 张 PNG，保存在 `output/{match_id}/` 下：

```bash
python -m dota_pro_analysis.cli match-maps --match-id 7123456789
```

输出文件命名：`radiant_1_wards.png`, `radiant_1_heatmap.png`, … `radiant_5_*`, `dire_1_*`, … `dire_5_*`。眼位来自 OpenDota 的 `obs_log`/`sen_log`，热力图来自 `lane_pos` 的近似位置（若该场未解析或缺少字段，对应图可能为空）。

### 2. 眼位图

从**眼位 JSON** 生成眼位图。眼位数据需自行从录像解析或从其他数据源导出，格式示例：

```json
[
  {"x": 1200, "y": 3400, "ward_type": "observer", "team": "radiant", "game_time": 600},
  {"x": 5000, "y": 8000, "ward_type": "sentry", "team": "dire"}
]
```

或带 key 的对象：

```json
{
  "match_id": 12345,
  "wards": [
    {"x": 1200, "y": 3400, "ward_type": "observer", "team": "radiant"}
  ]
}
```

坐标使用**游戏内单位**（地图约 17664×16643），工具会归一化到地图底图。

- 将眼位 JSON 放入 `replays/`（或在配置中修改 `replay_dir`），或直接用 `--file` 指定：

```bash
python -m dota_pro_analysis.cli wards
# 或
python -m dota_pro_analysis.cli wards --file path/to/wards.json -o output/ward_map.png
```

- 若需更美观的图，可在项目下建 `assets/` 并放入地图底图（如 `dota_map.png`、`dota_minimap.png`），工具会优先使用；否则使用默认背景。

### 3. 选手热力图

根据**位置时间序列**生成热力图。位置 JSON 格式示例：

- 单选手：`[[x1,y1],[x2,y2],...]`，坐标为游戏内单位。
- 多选手：`{"0": [[x,y],...], "1": [[x,y],...], ...}`，key 为 player_slot。

```bash
python -m dota_pro_analysis.cli heatmap --file positions.json -o output/heatmap.png
# 多选手时会按 slot 生成多张图到 output 目录
python -m dota_pro_analysis.cli heatmap --file positions_by_slot.json -o output/
```

位置数据目前需要从录像中解析得到（见下文“从录像解析”）。

## 从录像（.dem）解析眼位与位置

当前仓库内**不包含** .dem 解析实现。若要直接从录像得到眼位和选手位置，可以：

1. **使用现有解析器**  
   例如 [smoke](https://github.com/skadistats/smoke)（Python）、[clarity](https://github.com/skadistats/clarity)（Java）等，从 .dem 中读取实体（眼位、英雄坐标），导出为上述 JSON 格式，再交给本工具的 `wards` / `heatmap` 命令。

2. **扩展本工具**  
   在 `src/dota_pro_analysis/parsers/replay.py` 中：
   - `parse_dem_wards()`：解析眼位实体并返回 `list[WardPlacement]`
   - `parse_dem_positions()`：解析英雄位置并返回 `dict[player_slot, list[(x,y)]]`  
   可依赖 smoke 或通过子进程调用 clarity 等工具生成 JSON 再读入。

3. **数据源**  
   - 职业比赛 replay 可从 [Stratz](https://stratz.com/)、[OpenDota](https://www.opendota.com/) 或游戏内下载。  
   - 若第三方 API 提供眼位/位置数据，也可转成相同 JSON 格式后使用本工具。

## 项目结构

```
dota/
├── config.yaml
├── pyproject.toml
├── requirements.txt
├── README.md
├── assets/                 # 可选：地图底图
│   └── dota_map.png
├── replays/                 # 眼位/位置 JSON 或后续 .dem
└── src/
    └── dota_pro_analysis/
        ├── __init__.py
        ├── cli.py           # 命令行入口
        ├── config.py        # 配置加载
        ├── api/             # OpenDota 等 API
        ├── data/            # 数据模型
        ├── parsers/         # 眼位/位置解析（含 JSON，.dem 可扩展）
        ├── analyzers/       # 选禁聚合、眼位聚合
        └── viz/             # 眼位图、热力图、选禁 JSON 导出
```

## 依赖

- Python 3.9+
- requests, numpy, matplotlib, scipy, pandas, Pillow  
- 使用 `config.yaml` 时需要 PyYAML（见 `requirements.txt`）

## 许可证

MIT
