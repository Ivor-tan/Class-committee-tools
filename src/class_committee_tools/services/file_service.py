"""学生材料归档与删除。"""

from __future__ import annotations

import shutil
from pathlib import Path

from class_committee_tools.models import Material
from class_committee_tools.repositories import DatabaseRepository
from class_committee_tools.utils import sanitize_filename, unique_path


class FileService:
    def __init__(self, repository: DatabaseRepository, files_root: Path) -> None:
        self.repository = repository
        self.files_root = files_root.resolve()
        self.files_root.mkdir(parents=True, exist_ok=True)

    def add_files(
        self,
        student_id: str,
        source_paths: list[Path],
        requirement_id: str | None = None,
    ) -> list[Material]:
        requirement = None
        if requirement_id is not None:
            requirement = self.repository.get_activity_requirement(requirement_id)
            if requirement is None:
                raise ValueError("所选材料类型不存在，请刷新活动后重试。")
        destination_dir = (self.files_root / student_id).resolve()
        if self.files_root not in destination_dir.parents:
            raise ValueError("无效的学生存储目录。")
        destination_dir.mkdir(parents=True, exist_ok=True)
        results: list[Material] = []
        for source in source_paths:
            source = source.resolve()
            if not source.is_file():
                raise FileNotFoundError(f"文件不存在或不是普通文件：{source.name}")
            stored_name = (
                f"{sanitize_filename(requirement.name, '材料')}{source.suffix}"
                if requirement is not None
                else sanitize_filename(source.name, "材料")
            )
            destination = unique_path(destination_dir / stored_name)
            shutil.copy2(source, destination)
            try:
                results.append(
                    self.repository.add_material(
                        student_id, destination.name, destination, requirement_id
                    )
                )
            except Exception:
                destination.unlink(missing_ok=True)
                raise
        return results

    def remove_material(self, material_id: str) -> bool:
        material = self.repository.delete_material(material_id)
        if material is None:
            return False
        path = material.stored_path.resolve()
        if self.files_root in path.parents:
            path.unlink(missing_ok=True)
        return True

    def remove_student_storage(self, student_ids: list[str]) -> None:
        """清理已被明确替换的学生名单对应的内部材料副本。"""
        for student_id in student_ids:
            directory = (self.files_root / student_id).resolve()
            if self.files_root not in directory.parents or not directory.is_dir():
                continue
            shutil.rmtree(directory)
