from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from archive_goblin.models.file_item import FileItem, FileStatus
from archive_goblin.models.rule import FileType, file_type_label
from archive_goblin.ui.widgets.file_table import FileTable
from archive_goblin.ui.widgets.image_preview import ImagePreview


class FilesPage(QWidget):
    folder_chosen = Signal(object)
    apply_requested = Signal()
    rescan_requested = Signal()
    item_edited = Signal(int, dict)

    def __init__(self) -> None:
        super().__init__()
        self._files: list[FileItem] = []
        self._visible_rows: list[int] = []
        self._folder: Path | None = None
        self._current_row = -1
        self._updating = False

        root_layout = QVBoxLayout(self)

        toolbar_layout = QHBoxLayout()
        self.open_button = QPushButton("Open Folder")
        self.rescan_button = QPushButton("Rescan")
        self.apply_button = QPushButton("Apply Renames")
        self.hide_disk_images_checkbox = QCheckBox("Hide Disk Images")
        self.hide_disk_images_checkbox.setChecked(True)
        self.summary_label = QLabel("0 files")
        toolbar_layout.addWidget(self.open_button)
        toolbar_layout.addWidget(self.rescan_button)
        toolbar_layout.addWidget(self.apply_button)
        toolbar_layout.addWidget(self.hide_disk_images_checkbox)
        toolbar_layout.addWidget(self.summary_label)
        root_layout.addLayout(toolbar_layout)

        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        self.folder_path_edit.setPlaceholderText("No folder selected")
        root_layout.addWidget(self.folder_path_edit)

        splitter = QSplitter()
        self.file_table = FileTable()
        splitter.addWidget(self.file_table)

        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        self.preview = ImagePreview()
        detail_layout.addWidget(self.preview, 1)

        form_layout = QFormLayout()
        self.original_name_label = QLabel("Select a file")
        self.detected_type_label = QLabel("—")
        self.full_name_edit = QLineEdit()
        self.full_name_edit.setReadOnly(True)
        self.cover_copy_edit = QLineEdit()
        self.cover_copy_edit.setReadOnly(True)
        self.set_as_cover_image_checkbox = QCheckBox("Set as cover image")
        self.do_not_rename_checkbox = QCheckBox("Do not rename")
        self.status_label = QLabel("—")
        form_layout.addRow("Original", self.original_name_label)
        form_layout.addRow("Detected Type", self.detected_type_label)
        form_layout.addRow("Output", self.full_name_edit)
        form_layout.addRow("Cover Copy", self.cover_copy_edit)
        form_layout.addRow("", self.set_as_cover_image_checkbox)
        form_layout.addRow("", self.do_not_rename_checkbox)
        form_layout.addRow("Status", self.status_label)
        detail_layout.addLayout(form_layout)
        splitter.addWidget(detail_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root_layout.addWidget(splitter, 1)

        self.open_button.clicked.connect(self._choose_folder)
        self.rescan_button.clicked.connect(self.rescan_requested.emit)
        self.apply_button.clicked.connect(self.apply_requested.emit)
        self.file_table.row_selected.connect(self._on_row_selected)
        self.hide_disk_images_checkbox.toggled.connect(self._apply_filter)
        self.set_as_cover_image_checkbox.toggled.connect(self._emit_detail_change)
        self.do_not_rename_checkbox.toggled.connect(self._emit_detail_change)

    def set_files(self, folder: Path | None, files: list[FileItem]) -> None:
        self._folder = folder
        self._files = list(files)
        self.folder_path_edit.setText(str(folder) if folder is not None else "")
        self._apply_filter()

    def _choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Open Folder")
        if selected:
            self.folder_chosen.emit(Path(selected))

    def _on_row_selected(self, row: int) -> None:
        self._current_row = self._visible_rows[row] if 0 <= row < len(self._visible_rows) else -1
        self._refresh_details()

    def _emit_detail_change(self) -> None:
        if self._updating or self._current_row < 0 or self._current_row >= len(self._files):
            return

        changes = {
            "set_as_cover_image": self.set_as_cover_image_checkbox.isChecked(),
            "do_not_rename": self.do_not_rename_checkbox.isChecked(),
        }
        self.item_edited.emit(self._current_row, changes)

    def _refresh_details(self) -> None:
        self._updating = True
        try:
            if self._current_row < 0 or self._current_row >= len(self._files):
                self.original_name_label.setText("Select a file")
                self.detected_type_label.setText("—")
                self.full_name_edit.clear()
                self.cover_copy_edit.clear()
                self.set_as_cover_image_checkbox.setChecked(False)
                self.do_not_rename_checkbox.setChecked(False)
                self.status_label.setText("—")
                self.preview.clear()
                return

            file_item = self._files[self._current_row]
            self.original_name_label.setText(file_item.original_name)
            self.detected_type_label.setText(file_type_label(file_item.type))
            self.full_name_edit.setText(file_item.proposed_name or "")
            self.cover_copy_edit.setText(file_item.cover_image_name or "")
            self.set_as_cover_image_checkbox.setChecked(file_item.set_as_cover_image)
            self.do_not_rename_checkbox.setChecked(file_item.do_not_rename)
            self.status_label.setText(self._status_text(file_item))
            self.preview.load_image(file_item.path)
            allow_cover_copy = (
                not file_item.is_protected
                and file_item.type is not FileType.DISK_IMAGE
                and not file_item.is_cover_image_copy
            )
            self.set_as_cover_image_checkbox.setEnabled(allow_cover_copy)
            self.do_not_rename_checkbox.setEnabled(not file_item.is_protected and not file_item.is_cover_image_copy)
        finally:
            self._updating = False

    def _apply_filter(self) -> None:
        previous_name = None
        if 0 <= self._current_row < len(self._files):
            previous_name = self._files[self._current_row].original_name

        visible_files: list[FileItem] = []
        self._visible_rows = []
        hide_disk_images = self.hide_disk_images_checkbox.isChecked()
        for index, file_item in enumerate(self._files):
            if hide_disk_images and file_item.type is FileType.DISK_IMAGE:
                continue
            self._visible_rows.append(index)
            visible_files.append(file_item)

        self.file_table.set_files(visible_files)
        self.summary_label.setText(self._summarize(visible_files))

        new_visible_row = 0 if visible_files else -1
        if previous_name is not None:
            for visible_row, file_item in enumerate(visible_files):
                if file_item.original_name == previous_name:
                    new_visible_row = visible_row
                    break

        self._current_row = self._visible_rows[new_visible_row] if new_visible_row >= 0 else -1
        self.file_table.select_row(new_visible_row)
        self._refresh_details()

    def _status_text(self, file_item: FileItem) -> str:
        if file_item.status is FileStatus.CONFLICT and file_item.conflict_message:
            return f"{file_item.status.value.replace('_', ' ').title()}: {file_item.conflict_message}"
        return file_item.status.value.replace("_", " ").title()

    def _summarize(self, files: list[FileItem]) -> str:
        if not files:
            return "0 files"

        ready_count = sum(1 for file_item in files if file_item.status is FileStatus.READY)
        done_count = sum(1 for file_item in files if file_item.status is FileStatus.DONE)
        conflict_count = sum(1 for file_item in files if file_item.status is FileStatus.CONFLICT)
        protected_count = sum(1 for file_item in files if file_item.status is FileStatus.PROTECTED)
        return (
            f"{len(files)} files | {ready_count} ready | {done_count} done | "
            f"{conflict_count} conflicts | {protected_count} protected"
        )
