"""应用主窗口。"""

from __future__ import annotations

from functools import cmp_to_key
from pathlib import Path

from PyQt6.QtCore import QCollator, Qt, QThreadPool, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from class_committee_tools.i18n import translate
from class_committee_tools.models import Activity, Student
from class_committee_tools.repositories import DatabaseRepository
from class_committee_tools.services import (
    ActivityService,
    ExportResult,
    ExportService,
    FileService,
    ImportPreview,
    export_student_statistics,
    read_student_workbook,
)
from class_committee_tools.settings import (
    AppSettings,
    load_settings,
    save_settings,
    stylesheet_for_theme,
)
from class_committee_tools.ui.activity_dialog import CreateActivityDialog
from class_committee_tools.ui.material_dialog import MaterialDialog
from class_committee_tools.ui.settings_dialog import SettingsDialog
from class_committee_tools.ui.statistics_export_dialog import StatisticsExportDialog
from class_committee_tools.workers import FunctionTask


class MainWindow(QMainWindow):
    def __init__(
        self,
        repository: DatabaseRepository,
        activity_service: ActivityService,
        file_service: FileService,
        export_service: ExportService,
        settings: AppSettings,
    ) -> None:
        super().__init__()
        self.repository = repository
        self.activity_service = activity_service
        self.file_service = file_service
        self.export_service = export_service
        self.settings = settings
        self.current_activity: Activity | None = None
        self.students: list[Student] = []
        self.visible_students: list[Student] = []
        self.activity_sort_column: int | None = None
        self.activity_sort_ascending = True
        self.student_sort_column: int | None = None
        self.student_sort_ascending = True
        self.student_collator = QCollator()
        self.student_collator.setNumericMode(True)
        self.student_collator.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.thread_pool = QThreadPool.globalInstance()
        self._active_tasks: set[FunctionTask] = set()

        self.setWindowTitle(self._t("班级材料收集工具"))
        self.resize(1050, 680)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.home_page = self._build_home_page()
        self.detail_page = self._build_detail_page()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.detail_page)
        self.statusBar().showMessage(self._t("数据仅保存在本机"))
        self._load_activities()

    def _t(self, text: str) -> str:
        return translate(text, self.settings.language)

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel(self._t("班级材料收集工具"))
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addWidget(QLabel(self._t("创建新的材料收集活动")))

        create_row = QHBoxLayout()
        self.activity_name_input = QLineEdit()
        self.activity_name_input.setPlaceholderText(
            self._t("例如：2026 年奖学金申请材料收集")
        )
        self.activity_name_input.returnPressed.connect(self._create_activity)
        create_button = QPushButton(self._t("创建活动"))
        create_button.clicked.connect(self._create_activity)
        settings_button = QPushButton(self._t("设置"))
        settings_button.clicked.connect(self._open_settings)
        create_row.addWidget(self.activity_name_input)
        create_row.addWidget(create_button)
        create_row.addWidget(settings_button)
        layout.addLayout(create_row)
        layout.addWidget(QLabel(self._t("历史活动（双击可打开）")))

        self.activity_table = QTableWidget(0, 7)
        self.activity_table.setHorizontalHeaderLabels(
            [
                self._t("活动名称"),
                self._t("创建时间"),
                self._t("状态"),
                self._t("学生总数"),
                self._t("已提交"),
                self._t("未提交"),
                self._t("操作"),
            ]
        )
        self.activity_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.activity_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setWordWrap(True)
        activity_vertical_header = self.activity_table.verticalHeader()
        activity_vertical_header.setVisible(False)
        activity_vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        activity_header = self.activity_table.horizontalHeader()
        activity_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        activity_header.setMinimumSectionSize(70)
        activity_header.setSectionsClickable(True)
        activity_header.setSortIndicatorShown(False)
        activity_header.sectionClicked.connect(self._sort_activities_by_column)
        for column, width in enumerate((300, 170, 120, 90, 90, 90, 180)):
            self.activity_table.setColumnWidth(column, width)
        self.activity_table.cellDoubleClicked.connect(self._open_activity_row)
        layout.addWidget(self.activity_table)

        open_button = QPushButton(self._t("打开选中的活动"))
        open_button.clicked.connect(self._open_selected_activity)
        layout.addWidget(open_button, alignment=Qt.AlignmentFlag.AlignRight)
        return page

    def _build_detail_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        top = QHBoxLayout()
        back_button = QPushButton(self._t("← 返回主页"))
        back_button.clicked.connect(self._show_home)
        self.activity_title = QLabel()
        self.activity_title.setObjectName("pageTitle")
        top.addWidget(back_button)
        top.addWidget(self.activity_title)
        top.addStretch()
        layout.addLayout(top)

        toolbar = QHBoxLayout()
        import_button = QPushButton(self._t("导入 Excel 名单"))
        import_button.clicked.connect(self._choose_excel)
        export_button = QPushButton(self._t("导出学生压缩包"))
        export_button.clicked.connect(self._export_archives)
        export_data_button = QPushButton(self._t("导出当前数据"))
        export_data_button.clicked.connect(self._export_current_data)
        toolbar.addWidget(import_button)
        toolbar.addWidget(export_button)
        toolbar.addWidget(export_data_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.requirements_label = QLabel()
        self.requirements_label.setWordWrap(True)
        self.requirements_label.setObjectName("requirementsLabel")
        self.progress_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.requirements_label)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self._t("按姓名或学号搜索"))
        self.search_input.textChanged.connect(self._apply_filters)
        self.status_filter = QComboBox()
        self.status_filter.addItem(self._t("全部状态"), "all")
        self.status_filter.addItem(self._t("已提交"), "submitted")
        self.status_filter.addItem(self._t("未提交"), "pending")
        self.status_filter.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.status_filter.setMinimumWidth(130)
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.search_input)
        filters.addWidget(self.status_filter)
        layout.addLayout(filters)

        self.student_table = QTableWidget(0, 6)
        self.student_table.setHorizontalHeaderLabels(
            [
                self._t("姓名"),
                self._t("学号"),
                self._t("提交状态"),
                self._t("材料进度"),
                self._t("最后更新"),
                self._t("操作"),
            ]
        )
        self.student_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.student_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.student_table.setAlternatingRowColors(True)
        self.student_table.setWordWrap(True)
        student_vertical_header = self.student_table.verticalHeader()
        student_vertical_header.setVisible(False)
        student_vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header = self.student_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(70)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)
        header.sectionClicked.connect(self._sort_students_by_column)
        for column, width in enumerate((180, 140, 110, 180, 170, 210)):
            self.student_table.setColumnWidth(column, width)
        layout.addWidget(self.student_table)
        return page

    def _load_activities(self) -> None:
        activities = self.repository.list_activities()
        if self.activity_sort_column in {0, 1, 2}:
            column = self.activity_sort_column

            def compare(left: Activity, right: Activity) -> int:
                if column == 1:
                    return (left.created_at > right.created_at) - (
                        left.created_at < right.created_at
                    )
                if column == 2:
                    status_order = {"active": 0, "completed": 1}
                    return status_order[left.status] - status_order[right.status]
                return self.student_collator.compare(left.name, right.name)

            activities.sort(
                key=cmp_to_key(compare),
                reverse=not self.activity_sort_ascending,
            )
        self.activity_table.setRowCount(len(activities))
        for row, activity in enumerate(activities):
            values = (
                activity.name,
                activity.created_at.strftime("%Y-%m-%d %H:%M"),
                self._t("已完成") if activity.status == "completed" else self._t("未完成"),
                str(activity.student_count),
                str(activity.submitted_count),
                str(activity.pending_count),
            )
            for column, value in enumerate(values):
                if column == 2:
                    continue
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, activity.id)
                self.activity_table.setItem(row, column, item)
            status_combo = QComboBox()
            status_combo.addItem(self._t("未完成"), False)
            status_combo.addItem(self._t("已完成"), True)
            status_combo.setCurrentIndex(1 if activity.status == "completed" else 0)
            status_combo.currentIndexChanged.connect(
                lambda _index, selected=activity, combo=status_combo: (
                    self._change_activity_status(selected, bool(combo.currentData()))
                )
            )
            self.activity_table.setCellWidget(row, 2, status_combo)

            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(2, 2, 2, 2)
            edit_button = QPushButton(self._t("编辑"))
            edit_button.clicked.connect(
                lambda _checked=False, selected=activity: self._edit_activity(selected)
            )
            delete_button = QPushButton(self._t("删除"))
            delete_button.clicked.connect(
                lambda _checked=False, selected=activity: self._delete_activity(selected)
            )
            action_layout.addWidget(edit_button)
            action_layout.addWidget(delete_button)
            self.activity_table.setCellWidget(row, 6, actions)
        self.activity_table.resizeRowsToContents()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(load_settings(), self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        new_settings = dialog.values()
        try:
            new_settings.data_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "设置保存失败", f"无法使用所选缓存路径：{exc}")
            return
        restart_required = (
            new_settings.language != self.settings.language
            or new_settings.data_directory.resolve() != self.settings.data_directory.resolve()
        )
        save_settings(new_settings)
        self.settings = AppSettings(
            theme=new_settings.theme,
            language=self.settings.language,
            cache_path=self.settings.cache_path,
        )
        application = QApplication.instance()
        if application is not None:
            application.setStyleSheet(stylesheet_for_theme(new_settings.theme))
        if restart_required:
            QMessageBox.information(
                self,
                "设置已保存 / Settings saved",
                "语言或缓存路径将在重启程序后生效。旧缓存目录中的数据不会被删除。\n"
                "Language or data-path changes take effect after restart. Existing data is kept.",
            )
        else:
            self.statusBar().showMessage("设置已保存 / Settings saved", 3000)

    def _sort_activities_by_column(self, column: int) -> None:
        if column not in {0, 1, 2}:
            return
        if self.activity_sort_column == column:
            self.activity_sort_ascending = not self.activity_sort_ascending
        else:
            self.activity_sort_column = column
            self.activity_sort_ascending = True
        order = (
            Qt.SortOrder.AscendingOrder
            if self.activity_sort_ascending
            else Qt.SortOrder.DescendingOrder
        )
        header = self.activity_table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSortIndicator(column, order)
        self._load_activities()

    def _change_activity_status(self, activity: Activity, completed: bool) -> None:
        try:
            self.activity_service.set_completed(activity.id, completed)
        except ValueError as exc:
            QMessageBox.warning(self, "状态修改失败", str(exc))
            self._load_activities()
            return
        self.statusBar().showMessage(
            f"“{activity.name}”已标记为{'已完成' if completed else '未完成'}。", 3000
        )
        if self.activity_sort_column == 2:
            QTimer.singleShot(0, self._load_activities)

    def _edit_activity(self, activity: Activity) -> None:
        name, accepted = QInputDialog.getText(
            self,
            "编辑活动",
            "活动名称：",
            QLineEdit.EchoMode.Normal,
            activity.name,
        )
        if not accepted:
            return
        try:
            self.activity_service.rename(activity.id, name)
        except ValueError as exc:
            QMessageBox.warning(self, "编辑失败", str(exc))
            return
        self._load_activities()

    def _delete_activity(self, activity: Activity) -> None:
        answer = QMessageBox.warning(
            self,
            "确认删除活动",
            f"确定删除活动“{activity.name}”吗？\n\n"
            f"将删除 {activity.student_count} 名学生的记录及应用内保存的材料副本。"
            "\n学生原始文件不会受到影响。此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            student_ids = self.repository.delete_activity(activity.id)
            self.file_service.remove_student_storage(student_ids)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "删除失败", str(exc))
            self._load_activities()
            return
        self._load_activities()
        self.statusBar().showMessage(f"已删除活动“{activity.name}”。", 3000)

    def _create_activity(self) -> None:
        dialog = CreateActivityDialog(self.activity_name_input.text().strip(), self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        name, requirements = dialog.values()
        try:
            activity = self.activity_service.create(name, requirements)
        except ValueError as exc:
            QMessageBox.warning(self, "无法创建活动", str(exc))
            return
        self.activity_name_input.clear()
        self._load_activities()
        self._open_activity(activity.id)

    def _open_selected_activity(self) -> None:
        row = self.activity_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选择一个活动。")
            return
        self._open_activity_row(row)

    def _open_activity_row(self, row: int, _column: int = 0) -> None:
        item = self.activity_table.item(row, 0)
        if item:
            self._open_activity(item.data(Qt.ItemDataRole.UserRole))

    def _open_activity(self, activity_id: str) -> None:
        activity = self.repository.get_activity(activity_id)
        if activity is None:
            QMessageBox.warning(self, "活动不存在", "该活动已经不存在。")
            self._load_activities()
            return
        self.current_activity = activity
        self.student_sort_column = None
        self.student_sort_ascending = True
        self.student_table.horizontalHeader().setSortIndicatorShown(False)
        self.activity_title.setText(activity.name)
        requirements = self.repository.list_activity_requirements(activity.id)
        if requirements:
            self.requirements_label.setText(
                "需要收取："
                + "、".join(
                    f"{item.name}（{'必交' if item.required else '选交'}）"
                    for item in requirements
                )
            )
            self.requirements_label.show()
        else:
            self.requirements_label.hide()
        self.search_input.clear()
        self.status_filter.setCurrentIndex(0)
        self._refresh_students()
        self.stack.setCurrentWidget(self.detail_page)

    def _show_home(self) -> None:
        self.current_activity = None
        self._load_activities()
        self.stack.setCurrentWidget(self.home_page)

    def _refresh_students(self) -> None:
        if self.current_activity is None:
            return
        self.students = self.repository.list_students(self.current_activity.id)
        submitted = sum(student.submitted for student in self.students)
        total = len(self.students)
        pending = total - submitted
        self.progress_label.setText(
            f"共 {total} 人　已提交 {submitted} 人　未提交 {pending} 人"
        )
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(submitted)
        self.progress_bar.setFormat(f"{submitted}/{total}" if total else "暂无学生")
        self._apply_filters()

    def _apply_filters(self) -> None:
        keyword = self.search_input.text().strip().lower()
        status = self.status_filter.currentData()
        visible = []
        for student in self.students:
            searchable = f"{student.name} {student.student_number or ''}".lower()
            if keyword and keyword not in searchable:
                continue
            if status == "submitted" and not student.submitted:
                continue
            if status == "pending" and student.submitted:
                continue
            visible.append(student)
        if self.student_sort_column in {0, 1, 4}:
            column = self.student_sort_column

            def compare(left: Student, right: Student) -> int:
                if column == 4:
                    return (left.updated_at > right.updated_at) - (
                        left.updated_at < right.updated_at
                    )
                left_value = left.name if column == 0 else (left.student_number or "")
                right_value = right.name if column == 0 else (right.student_number or "")
                return self.student_collator.compare(left_value, right_value)

            visible.sort(
                key=cmp_to_key(compare),
                reverse=not self.student_sort_ascending,
            )
        self.visible_students = visible
        self._fill_student_table(visible)

    def _sort_students_by_column(self, column: int) -> None:
        if column not in {0, 1, 4}:
            return
        if self.student_sort_column == column:
            self.student_sort_ascending = not self.student_sort_ascending
        else:
            self.student_sort_column = column
            self.student_sort_ascending = True
        order = (
            Qt.SortOrder.AscendingOrder
            if self.student_sort_ascending
            else Qt.SortOrder.DescendingOrder
        )
        header = self.student_table.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSortIndicator(column, order)
        self._apply_filters()

    def _fill_student_table(self, students: list[Student]) -> None:
        self.student_table.setRowCount(len(students))
        for row, student in enumerate(students):
            values = (
                student.name,
                student.student_number or "—",
                self._t("已提交") if student.submitted else self._t("未提交"),
                (
                    f"必交 {student.fulfilled_count}/{student.required_count} 项"
                    f"（{student.file_count} 个文件）"
                    if student.requirement_count
                    else f"{student.file_count} 个文件"
                ),
                student.updated_at.strftime("%Y-%m-%d %H:%M"),
            )
            for column, value in enumerate(values):
                self.student_table.setItem(row, column, QTableWidgetItem(value))
            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(2, 2, 2, 2)
            add_button = QPushButton(self._t("添加文件"))
            add_button.clicked.connect(
                lambda _checked=False, selected=student: self._choose_student_files(selected)
            )
            view_button = QPushButton(self._t("查看"))
            view_button.clicked.connect(
                lambda _checked=False, selected=student: self._show_materials(selected)
            )
            action_layout.addWidget(add_button)
            action_layout.addWidget(view_button)
            self.student_table.setCellWidget(row, 5, actions)
        self.student_table.resizeRowsToContents()

    def _choose_excel(self) -> None:
        path_text, _ = QFileDialog.getOpenFileName(
            self, "选择学生名单", "", "Excel 工作簿 (*.xlsx)"
        )
        if not path_text:
            return
        self._run_task(
            lambda: read_student_workbook(Path(path_text)),
            self._confirm_import,
            "导入 Excel",
        )

    def _confirm_import(self, result: object) -> None:
        preview = result
        if not isinstance(preview, ImportPreview) or self.current_activity is None:
            return
        existing = bool(self.students)
        details = (
            f"识别姓名列：{preview.name_header}\n"
            f"识别学号列：{preview.number_header or '无'}\n"
            f"有效记录：{len(preview.entries)}\n"
            f"忽略空行：{preview.ignored_empty}\n"
            f"忽略重复：{preview.ignored_duplicates}"
        )
        replace = False
        if existing:
            box = QMessageBox(self)
            box.setWindowTitle("确认导入名单")
            box.setText(details)
            box.setInformativeText("当前活动已有学生，请选择导入方式。替换会删除现有学生记录及材料关联。")
            append_button = box.addButton("追加", QMessageBox.ButtonRole.AcceptRole)
            replace_button = box.addButton("替换", QMessageBox.ButtonRole.DestructiveRole)
            box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is replace_button:
                replace = True
            elif box.clickedButton() is not append_button:
                return
        else:
            answer = QMessageBox.question(self, "确认导入名单", details + "\n\n是否导入？")
            if answer != QMessageBox.StandardButton.Yes:
                return
        replaced_student_ids = [student.id for student in self.students] if replace else []
        added, ignored = self.repository.add_students(
            self.current_activity.id, preview.entries, replace=replace
        )
        if replaced_student_ids:
            self.file_service.remove_student_storage(replaced_student_ids)
        self._refresh_students()
        QMessageBox.information(self, "导入完成", f"成功导入 {added} 人，忽略重复 {ignored} 人。")

    def _choose_student_files(self, student: Student) -> None:
        if self.current_activity is None:
            return
        requirements = self.repository.list_activity_requirements(self.current_activity.id)
        requirement_id: str | None = None
        if requirements:
            options = [
                f"{item.name}（{'必交' if item.required else '选交'}）"
                for item in requirements
            ]
            selected_option, accepted = QInputDialog.getItem(
                self,
                "选择材料类型",
                f"请选择要为 {student.name} 添加的材料：",
                options,
                0,
                False,
            )
            if not accepted:
                return
            requirement = requirements[options.index(selected_option)]
            requirement_id = requirement.id
            existing_ids = {
                material.requirement_id
                for material in self.repository.list_materials(student.id)
            }
            if requirement_id in existing_ids:
                answer = QMessageBox.question(
                    self,
                    "材料已存在",
                    f"{student.name} 已添加过“{requirement.name}”。是否继续添加另一个文件？",
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
            path, _ = QFileDialog.getOpenFileName(
                self, f"添加 {student.name} 的“{requirement.name}”"
            )
            paths = [path] if path else []
        else:
            paths, _ = QFileDialog.getOpenFileNames(self, f"添加 {student.name} 的材料")
        if not paths:
            return
        self._run_task(
            lambda: self.file_service.add_files(
                student.id,
                [Path(path) for path in paths],
                requirement_id,
            ),
            lambda result: self._files_added(student, result),
            "添加材料",
        )

    def _files_added(self, student: Student, result: object) -> None:
        count = len(result) if isinstance(result, list) else 0
        self._refresh_students()
        QMessageBox.information(self, "添加完成", f"已为 {student.name} 添加 {count} 个文件。")

    def _show_materials(self, student: Student) -> None:
        dialog = MaterialDialog(student, self.repository, self.file_service, self)
        dialog.exec()
        if dialog.changed:
            self._refresh_students()

    def _export_archives(self) -> None:
        if self.current_activity is None:
            return
        submitted = sum(student.submitted for student in self.students)
        pending = len(self.students) - submitted
        if submitted == 0:
            QMessageBox.information(self, "没有材料", "当前没有已提交材料的学生。")
            return
        answer = QMessageBox.question(
            self,
            "确认导出",
            f"活动：{self.current_activity.name}\n将生成 {submitted} 个压缩包。\n"
            f"仍有 {pending} 人未提交。\n\n是否继续？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        directory = QFileDialog.getExistingDirectory(self, "选择压缩包输出目录")
        if not directory:
            return
        activity_id = self.current_activity.id
        self._run_task(
            lambda: self.export_service.export_activity(activity_id, Path(directory)),
            self._export_finished,
            "导出压缩包",
        )

    def _export_current_data(self) -> None:
        if self.current_activity is None:
            return
        if not self.visible_students:
            QMessageBox.information(self, "没有数据", "当前列表中没有可导出的学生数据。")
            return
        requirements = self.repository.list_activity_requirements(self.current_activity.id)
        dialog = StatisticsExportDialog(
            bool(requirements), len(self.visible_students), self
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        default_name = f"{self.current_activity.name}_学生提交统计.xlsx"
        path_text, _ = QFileDialog.getSaveFileName(
            self,
            "保存学生统计数据",
            default_name,
            "Excel 工作簿 (*.xlsx)",
        )
        if not path_text:
            return
        path = Path(path_text).with_suffix(".xlsx")
        students = list(self.visible_students)
        selected_fields = dialog.selected_fields()
        self._run_task(
            lambda: export_student_statistics(
                path,
                students,
                requirements,
                self.repository,
                selected_fields,
            ),
            self._statistics_export_finished,
            "导出当前数据",
        )

    def _statistics_export_finished(self, value: object) -> None:
        if not isinstance(value, Path):
            return
        box = QMessageBox(self)
        box.setWindowTitle("导出完成")
        box.setText(f"学生统计数据已导出：\n{value}")
        open_button = box.addButton("打开 Excel", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(value)))

    def _export_finished(self, value: object) -> None:
        if not isinstance(value, ExportResult):
            return
        message = f"成功生成 {len(value.exported)} 个压缩包，失败 {len(value.failures)} 个。"
        if value.failures:
            message += "\n\n" + "\n".join(value.failures[:10])
        box = QMessageBox(self)
        box.setWindowTitle("导出完成")
        box.setText(message)
        open_button = box.addButton("打开活动文件夹", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() is open_button and value.output_directory is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(value.output_directory)))

    def _run_task(self, function, on_success, operation_name: str) -> None:
        task = FunctionTask(function)
        self._active_tasks.add(task)
        task.signals.succeeded.connect(on_success)
        task.signals.failed.connect(
            lambda message: QMessageBox.critical(
                self, f"{operation_name}失败", message or "发生未知错误。"
            )
        )
        task.signals.finished.connect(lambda: self._finish_task(task))
        self.statusBar().showMessage(f"正在{operation_name}……")
        self.thread_pool.start(task)

    def _finish_task(self, task: FunctionTask) -> None:
        self._active_tasks.discard(task)
        self.statusBar().showMessage("就绪", 3000)

    def closeEvent(self, event) -> None:
        if self._active_tasks:
            answer = QMessageBox.question(
                self,
                "任务仍在运行",
                "仍有文件任务正在运行。是否等待任务完成后再退出？",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.thread_pool.waitForDone()
            else:
                event.ignore()
                return
        event.accept()
