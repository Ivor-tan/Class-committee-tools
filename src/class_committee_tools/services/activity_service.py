"""活动相关业务规则。"""

from __future__ import annotations

import re

from class_committee_tools.models import Activity
from class_committee_tools.repositories import DatabaseRepository

INVALID_ACTIVITY_NAME = re.compile(r'[\\/:*?"<>|]')


class ActivityService:
    def __init__(self, repository: DatabaseRepository) -> None:
        self.repository = repository

    def create(
        self,
        name: str,
        requirements: list[tuple[str, bool]] | None = None,
    ) -> Activity:
        normalized = self.validate_name(name)
        normalized_requirements = self.validate_requirements(requirements or [])
        activity = self.repository.create_activity(normalized)
        self.repository.add_activity_requirements(activity.id, normalized_requirements)
        return activity

    def rename(self, activity_id: str, name: str) -> None:
        self.repository.update_activity_name(activity_id, self.validate_name(name))

    def set_completed(self, activity_id: str, completed: bool) -> None:
        self.repository.update_activity_status(
            activity_id, "completed" if completed else "active"
        )

    @staticmethod
    def validate_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("活动名称不能为空。")
        if INVALID_ACTIVITY_NAME.search(normalized):
            raise ValueError('活动名称不能包含 \\ / : * ? " < > |。')
        return normalized

    @staticmethod
    def validate_requirements(
        requirements: list[tuple[str, bool]],
    ) -> list[tuple[str, bool]]:
        normalized: list[tuple[str, bool]] = []
        seen: set[str] = set()
        for raw_name, required in requirements:
            name = raw_name.strip()
            if not name:
                continue
            if len(name) > 100:
                raise ValueError("需要收取的文件名称不能超过 100 个字符。")
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append((name, bool(required)))
        return normalized
