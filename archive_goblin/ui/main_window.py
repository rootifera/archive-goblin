from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QMessageBox

from archive_goblin.models.file_item import FileItem, FileStatus
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

        rules, protected_disk_image_extensions = self.settings_store.load_settings()
        self.session = Session(
            rules=rules,
            protected_disk_image_extensions=protected_disk_image_extensions,
        )
        self.settings_store.save_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
        )

        self.files_page = FilesPage()
        self.settings_dialog = SettingsDialog(
            self.session.rules,
            self.session.protected_disk_image_extensions,
            self,
        )
        self.setCentralWidget(self.files_page)
        self._build_menu()

        self.files_page.folder_chosen.connect(self.open_folder)
        self.files_page.item_edited.connect(self.on_file_edited)
        self.files_page.apply_requested.connect(self.apply_renames)
        self.files_page.rescan_requested.connect(self.rescan_folder)
        self.settings_dialog.settings_changed.connect(self.on_settings_changed)

        self.files_page.set_files(self.session.folder, self.session.files)

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("Settings")

        edit_rules_action = QAction("Rules...", self)
        edit_rules_action.triggered.connect(self.open_rules_dialog)
        settings_menu.addAction(edit_rules_action)

    def open_rules_dialog(self) -> None:
        self.settings_dialog.set_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
        )
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def open_folder(self, folder: Path) -> None:
        self.session.folder = folder
        self._reload_files()

    def rescan_folder(self) -> None:
        if self.session.folder is not None:
            self._reload_files()

    def on_settings_changed(self, rules: list[Rule], protected_disk_image_extensions: list[str]) -> None:
        self.session.rules = list(rules)
        self.session.protected_disk_image_extensions = list(protected_disk_image_extensions)
        self.settings_store.save_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
        )
        self.settings_dialog.set_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
        )
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

        ready_files = [file_item for file_item in self.session.files if file_item.status is FileStatus.READY]
        if not ready_files:
            QMessageBox.information(self, "Nothing To Rename", "There are no ready renames to apply.")
            return

        if self._confirm_apply(ready_files) != QMessageBox.Yes:
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

        QMessageBox.information(self, "Renames Applied", self._build_apply_result_text(ready_files, renamed_count))
        self._reload_files()

    def _reload_files(self) -> None:
        folder = self.session.folder
        if folder is None:
            self.session.files = []
            self.files_page.set_files(folder, self.session.files)
            return

        scanned_paths = self.scanner.scan(folder)
        self.session.files = [
            self.matcher.classify(
                path,
                self.session.rules,
                self.session.protected_disk_image_extensions,
            )
            for path in scanned_paths
        ]
        self._recalculate_files()

    def _recalculate_files(self) -> None:
        for file_item in self.session.files:
            self.naming_service.update_file_name(file_item)

        self.validator.validate(self.session.folder, self.session.files)
        self.files_page.set_files(self.session.folder, self.session.files)

    def _confirm_apply(self, ready_files: list[FileItem]) -> QMessageBox.StandardButton:
        rename_count = sum(1 for file_item in ready_files if file_item.has_pending_rename)
        cover_copy_count = sum(1 for file_item in ready_files if file_item.has_pending_cover_copy)
        details = []
        if rename_count:
            details.append(f"{rename_count} rename(s)")
        if cover_copy_count:
            details.append(f"{cover_copy_count} cover copy/copies")

        file_preview_lines = []
        for file_item in ready_files[:8]:
            operations: list[str] = []
            if file_item.has_pending_rename and file_item.proposed_name is not None:
                operations.append(f"{file_item.original_name} -> {file_item.proposed_name}")
            if file_item.has_pending_cover_copy and file_item.cover_image_name is not None:
                operations.append(f"{file_item.original_name} => {file_item.cover_image_name}")
            file_preview_lines.extend(operations)

        if len(ready_files) > 8:
            file_preview_lines.append(f"...and {len(ready_files) - 8} more file(s)")

        summary = ", ".join(details) if details else "no file operations"
        text = f"Apply {summary}?\n\n" + "\n".join(file_preview_lines)
        return QMessageBox.question(
            self,
            "Confirm Apply",
            text,
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Yes,
        )

    def _build_apply_result_text(self, ready_files: list[FileItem], renamed_count: int) -> str:
        rename_count = sum(1 for file_item in ready_files if file_item.has_pending_rename)
        cover_copy_count = sum(1 for file_item in ready_files if file_item.has_pending_cover_copy)
        return (
            f"Processed {renamed_count} file(s).\n\n"
            f"Renames: {rename_count}\n"
            f"Cover copies: {cover_copy_count}"
        )
