from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from class_committee_tools.services import read_student_workbook


def test_read_student_workbook_ignores_empty_and_duplicate_rows(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["姓名", "学号"])
    sheet.append([" 张三 ", "001"])
    sheet.append(["张三", "001"])
    sheet.append([None, "002"])
    sheet.append(["李四", None])
    path = tmp_path / "students.xlsx"
    workbook.save(path)

    preview = read_student_workbook(path)

    assert preview.entries == [("张三", "001"), ("李四", None)]
    assert preview.ignored_duplicates == 1
    assert preview.ignored_empty == 1
    assert preview.number_header == "学号"
