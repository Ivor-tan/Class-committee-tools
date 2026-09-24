"""创建活动对话框。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class CreateActivityDialog(QDialog):
    """收集活动名称和可选材料清单。"""

    def __init__(self, initial_name: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("创建收集活动")
        self.resize(600, 460)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_input = QLineEdit(initial_name)
        self.name_input.setPlaceholderText("例如：2026 年奖学金申请材料收集")
        form.addRow("活动名称（必填）：", self.name_input)
        layout.addLayout(form)
        layout.addWidget(QLabel("需要收取的材料（可选）"))

        add_row = QHBoxLayout()
        self.requirement_name_input = QLineEdit()
        self.requirement_name_input.setPlaceholderText("例如：申请表")
        self.required_checkbox = QCheckBox("必须提交")
        self.required_checkbox.setChecked(True)
        add_button = QPushButton("添加材料")
        add_button.clicked.connect(self._add_requirement)
        self.requirement_name_input.returnPressed.connect(self._add_requirement)
        add_row.addWidget(self.requirement_name_input)
        add_row.addWidget(self.required_checkbox)
        add_row.addWidget(add_button)
        layout.addLayout(add_row)

        self.requirements_table = QTableWidget(0, 2)
        self.requirements_table.setHorizontalHeaderLabels(["材料名称", "是否必须提交"])
        header = self.requirements_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.requirements_table.verticalHeader().setVisible(False)
        layout.addWidget(self.requirements_table)
        remove_button = QPushButton("移除选中材料")
        remove_button.clicked.connect(self._remove_requirement)
        layout.addWidget(remove_button)

        hint = QLabel("必交材料全部上传后才算完成；选交材料不影响完成状态。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("创建")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.name_input.setFocus()

    def _add_requirement(self) -> None:
        name = self.requirement_name_input.text().strip()
        if not name:
            QMessageBox.information(self, "提示", "请先填写材料名称。")
            return
        existing_names = {
            self.requirements_table.item(row, 0).text().casefold()
            for row in range(self.requirements_table.rowCount())
        }
        if name.casefold() in existing_names:
            QMessageBox.information(self, "材料重复", "该材料名称已经添加。")
            return
        row = self.requirements_table.rowCount()
        self.requirements_table.insertRow(row)
        self.requirements_table.setItem(row, 0, QTableWidgetItem(name))
        required = QCheckBox("必须" if self.required_checkbox.isChecked() else "选交")
        required.setChecked(self.required_checkbox.isChecked())
        required.toggled.connect(
            lambda checked, checkbox=required: checkbox.setText("必须" if checked else "选交")
        )
        self.requirements_table.setCellWidget(row, 1, required)
        self.requirements_table.resizeRowsToContents()
        self.requirement_name_input.clear()
        self.required_checkbox.setChecked(True)
        self.requirement_name_input.setFocus()

    def _remove_requirement(self) -> None:
        row = self.requirements_table.currentRow()
        if row >= 0:
            self.requirements_table.removeRow(row)

    def values(self) -> tuple[str, list[tuple[str, bool]]]:
        requirements: list[tuple[str, bool]] = []
        for row in range(self.requirements_table.rowCount()):
            name_item = self.requirements_table.item(row, 0)
            checkbox = self.requirements_table.cellWidget(row, 1)
            if name_item is not None and isinstance(checkbox, QCheckBox):
                requirements.append((name_item.text(), checkbox.isChecked()))
        return self.name_input.text(), requirements
