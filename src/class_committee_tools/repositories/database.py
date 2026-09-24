"""SQLite 数据存储。"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from class_committee_tools.models import Activity, ActivityRequirement, Material, Student


class DatabaseRepository:
    """封装活动、学生和材料的数据库访问。"""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                );
                CREATE TABLE IF NOT EXISTS students (
                    id TEXT PRIMARY KEY,
                    activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    student_number TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_student_identity
                    ON students(activity_id, name, COALESCE(student_number, ''));
                CREATE TABLE IF NOT EXISTS activity_requirements (
                    id TEXT PRIMARY KEY,
                    activity_id TEXT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    required INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(activity_id, name)
                );
                CREATE TABLE IF NOT EXISTS materials (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                """
            )
            activity_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(activities)").fetchall()
            }
            if "status" not in activity_columns:
                connection.execute(
                    "ALTER TABLE activities ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
                )
            material_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(materials)").fetchall()
            }
            if "requirement_id" not in material_columns:
                connection.execute("ALTER TABLE materials ADD COLUMN requirement_id TEXT")
            requirement_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(activity_requirements)"
                ).fetchall()
            }
            if "required" not in requirement_columns:
                connection.execute(
                    """
                    ALTER TABLE activity_requirements
                    ADD COLUMN required INTEGER NOT NULL DEFAULT 1
                    """
                )

    def create_activity(self, name: str) -> Activity:
        now = datetime.now().astimezone()
        activity = Activity(str(uuid4()), name, now, "active")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO activities(id, name, created_at, status) VALUES (?, ?, ?, ?)",
                (
                    activity.id,
                    activity.name,
                    activity.created_at.isoformat(),
                    activity.status,
                ),
            )
        return activity

    def list_activities(self) -> list[Activity]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT a.id, a.name, a.created_at, a.status,
                       COUNT(DISTINCT s.id) AS student_count,
                       COUNT(DISTINCT CASE WHEN m.id IS NOT NULL THEN s.id END) AS submitted_count
                FROM activities a
                LEFT JOIN students s ON s.activity_id = a.id
                LEFT JOIN materials m ON m.student_id = s.id
                GROUP BY a.id
                ORDER BY a.created_at DESC
                """
            ).fetchall()
        return [
            Activity(
                row["id"],
                row["name"],
                datetime.fromisoformat(row["created_at"]),
                row["status"],
                row["student_count"],
                row["submitted_count"],
            )
            for row in rows
        ]

    def get_activity(self, activity_id: str) -> Activity | None:
        return next(
            (item for item in self.list_activities() if item.id == activity_id),
            None,
        )

    def add_activity_requirements(
        self, activity_id: str, requirements: list[tuple[str, bool]]
    ) -> None:
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO activity_requirements(id, activity_id, name, position, required)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (str(uuid4()), activity_id, name, position, int(required))
                    for position, (name, required) in enumerate(requirements)
                ],
            )

    def list_activity_requirements(self, activity_id: str) -> list[ActivityRequirement]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, activity_id, name, position, required
                FROM activity_requirements
                WHERE activity_id = ?
                ORDER BY position, name
                """,
                (activity_id,),
            ).fetchall()
        return [
            ActivityRequirement(
                row["id"],
                row["activity_id"],
                row["name"],
                row["position"],
                bool(row["required"]),
            )
            for row in rows
        ]

    def get_activity_requirement(self, requirement_id: str) -> ActivityRequirement | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, activity_id, name, position, required
                FROM activity_requirements
                WHERE id = ?
                """,
                (requirement_id,),
            ).fetchone()
        if row is None:
            return None
        return ActivityRequirement(
            row["id"],
            row["activity_id"],
            row["name"],
            row["position"],
            bool(row["required"]),
        )

    def update_activity_name(self, activity_id: str, name: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE activities SET name = ? WHERE id = ?", (name, activity_id)
            )
            if cursor.rowcount == 0:
                raise ValueError("要编辑的活动不存在。")

    def update_activity_status(self, activity_id: str, status: str) -> None:
        if status not in {"active", "completed"}:
            raise ValueError("无效的活动状态。")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE activities SET status = ? WHERE id = ?", (status, activity_id)
            )
            if cursor.rowcount == 0:
                raise ValueError("要更新的活动不存在。")

    def delete_activity(self, activity_id: str) -> list[str]:
        """删除活动数据，并返回需要清理文件的学生 ID。"""
        with self._connect() as connection:
            student_rows = connection.execute(
                "SELECT id FROM students WHERE activity_id = ?", (activity_id,)
            ).fetchall()
            cursor = connection.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
            if cursor.rowcount == 0:
                raise ValueError("要删除的活动不存在。")
        return [row["id"] for row in student_rows]

    def add_students(
        self,
        activity_id: str,
        entries: list[tuple[str, str | None]],
        *,
        replace: bool = False,
    ) -> tuple[int, int]:
        """添加学生，返回成功数和重复忽略数。"""
        now = datetime.now().astimezone().isoformat()
        added = 0
        ignored = 0
        with self._connect() as connection:
            if replace:
                connection.execute("DELETE FROM students WHERE activity_id = ?", (activity_id,))
            for name, student_number in entries:
                try:
                    connection.execute(
                        """
                        INSERT INTO students(
                            id, activity_id, name, student_number, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (str(uuid4()), activity_id, name, student_number, now, now),
                    )
                    added += 1
                except sqlite3.IntegrityError:
                    ignored += 1
        return added, ignored

    def list_students(self, activity_id: str) -> list[Student]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.*, COUNT(DISTINCT m.id) AS file_count,
                       (
                           SELECT COUNT(*) FROM activity_requirements r
                           WHERE r.activity_id = s.activity_id
                       ) AS requirement_count,
                       (
                           SELECT COUNT(*) FROM activity_requirements r
                           WHERE r.activity_id = s.activity_id AND r.required = 1
                       ) AS required_count,
                       COUNT(DISTINCT CASE WHEN r.required = 1 THEN m.requirement_id END)
                           AS fulfilled_count
                FROM students s
                LEFT JOIN materials m ON m.student_id = s.id
                LEFT JOIN activity_requirements r ON r.id = m.requirement_id
                WHERE s.activity_id = ?
                GROUP BY s.id
                ORDER BY s.name COLLATE NOCASE, s.student_number
                """,
                (activity_id,),
            ).fetchall()
        return [
            Student(
                row["id"],
                row["activity_id"],
                row["name"],
                row["student_number"],
                datetime.fromisoformat(row["created_at"]),
                datetime.fromisoformat(row["updated_at"]),
                row["file_count"],
                row["requirement_count"],
                row["required_count"],
                row["fulfilled_count"],
            )
            for row in rows
        ]

    def add_material(
        self,
        student_id: str,
        original_name: str,
        stored_path: Path,
        requirement_id: str | None = None,
    ) -> Material:
        now = datetime.now().astimezone()
        material = Material(
            str(uuid4()), student_id, original_name, stored_path, now, requirement_id
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO materials(
                    id, student_id, original_name, stored_path, created_at, requirement_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    material.id,
                    material.student_id,
                    material.original_name,
                    str(material.stored_path),
                    material.created_at.isoformat(),
                    material.requirement_id,
                ),
            )
            connection.execute(
                "UPDATE students SET updated_at = ? WHERE id = ?",
                (now.isoformat(), student_id),
            )
        return material

    def list_materials(self, student_id: str) -> list[Material]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT m.*, r.name AS requirement_name
                FROM materials m
                LEFT JOIN activity_requirements r ON r.id = m.requirement_id
                WHERE m.student_id = ?
                ORDER BY m.created_at
                """,
                (student_id,),
            ).fetchall()
        return [
            Material(
                row["id"],
                row["student_id"],
                row["original_name"],
                Path(row["stored_path"]),
                datetime.fromisoformat(row["created_at"]),
                row["requirement_id"],
                row["requirement_name"],
            )
            for row in rows
        ]

    def delete_material(self, material_id: str) -> Material | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT m.*, r.name AS requirement_name
                FROM materials m
                LEFT JOIN activity_requirements r ON r.id = m.requirement_id
                WHERE m.id = ?
                """,
                (material_id,),
            ).fetchone()
            if row is None:
                return None
            connection.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        return Material(
            row["id"],
            row["student_id"],
            row["original_name"],
            Path(row["stored_path"]),
            datetime.fromisoformat(row["created_at"]),
            row["requirement_id"],
            row["requirement_name"],
        )
