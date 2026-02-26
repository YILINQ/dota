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

### 1. 选禁统计与胜率（无需录像，仅用 OpenDota API）

拉取最近职业比赛并生成英雄选择/禁用率与胜率 JSON：

```bash
python -m dota_pro_analysis.cli draft --limit 200 -o output/draft_stats.json
# 指定联赛（如 TI）
python -m dota_pro_analysis.cli draft --league-id 15194 -o output/ti_draft.json
```

输出在 `output/draft_stats.json`，包含：

- `total_matches`：场次
- `heroes`：各英雄的 `pick_count`、`pick_rate`、`ban_count`、`ban_rate`、`wins`、`win_rate`
- `summary`：选人率/禁用率/胜率排行（至少出场 5 次的英雄参与胜率排行）

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
