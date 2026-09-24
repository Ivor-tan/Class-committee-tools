"""应用设置对话框。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from class_committee_tools.settings import AppSettings
from class_committee_tools.utils import get_app_data_dir


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.original_settings = settings
        self.setWindowTitle("设置 / Settings")
        self.resize(590, 320)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("浅色 / Light", "light")
        self.theme_combo.addItem("深色 / Dark", "dark")
        self.theme_combo.setCurrentIndex(1 if settings.theme == "dark" else 0)
        form.addRow("主题 / Theme：", self.theme_combo)

        self.language_combo = QComboBox()
        self.language_combo.addItem("简体中文", "zh_CN")
        self.language_combo.addItem("English", "en_US")
        self.language_combo.setCurrentIndex(1 if settings.language == "en_US" else 0)
        form.addRow("语言 / Language：", self.language_combo)

        cache_row = QHBoxLayout()
        self.cache_path_input = QLineEdit(str(settings.data_directory))
        browse_button = QPushButton("浏览 / Browse")
        browse_button.clicked.connect(self._choose_cache_directory)
        default_button = QPushButton("恢复默认 / Default")
        default_button.clicked.connect(self._use_default_cache_directory)
        cache_row.addWidget(self.cache_path_input)
        cache_row.addWidget(browse_button)
        cache_row.addWidget(default_button)
        form.addRow("缓存文件路径 / Data path：", cache_row)
        layout.addLayout(form)

        warning = QLabel(
            "更改语言或缓存路径后需要重启程序。切换缓存路径不会移动或删除旧目录中的数据。\n"
            "Language and data-path changes require a restart. "
            "Existing data is not moved or deleted."
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)
        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存 / Save")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消 / Cancel")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _choose_cache_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择缓存文件路径 / Select data path", self.cache_path_input.text()
        )
        if directory:
            self.cache_path_input.setText(directory)

    def _use_default_cache_directory(self) -> None:
        self.cache_path_input.clear()

    def values(self) -> AppSettings:
        cache_text = self.cache_path_input.text().strip()
        default_path = get_app_data_dir()
        cache_path = Path(cache_text) if cache_text and Path(cache_text) != default_path else None
        return AppSettings(
            theme=str(self.theme_combo.currentData()),
            language=str(self.language_combo.currentData()),
            cache_path=cache_path,
        )
