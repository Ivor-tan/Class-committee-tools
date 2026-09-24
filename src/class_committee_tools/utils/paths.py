"""应用路径及安全文件名处理。"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

APP_DIRECTORY_NAME = "ClassCommitteeTools"
INVALID_FILENAME_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def get_app_data_dir() -> Path:
    """返回当前用户的应用数据目录，并确保其存在。"""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    result = base / APP_DIRECTORY_NAME
    result.mkdir(parents=True, exist_ok=True)
    return result


def get_resource_path(relative_path: str) -> Path:
    """返回源码运行或 PyInstaller 运行时的资源路径。"""
    bundle_root = getattr(sys, "_MEIPASS", None)
    base_path = Path(bundle_root) if bundle_root else Path(__file__).resolve().parents[3]
    return base_path / relative_path


def sanitize_filename(value: str, fallback: str = "未命名") -> str:
    """将用户文本转换为安全的 Windows 文件名。"""
    cleaned = INVALID_FILENAME_PATTERN.sub("_", value).strip().rstrip(". ")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    return cleaned[:120].rstrip(". ") or fallback


def unique_path(path: Path) -> Path:
    """在不覆盖现有文件的前提下返回可用路径。"""
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1
