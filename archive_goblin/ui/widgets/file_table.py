from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from archive_goblin.models.file_item import FileItem
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
                self.setItem(row, 0, QTableWidgetItem(file_item.original_name))
                self.setItem(row, 1, QTableWidgetItem(file_type_label(file_item.type)))
                self.setItem(row, 2, QTableWidgetItem(file_item.proposed_name or ""))
                status_text = file_item.status.replace("_", " ").title()
                if file_item.conflict_message:
                    status_text = f"{status_text}: {file_item.conflict_message}"
                self.setItem(row, 3, QTableWidgetItem(status_text))
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
