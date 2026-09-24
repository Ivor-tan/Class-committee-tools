"""学生材料查看与删除对话框。"""

from __future__ import annotations

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from class_committee_tools.models import Student
from class_committee_tools.repositories import DatabaseRepository
from class_committee_tools.services import FileService


class MaterialDialog(QDialog):
    def __init__(
        self,
        student: Student,
        repository: DatabaseRepository,
        file_service: FileService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.student = student
        self.repository = repository
        self.file_service = file_service
        self.changed = False
        self.setWindowTitle(f"{student.name}的材料")
        self.resize(560, 360)

        layout = QVBoxLayout(self)
        student_info = f"学生：{student.name}　学号：{student.student_number or '未填写'}"
        layout.addWidget(QLabel(student_info))
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._open_material)
        layout.addWidget(self.list_widget)

        buttons = QHBoxLayout()
        open_button = QPushButton("打开文件")
        open_button.clicked.connect(self._open_selected)
        delete_button = QPushButton("移除材料")
        delete_button.clicked.connect(self._remove_selected)
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(open_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self._reload()

    def _reload(self) -> None:
        self.list_widget.clear()
        for material in self.repository.list_materials(self.student.id):
            prefix = f"[{material.requirement_name}] " if material.requirement_name else ""
            item = QListWidgetItem(f"{prefix}{material.original_name}")
            item.setData(256, material)
            item.setToolTip(str(material.stored_path))
            self.list_widget.addItem(item)

    def _open_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            self._open_material(item)

    def _open_material(self, item: QListWidgetItem) -> None:
        material = item.data(256)
        if not material.stored_path.exists():
            QMessageBox.warning(self, "文件缺失", "该材料文件已不存在。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(material.stored_path)))

    def _remove_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            QMessageBox.information(self, "提示", "请先选择要移除的材料。")
            return
        material = item.data(256)
        answer = QMessageBox.question(
            self,
            "确认移除",
            f"确定移除“{material.original_name}”吗？\n此操作会删除应用内保存的副本，不影响原文件。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.file_service.remove_material(material.id)
        self.changed = True
        self._reload()
