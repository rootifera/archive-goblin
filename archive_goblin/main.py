from __future__ import annotations

import sys
from importlib import resources

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from archive_goblin.ui.main_window import MainWindow


def _build_app_icon() -> QIcon:
    icon = QIcon()
    icons_dir = resources.files("archive_goblin").joinpath("icons")
    for file_name, size in (("small.png", 32), ("mid.png", 128), ("large.png", 512)):
        icon_path = icons_dir.joinpath(file_name)
        icon.addFile(str(icon_path), QSize(size, size))
    return icon


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Archive Goblin")
    app_icon = _build_app_icon()
    app.setWindowIcon(app_icon)
    window = MainWindow()
    window.setWindowIcon(app_icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
