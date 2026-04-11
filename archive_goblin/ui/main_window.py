from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QMessageBox

from archive_goblin.models.file_item import FileStatus
from archive_goblin.models.rule import Rule, coerce_file_type
from archive_goblin.models.session import Session
from archive_goblin.services.matcher import RuleMatcher
from archive_goblin.services.naming import NamingService
from archive_goblin.services.renamer import RenameService
from archive_goblin.services.scanner import FolderScanner
from archive_goblin.services.validator import RenameValidator
from archive_goblin.storage.settings_store import SettingsStore
from archive_goblin.ui.pages.files_page import FilesPage
from archive_goblin.ui.pages.settings_page import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Archive Goblin")
        self.resize(1280, 760)

        self.settings_store = SettingsStore()
        self.scanner = FolderScanner()
        self.matcher = RuleMatcher()
        self.naming_service = NamingService()
        self.validator = RenameValidator()
        self.renamer = RenameService()

        self.session = Session(rules=self.settings_store.load_rules())
        self.settings_store.save_rules(self.session.rules)

        self.files_page = FilesPage()
        self.settings_dialog = SettingsDialog(self.session.rules, self)
        self.setCentralWidget(self.files_page)
        self._build_menu()

        self.files_page.folder_chosen.connect(self.open_folder)
        self.files_page.item_edited.connect(self.on_file_edited)
        self.files_page.apply_requested.connect(self.apply_renames)
        self.files_page.rescan_requested.connect(self.rescan_folder)
        self.settings_dialog.rules_changed.connect(self.on_rules_changed)

        self.files_page.set_files(self.session.folder, self.session.files)

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("Settings")

        edit_rules_action = QAction("Rules...", self)
        edit_rules_action.triggered.connect(self.open_rules_dialog)
        settings_menu.addAction(edit_rules_action)

    def open_rules_dialog(self) -> None:
        self.settings_dialog.set_rules(self.session.rules)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def open_folder(self, folder: Path) -> None:
        self.session.folder = folder
        self._reload_files()

    def rescan_folder(self) -> None:
        if self.session.folder is not None:
            self._reload_files()

    def on_rules_changed(self, rules: list[Rule]) -> None:
        self.session.rules = list(rules)
        self.settings_store.save_rules(self.session.rules)
        self.settings_dialog.set_rules(self.session.rules)
        if self.session.folder is not None:
            self._reload_files()

    def on_file_edited(self, row: int, changes: dict[str, object]) -> None:
        if row < 0 or row >= len(self.session.files):
            return

        file_item = self.session.files[row]
        for key, value in changes.items():
            if key in {"type", "detected_type"} and value is not None:
                value = coerce_file_type(value)
            setattr(file_item, key, value)

        self._recalculate_files()

    def apply_renames(self) -> None:
        folder = self.session.folder
        if folder is None:
            QMessageBox.information(self, "No Folder", "Open a folder before applying renames.")
            return

        self.validator.validate(folder, self.session.files)
        conflicts = [file_item for file_item in self.session.files if file_item.status is FileStatus.CONFLICT]
        if conflicts:
            QMessageBox.warning(
                self,
                "Resolve Conflicts",
                "Some files still have naming conflicts. Fix them before applying renames.",
            )
            self.files_page.set_files(folder, self.session.files)
            return

        try:
            renamed_count = self.renamer.apply(folder, self.session.files)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Rename Failed",
                f"Could not apply file operations:\n{exc}",
            )
            self._reload_files()
            return

        if renamed_count == 0:
            QMessageBox.information(self, "Nothing To Rename", "There are no ready renames to apply.")
            return

        QMessageBox.information(self, "Renames Applied", f"Applied {renamed_count} rename(s).")
        self._reload_files()

    def _reload_files(self) -> None:
        folder = self.session.folder
        if folder is None:
            self.session.files = []
            self.files_page.set_files(folder, self.session.files)
            return

        scanned_paths = self.scanner.scan(folder)
        self.session.files = [self.matcher.classify(path, self.session.rules) for path in scanned_paths]
        self._recalculate_files()

    def _recalculate_files(self) -> None:
        for file_item in self.session.files:
            self.naming_service.update_file_name(file_item)

        self.validator.validate(self.session.folder, self.session.files)
        self.files_page.set_files(self.session.folder, self.session.files)
