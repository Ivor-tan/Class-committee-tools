"""按学生导出 ZIP 压缩包。"""

from __future__ import annotations

import os
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from class_committee_tools.models import Student
from class_committee_tools.repositories import DatabaseRepository
from class_committee_tools.utils import sanitize_filename, unique_path


@dataclass(slots=True)
class ExportResult:
    output_directory: Path | None = None
    exported: list[Path] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


class ExportService:
    def __init__(self, repository: DatabaseRepository) -> None:
        self.repository = repository

    def export_activity(self, activity_id: str, output_dir: Path) -> ExportResult:
        activity = self.repository.get_activity(activity_id)
        if activity is None:
            raise ValueError("要导出的活动不存在。")
        activity_dir = output_dir / sanitize_filename(activity.name, "未命名活动")
        activity_dir.mkdir(parents=True, exist_ok=True)
        result = ExportResult(output_directory=activity_dir)
        students = [item for item in self.repository.list_students(activity_id) if item.submitted]
        name_counts: dict[str, int] = {}
        for student in students:
            name_counts[student.name] = name_counts.get(student.name, 0) + 1
        used_names: dict[str, int] = {}

        for student in students:
            try:
                base_name = self._archive_name(student, name_counts, used_names)
                archive_path = unique_path(activity_dir / f"{base_name}.zip")
                self._write_student_archive(student, archive_path)
                result.exported.append(archive_path)
            except Exception as exc:
                result.failures.append(f"{student.name}：{exc}")
        return result

    @staticmethod
    def _archive_name(
        student: Student,
        name_counts: dict[str, int],
        used_names: dict[str, int],
    ) -> str:
        base = sanitize_filename(student.name, "未命名学生")
        if name_counts[student.name] > 1:
            if student.student_number:
                base = f"{base}_{sanitize_filename(student.student_number, '无学号')}"
            else:
                used_names[student.name] = used_names.get(student.name, 0) + 1
                base = f"{base}_{used_names[student.name]}"
        return base

    def _write_student_archive(self, student: Student, archive_path: Path) -> None:
        materials = self.repository.list_materials(student.id)
        if not materials:
            raise ValueError("没有可导出的材料")
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="class_committee_", suffix=".zip", dir=archive_path.parent, delete=False
            ) as handle:
                temporary_path = Path(handle.name)
            with zipfile.ZipFile(
                temporary_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
            ) as archive:
                used_names: set[str] = set()
                for material in materials:
                    if not material.stored_path.is_file():
                        raise FileNotFoundError(f"材料文件缺失：{material.original_name}")
                    archive_name = sanitize_filename(material.original_name, "材料")
                    if archive_name in used_names:
                        index = 2
                        candidate = Path(archive_name)
                        while f"{candidate.stem}_{index}{candidate.suffix}" in used_names:
                            index += 1
                        archive_name = f"{candidate.stem}_{index}{candidate.suffix}"
                    used_names.add(archive_name)
                    archive.write(material.stored_path, arcname=archive_name)
            os.replace(temporary_path, archive_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
