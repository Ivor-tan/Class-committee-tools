"""应用设置的持久化与主题样式。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QSettings

from class_committee_tools.utils import get_app_data_dir

ORGANIZATION_NAME = "ClassCommitteeTools"
APPLICATION_NAME = "ClassCommitteeTools"


@dataclass(frozen=True, slots=True)
class AppSettings:
    theme: str = "light"
    language: str = "zh_CN"
    cache_path: Path | None = None

    @property
    def data_directory(self) -> Path:
        return self.cache_path or get_app_data_dir()


def load_settings() -> AppSettings:
    storage = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
    cache_value = str(storage.value("cache_path", "")).strip()
    return AppSettings(
        theme=str(storage.value("theme", "light")),
        language=str(storage.value("language", "zh_CN")),
        cache_path=Path(cache_value) if cache_value else None,
    )


def save_settings(settings: AppSettings) -> None:
    storage = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
    storage.setValue("theme", settings.theme)
    storage.setValue("language", settings.language)
    storage.setValue("cache_path", str(settings.cache_path) if settings.cache_path else "")
    storage.sync()


def stylesheet_for_theme(theme: str) -> str:
    if theme == "dark":
        return """
        QMainWindow, QDialog { background: #111b2b; color: #f7eadb; }
        QWidget { font-size: 14px; color: #f7eadb; }
        QLabel#pageTitle {
            font-size: 24px; font-weight: 700; color: #ffd18a; padding: 4px 0;
        }
        QLabel#requirementsLabel {
            color: #dbeaff; padding: 8px 10px; background: #19365c;
            border-left: 4px solid #f3a33c; border-radius: 4px;
        }
        QPushButton {
            padding: 8px 14px; color: #ffffff; background: #1769c2;
            border: 1px solid #2e86de; border-radius: 6px; font-weight: 600;
        }
        QPushButton:hover { background: #2381df; border-color: #65aaf0; }
        QPushButton:pressed { background: #0e4f98; }
        QPushButton:disabled { color: #7f8ba0; background: #263449; border-color: #35445a; }
        QLineEdit, QComboBox, QPlainTextEdit, QListWidget, QTableWidget {
            padding: 7px; background: #182538; color: #f8f1e8;
            border: 1px solid #3a516d; border-radius: 5px;
            selection-background-color: #1769c2; selection-color: #ffffff;
        }
        QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {
            border: 1px solid #f3a33c;
        }
        QComboBox QAbstractItemView {
            background: #182538; color: #f8f1e8; selection-background-color: #1769c2;
        }
        QHeaderView::section {
            background: #273b55; color: #ffe0ad; padding: 8px;
            border: 0; border-right: 1px solid #3a516d; border-bottom: 2px solid #a85c30;
            font-weight: 700;
        }
        QTableWidget {
            gridline-color: #31465f; alternate-background-color: #1d2c40;
            background: #182538;
        }
        QProgressBar {
            min-height: 18px; text-align: center; color: #ffffff; background: #273b55;
            border: 1px solid #3a516d; border-radius: 7px;
        }
        QProgressBar::chunk { background: #2381df; border-radius: 6px; }
        QScrollBar:vertical { background: #182538; width: 12px; }
        QScrollBar::handle:vertical { background: #526985; min-height: 24px; border-radius: 6px; }
        QStatusBar { background: #0d1624; color: #c7d5e8; }
        QToolTip { color: #172033; background: #fff1d8; border: 1px solid #a85c30; }
        """
    return """
    QMainWindow, QDialog { background: #fff8ef; color: #213550; }
    QWidget { font-size: 14px; color: #213550; }
    QLabel#pageTitle {
        font-size: 24px; font-weight: 700; color: #7a3f24; padding: 4px 0;
    }
    QLabel#requirementsLabel {
        color: #173f70; padding: 8px 10px; background: #e7f2ff;
        border-left: 4px solid #e9902f; border-radius: 4px;
    }
    QPushButton {
        padding: 8px 14px; color: #ffffff; background: #1877d2;
        border: 1px solid #1166b8; border-radius: 6px; font-weight: 600;
    }
    QPushButton:hover { background: #2489e5; border-color: #1268bb; }
    QPushButton:pressed { background: #0d5ca8; }
    QPushButton:disabled { color: #8b96a5; background: #e6e9ee; border-color: #d2d7de; }
    QLineEdit, QComboBox, QPlainTextEdit, QListWidget, QTableWidget {
        padding: 7px; background: #ffffff; color: #213550;
        border: 1px solid #c6d3e2; border-radius: 5px;
        selection-background-color: #1877d2; selection-color: #ffffff;
    }
    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {
        border: 1px solid #d97a28;
    }
    QComboBox QAbstractItemView {
        background: #ffffff; color: #213550; selection-background-color: #1877d2;
    }
    QHeaderView::section {
        background: #f4e2cd; color: #64351f; padding: 8px;
        border: 0; border-right: 1px solid #dfc5a8; border-bottom: 2px solid #ba6a35;
        font-weight: 700;
    }
    QTableWidget {
        background: #ffffff; alternate-background-color: #f5f9ff;
        gridline-color: #dce5ef;
    }
    QProgressBar {
        min-height: 18px; text-align: center; color: #173f70; background: #e8eef5;
        border: 1px solid #c6d3e2; border-radius: 7px;
    }
    QProgressBar::chunk { background: #2388df; border-radius: 6px; }
    QScrollBar:vertical { background: #f1e6d8; width: 12px; }
    QScrollBar::handle:vertical { background: #b8c9dc; min-height: 24px; border-radius: 6px; }
    QStatusBar { background: #f0dfcc; color: #5c3a28; }
    QToolTip { color: #213550; background: #fff0d5; border: 1px solid #ba6a35; }
    """
