"""应用领域模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Activity:
    """一次材料收集活动。"""

    id: str
    name: str
    created_at: datetime
    status: str = "active"
    student_count: int = 0
    submitted_count: int = 0

    @property
    def pending_count(self) -> int:
        return self.student_count - self.submitted_count


@dataclass(frozen=True, slots=True)
class Student:
    """活动中的一名学生。"""

    id: str
    activity_id: str
    name: str
    student_number: str | None
    created_at: datetime
    updated_at: datetime
    file_count: int = 0
    requirement_count: int = 0
    required_count: int = 0
    fulfilled_count: int = 0

    @property
    def submitted(self) -> bool:
        if self.requirement_count:
            return self.fulfilled_count >= self.required_count
        return self.file_count > 0


@dataclass(frozen=True, slots=True)
class ActivityRequirement:
    """活动中需要收取的一类材料。"""

    id: str
    activity_id: str
    name: str
    position: int
    required: bool = True


@dataclass(frozen=True, slots=True)
class Material:
    """已经复制到应用数据目录的学生材料。"""

    id: str
    student_id: str
    original_name: str
    stored_path: Path
    created_at: datetime
    requirement_id: str | None = None
    requirement_name: str | None = None
