from __future__ import annotations

from PySide6.QtGui import QColor, QBrush
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class UploadProgressDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Uploading to Archive.org")
        self.resize(760, 520)

        layout = QVBoxLayout(self)
        self.status_label = QLabel("Preparing upload...")
        self.overall_progress_label = QLabel("Overall Progress")
        self.overall_progress_bar = QProgressBar()
        self.current_item_progress_label = QLabel("Current Item")
        self.current_file_label = QLabel("Current file: —")
        self.current_item_progress_bar = QProgressBar()
        self.progress_list = QListWidget()
        self.help_label = QLabel(
            "Archive.org uploads can be slow, especially for large files. Please be patient while the current item is uploading."
        )
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color:#7c8796;")

        layout.addWidget(self.status_label)
        layout.addWidget(self.overall_progress_label)
        layout.addWidget(self.overall_progress_bar)
        layout.addWidget(self.current_item_progress_label)
        layout.addWidget(self.current_file_label)
        layout.addWidget(self.current_item_progress_bar)
        layout.addWidget(self.progress_list, 1)
        layout.addWidget(self.help_label)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttons.button(QDialogButtonBox.Close).setEnabled(False)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)
        self.buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(self.buttons)

    def _set_item_state(self, item: QListWidgetItem, prefix: str, file_name: str, color: str) -> None:
        item.setText(f"[{prefix}] {file_name}")
        item.setForeground(QBrush(QColor(color)))

    def start(self, file_names: list[str]) -> None:
        self.status_label.setText(f"Uploading {len(file_names)} file(s)...")
        self.current_file_label.setText("Current file: —")
        self.overall_progress_bar.setMaximum(max(1, len(file_names)))
        self.overall_progress_bar.setValue(0)
        self.current_item_progress_bar.setRange(0, 1)
        self.current_item_progress_bar.setValue(0)
        self.progress_list.clear()
        for name in file_names:
            item = QListWidgetItem()
            self._set_item_state(item, "Pending", name, "#9aa3ad")
            self.progress_list.addItem(item)
        self.buttons.button(QDialogButtonBox.Close).setEnabled(False)

    def mark_file_started(self, index: int, file_name: str) -> None:
        self.current_file_label.setText(f"Current file: {file_name}")
        self.current_item_progress_bar.setRange(0, 0)
        item = self.progress_list.item(index)
        if item is not None:
            self._set_item_state(item, "Uploading", file_name, "#d9b46b")

    def mark_file_finished(self, index: int, file_name: str, completed: int) -> None:
        self.overall_progress_bar.setValue(completed)
        self.current_item_progress_bar.setRange(0, 1)
        self.current_item_progress_bar.setValue(0)
        item = self.progress_list.item(index)
        if item is not None:
            self._set_item_state(item, "Done", file_name, "#6fb27f")
        self.current_file_label.setText("Current file: waiting for next file")

    def finish_success(self, message: str) -> None:
        self.status_label.setText(message)
        self.current_file_label.setText("Current file: Complete")
        self.current_item_progress_bar.setRange(0, 1)
        self.current_item_progress_bar.setValue(1)
        self.buttons.button(QDialogButtonBox.Close).setEnabled(True)

    def finish_failure(self, message: str) -> None:
        self.status_label.setText(message)
        self.current_item_progress_bar.setRange(0, 1)
        self.current_item_progress_bar.setValue(0)
        self.buttons.button(QDialogButtonBox.Close).setEnabled(True)
