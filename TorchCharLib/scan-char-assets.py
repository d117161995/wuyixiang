#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描 X:\projects2024\TLI\Asset\Cha 下所有角色目录，
按照统一资产结构生成 torch-char-db.json
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone

CHA_ROOT = r"X:\projects2024\TLI\Asset\Cha"
OUTPUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "torch-char-db.json")
OUTPUT_JS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "torch-char-db.data.js")

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tga", ".tif", ".tiff", ".psd", ".exr"}
VIDEO_EXT = {".mp4", ".mov", ".avi", ".wmv", ".webm", ".mkv", ".flv"}
MAYA_EXT = {".ma", ".mb"}

EXCLUDE_DIRS = {"history", "metadata", "backup"}


def collect_media(folder: Path, extensions: set):
    """收集目录下的媒体文件（排除 history/metadata/backup 子目录）"""
    if not folder.exists() or not folder.is_dir():
        return []
    results = []
    for f in sorted(folder.rglob("*")):
        if not f.is_file():
            continue
        if any(part.lower() in EXCLUDE_DIRS for part in f.relative_to(folder).parts):
            continue
        if f.suffix.lower() in extensions:
            results.append(str(f).replace("\\", "/"))
    return results


def collect_maya_files(folder: Path):
    """收集目录下的 Maya 文件（排除 history/metadata/backup）"""
    if not folder.exists() or not folder.is_dir():
        return []
    results = []
    for f in sorted(folder.rglob("*")):
        if not f.is_file():
            continue
        if any(part.lower() in EXCLUDE_DIRS for part in f.relative_to(folder).parts):
            continue
        if f.suffix.lower() in MAYA_EXT:
            results.append(str(f).replace("\\", "/"))
    return results


def find_main_maya(folder: Path, char_id: str, suffix: str):
    """在目录下找主 Maya 文件，优先匹配 {char_id}_{suffix}.ma"""
    files = collect_maya_files(folder)
    if not files:
        return ""
    target = f"{char_id}_{suffix}.ma".lower()
    for f in files:
        if f.split("/")[-1].lower() == target:
            return f
    return files[0]


def scan_character(char_dir: Path):
    char_id = char_dir.name

    prodesign_game_images = collect_media(char_dir / "Prodesign" / "work", IMAGE_EXT)
    prodesign_film_images = collect_media(char_dir / "Prodesign" / "approved", IMAGE_EXT)
    game_3d_images = []  # 路径待定
    lookdev_videos = collect_media(char_dir / "LookDev" / "approved", VIDEO_EXT)
    if len(lookdev_videos) > 1:
        latest = max(lookdev_videos, key=lambda f: Path(f).stat().st_mtime)
        lookdev_videos = [latest]
    lookdev_images = collect_media(char_dir / "LookDev" / "approved", IMAGE_EXT)

    mod_path = find_main_maya(char_dir / "MOD" / "work", char_id, "mod")
    tex_path = find_main_maya(char_dir / "TEX" / "publish" / "maya", char_id, "tex")
    rig_path = find_main_maya(char_dir / "RIG" / "publish", char_id, "rig")

    return {
        "id": char_id,
        "name": char_id,
        "basePath": str(char_dir).replace("\\", "/"),
        "prodesign_game": {
            "label": "2D游戏设计",
            "images": prodesign_game_images,
        },
        "prodesign_film": {
            "label": "2D影视设计",
            "images": prodesign_film_images,
        },
        "game_3d": {
            "label": "3D游戏设计",
            "images": game_3d_images,
        },
        "lookdev": {
            "label": "3D影视设计（LookDev）",
            "videos": lookdev_videos,
            "images": lookdev_images,
        },
        "mod": {
            "label": "模型",
            "path": mod_path,
        },
        "tex": {
            "label": "贴图 Maya",
            "path": tex_path,
        },
        "rig": {
            "label": "绑定",
            "path": rig_path,
        },
    }


def main():
    cha_root = Path(CHA_ROOT)
    if not cha_root.exists():
        print(f"根目录不存在: {CHA_ROOT}")
        return

    char_dirs = sorted([d for d in cha_root.iterdir() if d.is_dir()])
    print(f"扫描到 {len(char_dirs)} 个角色目录")

    characters = []
    for d in char_dirs:
        print(f"  扫描: {d.name} ...", end="")
        char_data = scan_character(d)
        characters.append(char_data)

        counts = []
        pg = len(char_data["prodesign_game"]["images"])
        pf = len(char_data["prodesign_film"]["images"])
        g3 = len(char_data["game_3d"]["images"])
        lv = len(char_data["lookdev"]["videos"])
        li = len(char_data["lookdev"]["images"])
        if pg: counts.append(f"2D游戏:{pg}")
        if pf: counts.append(f"2D影视:{pf}")
        if g3: counts.append(f"3D游戏:{g3}")
        if lv: counts.append(f"LookDev视频:{lv}")
        if li: counts.append(f"LookDev图:{li}")
        if char_data["mod"]["path"]: counts.append("MOD")
        if char_data["tex"]["path"]: counts.append("TEX")
        if char_data["rig"]["path"]: counts.append("RIG")
        print(f" [{', '.join(counts) if counts else '暂无资源'}]")

    db = {
        "version": "1.0.0",
        "project": "火炬 TLI",
        "source": CHA_ROOT.replace("\\", "/"),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totalCharacters": len(characters),
        "characters": characters,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write("window.__TORCH_CHAR_DB__ = ")
        json.dump(db, f, ensure_ascii=False, indent=2)
        f.write(";\n")

    print(f"\n完成！共 {len(characters)} 个角色")
    print(f"JSON 数据库: {OUTPUT_JSON}")
    print(f"JS 数据库:   {OUTPUT_JS}")


if __name__ == "__main__":
    main()
