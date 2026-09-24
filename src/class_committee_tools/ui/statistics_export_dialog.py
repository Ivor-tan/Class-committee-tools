"""选择学生统计数据导出字段。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from class_committee_tools.services import EXPORT_FIELDS


class StatisticsExportDialog(QDialog):
    def __init__(self, has_requirements: bool, student_count: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("导出当前数据")
        self.resize(400, 430)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"将导出当前列表中的 {student_count} 名学生，请选择字段："))
        self.checkboxes: dict[str, QCheckBox] = {}
        for field, title in EXPORT_FIELDS.items():
            if field == "requirement_details" and not has_requirements:
                continue
            checkbox = QCheckBox(title)
            checkbox.setChecked(True)
            self.checkboxes[field] = checkbox
            layout.addWidget(checkbox)
        layout.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("选择保存位置")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_if_valid(self) -> None:
        if not self.selected_fields():
            QMessageBox.information(self, "提示", "请至少选择一项要导出的数据。")
            return
        self.accept()

    def selected_fields(self) -> set[str]:
        return {field for field, checkbox in self.checkboxes.items() if checkbox.isChecked()}
