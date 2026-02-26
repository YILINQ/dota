"""选手热力图：根据位置时间序列生成地图上的频率热力图。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter

from ..config import get_output_dir
from ..parsers.replay import MAP_SIZE_X, MAP_SIZE_Y, game_to_normalized
from .map_loader import load_map_image


def draw_heatmap(
    positions: list[tuple[float, float]],
    output_path: str | Path | None = None,
    map_size: int = 1440,
    sigma: float = 12.0,
    title: str = "Player Heatmap",
    use_game_coords: bool = True,
) -> Path:
    """
    根据位置列表 (x, y) 生成热力图。若 use_game_coords 为 True，则 (x,y) 为游戏坐标；
    否则视为已归一化 [0,1]。
    """
    if output_path is None:
        from ..config import load_config
        cfg = load_config()
        out_dir = get_output_dir()
        out_path = out_dir / "heatmap.png"
    else:
        out_path = Path(output_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not positions:
        # 空图
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))
        ax.set_facecolor("#1a1a2e")
        ax.set_title(title)
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        return out_path

    if use_game_coords:
        normalized = [game_to_normalized(x, y) for x, y in positions]
    else:
        normalized = [(max(0, min(1, x)), max(0, min(1, y))) for x, y in positions]

    # 映射到 [0, map_size-1] 像素
    xs = np.array([p[0] * (map_size - 1) for p in normalized])
    ys = np.array([p[1] * (map_size - 1) for p in normalized])

    # 2D 直方图 + 高斯平滑
    H, xedges, yedges = np.histogram2d(ys, xs, bins=map_size, range=[[0, map_size], [0, map_size]])
    H = gaussian_filter(H, sigma=sigma)
    H = np.log10(H + 1)

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.set_aspect("equal")
    ax.set_xlim(0, map_size)
    ax.set_ylim(0, map_size)

    bg = load_map_image(map_size)
    if bg is not None:
        ax.imshow(bg[::-1, :], origin="lower", extent=[0, map_size, 0, map_size], alpha=0.85, zorder=0)
    else:
        ax.set_facecolor("#1a1a2e")

    im = ax.imshow(
        H.T,
        origin="lower",
        extent=[0, map_size, 0, map_size],
        cmap="hot",
        alpha=0.55,
        interpolation="bilinear",
        zorder=1,
    )
    plt.colorbar(im, ax=ax, label="log10(count+1)")
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    return out_path


def draw_heatmaps_by_slot(
    positions_by_slot: dict[int, list[tuple[float, float]]],
    output_dir: str | Path | None = None,
    map_size: int = 1440,
    sigma: float = 12.0,
) -> list[Path]:
    """为每个 player_slot 生成一张热力图。"""
    from ..config import load_config
    cfg = load_config()
    out_dir = Path(output_dir or get_output_dir())
    pattern = cfg["output"].get("heatmap_file", "heatmap_{player_slot}.png")
    paths = []
    for slot, positions in positions_by_slot.items():
        out_path = out_dir / pattern.format(player_slot=slot)
        draw_heatmap(
            positions,
            output_path=out_path,
            map_size=map_size,
            sigma=sigma,
            title=f"Player Heatmap (slot {slot})",
        )
        paths.append(out_path)
    return paths
