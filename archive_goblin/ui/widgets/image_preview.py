from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea


class ImagePreview(QScrollArea):
    def __init__(self) -> None:
        super().__init__()
        self._label = QLabel("No preview available")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumHeight(260)
        self.setWidget(self._label)
        self.setWidgetResizable(True)

    def load_image(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.clear()
            return

        scaled = pixmap.scaled(
            420,
            420,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._label.setPixmap(scaled)
        self._label.setText("")

    def clear(self) -> None:
        self._label.setPixmap(QPixmap())
        self._label.setText("No preview available")
