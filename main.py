"""班级材料收集工具启动入口。"""

from __future__ import annotations

import sys
from pathlib import Path


def _add_src_to_path() -> None:
    """允许在未安装项目包时直接运行源码。"""
    src_path = Path(__file__).resolve().parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


if __name__ == "__main__":
    _add_src_to_path()
    from class_committee_tools.app import run

    raise SystemExit(run())
