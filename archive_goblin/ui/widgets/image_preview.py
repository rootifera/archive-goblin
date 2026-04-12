from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea


class ImagePreview(QScrollArea):
    def __init__(self) -> None:
        super().__init__()
        self._pixmap: QPixmap | None = None
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

        self._pixmap = pixmap
        self._update_scaled_pixmap()

    def clear(self) -> None:
        self._pixmap = None
        self._label.setPixmap(QPixmap())
        self._label.setText("No preview available")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        if self._pixmap is None:
            return

        viewport_size = self.viewport().size()
        target_size = QSize(
            max(1, viewport_size.width() - 12),
            max(1, viewport_size.height() - 12),
        )
        scaled = self._pixmap.scaled(
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._label.setPixmap(scaled)
        self._label.setText("")
