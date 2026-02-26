"""统一加载 Dota 2 地图底图：优先使用本地 assets，可选自动下载。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

# 默认地图图片来源（Dota 2 小地图风格，社区资源）
DEFAULT_MAP_URL = (
    "https://raw.githubusercontent.com/KaiSforza/dotaMinimapCovers/master/dota700_minimap_1080_large.png"
)


def _project_roots() -> list[Path]:
    """项目根目录及当前工作目录。"""
    roots = [Path.cwd()]
    try:
        # 包所在位置 -> 项目根（src/dota_pro_analysis/viz -> 上三级）
        roots.append(Path(__file__).resolve().parent.parent.parent.parent)
    except Exception:
        pass
    return roots


def get_map_path() -> Path | None:
    """返回第一个找到的地图文件路径；未找到返回 None。"""
    names = ["dota_minimap.png", "dota_map.png", "map.png", "minimap.png", "dota700_minimap_1080_large.png"]
    for root in _project_roots():
        for name in names:
            p = root / "assets" / name
            if p.is_file():
                return p
    return None


def ensure_map_downloaded(force: bool = False) -> Path | None:
    """
    若 assets 下没有地图图，则从默认 URL 下载到 assets/dota_minimap.png。
    force=True 时强制重新下载。
    成功返回保存路径，失败返回 None。
    """
    for root in _project_roots():
        assets = root / "assets"
        dest = assets / "dota_minimap.png"
        if dest.is_file() and not force:
            return dest
        try:
            import urllib.request
            assets.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(DEFAULT_MAP_URL, dest)
            if dest.is_file():
                return dest
        except Exception:
            continue
    return None


def load_map_image(size: int = 1024, download_if_missing: bool = True) -> Any:
    """
    加载地图底图并缩放到 size x size，返回 numpy 数组 (H, W, C) 或 None。
    download_if_missing: 若本地无图则尝试下载后再加载。
    """
    import numpy as np
    path = get_map_path()
    if path is None and download_if_missing:
        path = ensure_map_downloaded()
    if path is None:
        return None
    try:
        from PIL import Image
        img = Image.open(path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        arr = np.array(img.resize((size, size), Image.Resampling.LANCZOS))
        return arr
    except Exception:
        return None
