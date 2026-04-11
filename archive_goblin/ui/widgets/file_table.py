from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from archive_goblin.models.file_item import FileItem, FileStatus
from archive_goblin.models.rule import file_type_label


class FileTable(QTableWidget):
    row_selected = Signal(int)

    def __init__(self) -> None:
        super().__init__(0, 4)
        self._files: list[FileItem] = []
        self._updating = False
        self.setHorizontalHeaderLabels(["Original Filename", "Type", "Proposed New Name", "Status"])
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.setColumnWidth(0, 280)
        self.setColumnWidth(1, 150)
        self.setColumnWidth(3, 140)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.itemSelectionChanged.connect(self._emit_row_selected)

    def set_files(self, files: list[FileItem]) -> None:
        self._files = list(files)
        self._updating = True
        try:
            self.setRowCount(len(files))
            for row, file_item in enumerate(files):
                original_item = QTableWidgetItem(file_item.original_name)
                type_item = QTableWidgetItem(file_type_label(file_item.type))
                proposed_item = QTableWidgetItem(file_item.proposed_name or "")
                status_text = self._display_status_text(file_item.status)
                if file_item.conflict_message:
                    status_text = f"{status_text}: {file_item.conflict_message}"
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignCenter)

                for item in (original_item, type_item, proposed_item, status_item):
                    self._style_item(item, file_item)

                self.setItem(row, 0, original_item)
                self.setItem(row, 1, type_item)
                self.setItem(row, 2, proposed_item)
                self.setItem(row, 3, status_item)
        finally:
            self._updating = False

    def select_row(self, row: int) -> None:
        if row < 0 or row >= self.rowCount():
            self.clearSelection()
            return
        self.selectRow(row)

    def _emit_row_selected(self) -> None:
        selected_rows = self.selectionModel().selectedRows()
        row = selected_rows[0].row() if selected_rows else -1
        self.row_selected.emit(row)

    def _style_item(self, item: QTableWidgetItem, file_item: FileItem) -> None:
        foreground = QColor("#1f2933")
        background = QColor("#151a21")
        font = QFont()

        if file_item.status is FileStatus.CONFLICT:
            foreground = QColor("#ffb4b4")
            background = QColor("#4c1d1d")
            font.setBold(True)
        elif file_item.status is FileStatus.READY:
            foreground = QColor("#b7f7c2")
            background = QColor("#173225")
        elif file_item.status is FileStatus.DONE:
            foreground = QColor("#c5ced8")
            background = QColor("#24303d")
        elif file_item.status is FileStatus.PROTECTED:
            foreground = QColor("#ffd79a")
            background = QColor("#45311a")
        elif file_item.status is FileStatus.UNMATCHED:
            foreground = QColor("#d5dbe3")
            background = QColor("#2a3441")
        elif file_item.status is FileStatus.IGNORED:
            foreground = QColor("#b0bac5")
            background = QColor("#2d3642")

        item.setForeground(QBrush(foreground))
        item.setBackground(QBrush(background))
        item.setFont(font)

    def _display_status_text(self, status: FileStatus) -> str:
        if status is FileStatus.READY:
            return "Ready for Rename"
        return status.value.replace("_", " ").title()
