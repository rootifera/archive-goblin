from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QFrame,
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
        self.previous_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.hide_protected_files_checkbox = QCheckBox("Hide Protected Files")
        self.hide_protected_files_checkbox.setChecked(True)
        self.summary_label = QLabel("0 files")
        self.toolbar_divider = QFrame()
        self.toolbar_divider.setFrameShape(QFrame.VLine)
        self.toolbar_divider.setFrameShadow(QFrame.Sunken)
        toolbar_layout.addWidget(self.open_button)
        toolbar_layout.addWidget(self.rescan_button)
        toolbar_layout.addWidget(self.apply_button)
        toolbar_layout.addWidget(self.previous_button)
        toolbar_layout.addWidget(self.next_button)
        toolbar_layout.addWidget(self.hide_protected_files_checkbox)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(self.toolbar_divider)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addStretch(1)
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
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        self.original_name_label = QLabel("Select a file")
        self.original_name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.detected_type_label = QLabel("—")
        self.detected_type_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.full_name_edit = QLineEdit()
        self.full_name_edit.setReadOnly(True)
        self.full_name_edit.setPlaceholderText("Enable protected rename to edit the final filename")
        self.cover_copy_edit = QLineEdit()
        self.cover_copy_edit.setReadOnly(True)
        self.allow_protected_rename_checkbox = QCheckBox("Allow rename for protected file")
        self.set_as_cover_image_checkbox = QCheckBox("Set as cover image")
        self.do_not_rename_checkbox = QCheckBox("Do not rename")
        self.status_label = QLabel("—")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_label.setFrameShape(QFrame.StyledPanel)
        self.status_label.setMargin(6)
        self.review_note_title_label = QLabel("Review Note")
        self.review_note_title_label.setStyleSheet("font-weight:600;")
        self.review_note_label = QLabel("")
        self.review_note_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.review_note_label.setWordWrap(True)
        self.review_note_label.setStyleSheet("color:#7c8796;")
        self.review_note_label.setFrameShape(QFrame.StyledPanel)
        self.review_note_label.setMargin(8)
        self.review_note_label.setMinimumHeight(72)
        form_layout.addRow("Original", self.original_name_label)
        form_layout.addRow("Detected Type", self.detected_type_label)
        form_layout.addRow("Final Name", self.full_name_edit)
        form_layout.addRow("Cover Copy", self.cover_copy_edit)
        form_layout.addRow("", self.allow_protected_rename_checkbox)
        form_layout.addRow("", self.set_as_cover_image_checkbox)
        form_layout.addRow("", self.do_not_rename_checkbox)
        form_layout.addRow("Status", self.status_label)
        detail_layout.addLayout(form_layout)
        detail_layout.addWidget(self.review_note_title_label)
        detail_layout.addWidget(self.review_note_label)
        splitter.addWidget(detail_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root_layout.addWidget(splitter, 1)

        self.shortcut_hint_label = QLabel(
            "Shortcuts: J/K navigate • C toggle cover image • D toggle do not rename"
        )
        self.shortcut_hint_label.setStyleSheet("color:#7c8796; padding-top:4px;")
        root_layout.addWidget(self.shortcut_hint_label)

        self.open_button.clicked.connect(self._choose_folder)
        self.rescan_button.clicked.connect(self.rescan_requested.emit)
        self.apply_button.clicked.connect(self.apply_requested.emit)
        self.file_table.row_selected.connect(self._on_row_selected)
        self.hide_protected_files_checkbox.toggled.connect(self._apply_filter)
        self.allow_protected_rename_checkbox.toggled.connect(self._emit_detail_change)
        self.set_as_cover_image_checkbox.toggled.connect(self._emit_detail_change)
        self.do_not_rename_checkbox.toggled.connect(self._emit_detail_change)
        self.full_name_edit.editingFinished.connect(self._emit_name_change)
        self.full_name_edit.returnPressed.connect(self._emit_name_change)
        self.previous_button.clicked.connect(lambda: self._step_selection(-1))
        self.next_button.clicked.connect(lambda: self._step_selection(1))

        self._install_shortcuts()

    def set_files(self, folder: Path | None, files: list[FileItem]) -> None:
        self._folder = folder
        self._files = list(files)
        self.folder_path_edit.setText(str(folder) if folder is not None else "")
        self._apply_filter()

    def _choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Open Folder", str(Path.home()))
        if selected:
            self.folder_chosen.emit(Path(selected))

    def _on_row_selected(self, row: int) -> None:
        self._current_row = self._visible_rows[row] if 0 <= row < len(self._visible_rows) else -1
        self._refresh_details()
        self._update_navigation_buttons()

    def _emit_detail_change(self) -> None:
        if self._updating or self._current_row < 0 or self._current_row >= len(self._files):
            return

        allow_protected_rename = self.allow_protected_rename_checkbox.isChecked()
        if allow_protected_rename and self.do_not_rename_checkbox.isChecked():
            self.do_not_rename_checkbox.setChecked(False)

        changes = {
            "allow_protected_rename": allow_protected_rename,
            "set_as_cover_image": self.set_as_cover_image_checkbox.isChecked(),
            "do_not_rename": self.do_not_rename_checkbox.isChecked(),
        }
        self.item_edited.emit(self._current_row, changes)

    def _emit_name_change(self) -> None:
        if self._updating or self._current_row < 0 or self._current_row >= len(self._files):
            return

        file_item = self._files[self._current_row]
        is_manual_name_editable = file_item.is_protected and file_item.allow_protected_rename and not file_item.is_cover_image_copy
        if not is_manual_name_editable:
            return

        self.item_edited.emit(
            self._current_row,
            {"manual_proposed_name": self.full_name_edit.text().strip()},
        )

    def _refresh_details(self) -> None:
        self._updating = True
        try:
            if self._current_row < 0 or self._current_row >= len(self._files):
                self.original_name_label.setText("Select a file")
                self.detected_type_label.setText("—")
                self.full_name_edit.clear()
                self.full_name_edit.setReadOnly(True)
                self.cover_copy_edit.clear()
                self.allow_protected_rename_checkbox.setChecked(False)
                self.set_as_cover_image_checkbox.setChecked(False)
                self.do_not_rename_checkbox.setChecked(False)
                self.status_label.setText("—")
                self.status_label.setStyleSheet("")
                self.review_note_label.setText("")
                self.preview.clear()
                self._update_navigation_buttons()
                return

            file_item = self._files[self._current_row]
            self.original_name_label.setText(file_item.original_name)
            self.detected_type_label.setText(file_type_label(file_item.type))
            self.full_name_edit.setText(file_item.proposed_name or "")
            self.cover_copy_edit.setText(file_item.cover_image_name or "")
            self.allow_protected_rename_checkbox.setChecked(file_item.allow_protected_rename)
            self.set_as_cover_image_checkbox.setChecked(file_item.set_as_cover_image)
            self.do_not_rename_checkbox.setChecked(file_item.do_not_rename)
            self.status_label.setText(self._status_text(file_item))
            self.status_label.setStyleSheet(self._status_style(file_item.status))
            self.review_note_label.setText(self._review_note_text(file_item))
            self.preview.load_image(file_item.path)
            is_manual_name_editable = (
                file_item.is_protected
                and file_item.allow_protected_rename
                and not file_item.is_cover_image_copy
            )
            self.full_name_edit.setReadOnly(not is_manual_name_editable)
            self.full_name_edit.setPlaceholderText(
                "Press Enter to apply a custom filename for this protected file"
                if is_manual_name_editable
                else "Enable protected rename to edit the final filename"
            )
            allow_cover_copy = (
                (not file_item.is_protected or file_item.allow_protected_rename)
                and file_item.type is not FileType.DISK_IMAGE
                and not file_item.is_cover_image_copy
            )
            self.allow_protected_rename_checkbox.setEnabled(file_item.is_protected and not file_item.is_cover_image_copy)
            self.set_as_cover_image_checkbox.setEnabled(allow_cover_copy)
            self.do_not_rename_checkbox.setEnabled(
                not file_item.allow_protected_rename
                and (not file_item.is_protected or file_item.allow_protected_rename)
                and not file_item.is_cover_image_copy
            )
            self._update_navigation_buttons()
        finally:
            self._updating = False

    def _apply_filter(self) -> None:
        previous_name = None
        if 0 <= self._current_row < len(self._files):
            previous_name = self._files[self._current_row].original_name

        visible_files: list[FileItem] = []
        self._visible_rows = []
        hide_protected_files = self.hide_protected_files_checkbox.isChecked()
        for index, file_item in enumerate(self._files):
            if hide_protected_files and file_item.is_protected:
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
        self._update_navigation_buttons()

    def _status_text(self, file_item: FileItem) -> str:
        if file_item.status is FileStatus.CONFLICT and file_item.conflict_message:
            return f"{self._display_status_text(file_item.status)}: {file_item.conflict_message}"
        return self._display_status_text(file_item.status)

    def _status_style(self, status: FileStatus) -> str:
        if status is FileStatus.CONFLICT:
            return "background:#4c1d1d; color:#ffb4b4; font-weight:600;"
        if status is FileStatus.READY:
            return "background:#173225; color:#b7f7c2;"
        if status is FileStatus.DONE:
            return "background:#24303d; color:#c5ced8;"
        if status is FileStatus.PROTECTED:
            return "background:#45311a; color:#ffd79a;"
        if status is FileStatus.UNMATCHED:
            return "background:#2a3441; color:#d5dbe3;"
        if status is FileStatus.IGNORED:
            return "background:#2d3642; color:#b0bac5;"
        return ""

    def _display_status_text(self, status: FileStatus) -> str:
        if status is FileStatus.READY:
            return "Ready for Rename"
        return status.value.replace("_", " ").title()

    def _summarize(self, files: list[FileItem]) -> str:
        if not files:
            return "0 files"

        ready_count = sum(1 for file_item in files if file_item.status is FileStatus.READY)
        done_count = sum(1 for file_item in files if file_item.status is FileStatus.DONE)
        conflict_count = sum(1 for file_item in files if file_item.status is FileStatus.CONFLICT)
        protected_count = sum(1 for file_item in files if file_item.status is FileStatus.PROTECTED)
        unmatched_count = sum(1 for file_item in files if file_item.status is FileStatus.UNMATCHED)
        return (
            f"{len(files)} files | {ready_count} ready | {done_count} done | "
            f"{conflict_count} conflicts | {unmatched_count} unmatched | {protected_count} protected"
        )

    def _install_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key_J), self, activated=lambda: self._step_selection(1))
        QShortcut(QKeySequence(Qt.Key_K), self, activated=lambda: self._step_selection(-1))
        QShortcut(QKeySequence(Qt.Key_D), self, activated=self._toggle_do_not_rename)
        QShortcut(QKeySequence(Qt.Key_C), self, activated=self._toggle_cover_image)

    def _step_selection(self, direction: int) -> None:
        if not self._visible_rows:
            return

        current_visible_row = self._visible_row_for_current_selection()
        if current_visible_row < 0:
            target_row = 0
        else:
            target_row = max(0, min(len(self._visible_rows) - 1, current_visible_row + direction))
        self.file_table.select_row(target_row)

    def _visible_row_for_current_selection(self) -> int:
        if self._current_row < 0:
            return -1
        for visible_row, file_index in enumerate(self._visible_rows):
            if file_index == self._current_row:
                return visible_row
        return -1

    def _toggle_do_not_rename(self) -> None:
        if not self.do_not_rename_checkbox.isEnabled():
            return
        self.do_not_rename_checkbox.toggle()

    def _toggle_cover_image(self) -> None:
        if not self.set_as_cover_image_checkbox.isEnabled():
            return
        self.set_as_cover_image_checkbox.toggle()

    def _update_navigation_buttons(self) -> None:
        visible_row = self._visible_row_for_current_selection()
        has_files = bool(self._visible_rows)
        self.previous_button.setEnabled(has_files and visible_row > 0)
        self.next_button.setEnabled(has_files and 0 <= visible_row < len(self._visible_rows) - 1)

    def _review_note_text(self, file_item: FileItem) -> str:
        if file_item.status is FileStatus.UNMATCHED:
            return "No rule matched this filename stem. Add or adjust a rule in Settings -> Rules if this file should be classified automatically."
        if file_item.status is FileStatus.CONFLICT:
            return "This file cannot be applied yet because its target name collides with another file or an existing filename."
        if file_item.status is FileStatus.PROTECTED:
            return "This file is protected from automatic rename, usually because of its extension. Enable the protected-file override to allow renaming for this one file."
        if file_item.is_protected and file_item.allow_protected_rename:
            return "This protected file is in manual rename mode. Edit the Final Name field and press Enter to apply the filename for this file."
        if file_item.status is FileStatus.DONE:
            return "This file already matches its normalized output name."
        if file_item.status is FileStatus.READY:
            return "This file has a valid proposed rename and will be processed during the next apply step."
        return ""
