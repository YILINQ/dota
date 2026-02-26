"""眼位图：在地图底图上绘制真假眼位置。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ..config import get_output_dir
from ..data.models import WardPlacement
from ..parsers.replay import game_to_normalized
from .map_loader import load_map_image


def draw_ward_map(
    wards: list[WardPlacement],
    output_path: str | Path | None = None,
    map_size: int = 1440,
    point_radius: float = 8.0,
    title: str = "Ward Map (Observer / Sentry)",
) -> Path:
    """
    绘制眼位图：天辉/夜魇、真眼/假眼用不同颜色标在地图上。
    坐标会从游戏单位归一化到 [0,1] 再映射到图像。
    """
    if output_path is None:
        from ..config import load_config
        cfg = load_config()
        out_dir = get_output_dir()
        out_path = out_dir / cfg["output"].get("ward_map_file", "ward_map.png")
    else:
        out_path = Path(output_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 归一化坐标并映射到像素 (0,0) 左下
    obs_radiant: list[tuple[float, float]] = []
    obs_dire: list[tuple[float, float]] = []
    sent_radiant: list[tuple[float, float]] = []
    sent_dire: list[tuple[float, float]] = []

    for w in wards:
        nx, ny = game_to_normalized(w.x, w.y)
        px = nx * (map_size - 1)
        py = ny * (map_size - 1)
        pt = (px, py)
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

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.set_aspect("equal")
    ax.set_xlim(0, map_size)
    ax.set_ylim(0, map_size)

    bg = load_map_image(map_size)
    if bg is not None:
        # 图像坐标系 y 向下，我们约定 y 向上（游戏左下角原点）
        ax.imshow(bg[::-1, :], origin="lower", extent=[0, map_size, 0, map_size], zorder=0)
    else:
        ax.set_facecolor("#1a1a2e")
        ax.add_patch(plt.Rectangle((0, 0), map_size, map_size, facecolor="#16213e", edgecolor="#0f3460"))

    def plot_pts(pts: list, color: str, label: str, marker: str = "o"):
        if not pts:
            return
        xs, ys = zip(*pts)
        ax.scatter(xs, ys, c=color, s=point_radius**2, label=label, alpha=0.85, zorder=5, edgecolors="white", linewidths=0.5)

    # 只绘制有数据的类型，图例也只显示有数据的项（避免单人眼位图出现空的 Dire Sentry 等）
    if obs_radiant:
        plot_pts(obs_radiant, "#7cb342", "Radiant Observer", "o")
    if obs_dire:
        plot_pts(obs_dire, "#e53935", "Dire Observer", "o")
    if sent_radiant:
        plot_pts(sent_radiant, "#66bb6a", "Radiant Sentry", "s")
    if sent_dire:
        plot_pts(sent_dire, "#ef5350", "Dire Sentry", "s")

    ax.legend(loc="upper left", fontsize=8)
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return out_path
