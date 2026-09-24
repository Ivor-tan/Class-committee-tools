"""PyQt6 应用程序的创建与启动逻辑。"""

from __future__ import annotations

import logging
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox

from class_committee_tools.repositories import DatabaseRepository
from class_committee_tools.services import ActivityService, ExportService, FileService
from class_committee_tools.settings import (
    APPLICATION_NAME,
    ORGANIZATION_NAME,
    load_settings,
    stylesheet_for_theme,
)
from class_committee_tools.ui import MainWindow
from class_committee_tools.utils import get_resource_path


def run() -> int:
    settings = load_settings()
    app_data = settings.data_directory
    app_data.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=app_data / "application.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    application = QApplication(sys.argv)
    application.setApplicationName(APPLICATION_NAME)
    application.setOrganizationName(ORGANIZATION_NAME)
    application.setWindowIcon(QIcon(str(get_resource_path("resources/app-icon.png"))))
    application.setStyleSheet(stylesheet_for_theme(settings.theme))
    try:
        repository = DatabaseRepository(app_data / "class_committee.db")
        window = MainWindow(
            repository,
            ActivityService(repository),
            FileService(repository, app_data / "files"),
            ExportService(repository),
            settings,
        )
        window.show()
        return application.exec()
    except Exception as exc:
        logging.exception("应用启动失败")
        QMessageBox.critical(None, "启动失败", f"应用无法启动：{exc}")
        return 1
