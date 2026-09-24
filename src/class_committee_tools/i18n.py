"""简体中文与英文界面文本。"""

from __future__ import annotations

ENGLISH_TEXT = {
    "班级材料收集工具": "Class File Collector",
    "创建新的材料收集活动": "Create a new collection activity",
    "例如：2026 年奖学金申请材料收集": "Example: 2026 Scholarship Documents",
    "创建活动": "Create Activity",
    "设置": "Settings",
    "历史活动（双击可打开）": "Activities (double-click to open)",
    "活动名称": "Activity Name",
    "创建时间": "Created At",
    "状态": "Status",
    "学生总数": "Students",
    "已提交": "Submitted",
    "未提交": "Pending",
    "操作": "Actions",
    "打开选中的活动": "Open Selected Activity",
    "← 返回主页": "← Home",
    "导入 Excel 名单": "Import Excel List",
    "导出学生压缩包": "Export Student ZIPs",
    "导出当前数据": "Export Current Data",
    "按姓名或学号搜索": "Search by name or student ID",
    "全部状态": "All Statuses",
    "姓名": "Name",
    "学号": "Student ID",
    "提交状态": "Submission Status",
    "材料进度": "Material Progress",
    "最后更新": "Last Updated",
    "未完成": "In Progress",
    "已完成": "Completed",
    "编辑": "Edit",
    "删除": "Delete",
    "添加文件": "Add File",
    "查看": "View",
    "数据仅保存在本机": "Data is stored locally only",
}


def translate(text: str, language: str) -> str:
    if language == "en_US":
        return ENGLISH_TEXT.get(text, text)
    return text
