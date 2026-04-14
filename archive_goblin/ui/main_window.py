from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QCheckBox, QMainWindow, QMessageBox

from archive_goblin.models.file_item import FileItem, FileStatus
from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.models.rule import Rule, coerce_file_type
from archive_goblin.models.session import Session
from archive_goblin.services.archive_metadata import ArchiveMetadataService
from archive_goblin.services.matcher import RuleMatcher
from archive_goblin.services.mount_detector import MountDetector
from archive_goblin.services.naming import NamingService
from archive_goblin.services.renamer import RenameService
from archive_goblin.services.scanner import FolderScanner
from archive_goblin.services.validator import RenameValidator
from archive_goblin.services.archive_upload import ArchiveUploadService
from archive_goblin.services.upload_preview import UploadPreviewService
from archive_goblin.storage.project_store import ProjectStore
from archive_goblin.storage.settings_store import SettingsStore
from archive_goblin.ui.pages.files_page import FilesPage
from archive_goblin.ui.pages.archive_settings_page import ArchiveSettingsDialog
from archive_goblin.ui.pages.metadata_page import MetadataDialog
from archive_goblin.ui.pages.metadata_settings_page import MetadataSettingsDialog
from archive_goblin.ui.pages.settings_page import SettingsDialog
from archive_goblin.ui.pages.upload_progress_page import UploadProgressDialog
from archive_goblin.ui.pages.upload_preview_page import UploadPreviewDialog
from archive_goblin.ui.workers.upload_worker import UploadWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Archive Goblin")
        self.resize(1480, 820)

        self.settings_store = SettingsStore()
        self.project_store = ProjectStore()
        self.scanner = FolderScanner()
        self.matcher = RuleMatcher()
        self.mount_detector = MountDetector()
        self.archive_metadata_service = ArchiveMetadataService()
        self.naming_service = NamingService()
        self.validator = RenameValidator()
        self.renamer = RenameService()
        self.archive_upload_service = ArchiveUploadService()
        self.upload_preview_service = UploadPreviewService()
        self._warned_mount_points: set[str] = set()
        self._upload_thread: QThread | None = None
        self._upload_worker: UploadWorker | None = None

        (
            rules,
            protected_disk_image_extensions,
            show_smb_warning,
            title_pattern,
            page_url_pattern,
            default_tags,
            archive_access_key,
            archive_secret_key,
        ) = self.settings_store.load_settings()
        self.session = Session(
            rules=rules,
            protected_disk_image_extensions=protected_disk_image_extensions,
            show_smb_warning=show_smb_warning,
            title_pattern=title_pattern,
            page_url_pattern=page_url_pattern,
            default_tags=default_tags,
            archive_access_key=archive_access_key,
            archive_secret_key=archive_secret_key,
        )
        self.settings_store.save_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
            self.session.show_smb_warning,
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.archive_access_key,
            self.session.archive_secret_key,
        )

        self.files_page = FilesPage()
        self.settings_dialog = SettingsDialog(
            self.session.rules,
            self.session.protected_disk_image_extensions,
            self,
        )
        self.metadata_settings_dialog = MetadataSettingsDialog(
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self,
        )
        self.archive_settings_dialog = ArchiveSettingsDialog(
            self.session.archive_access_key,
            self.session.archive_secret_key,
            self,
        )
        self.metadata_dialog = MetadataDialog(
            self.session.metadata,
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.files,
            self,
        )
        self.upload_preview_dialog = UploadPreviewDialog(self)
        self.upload_progress_dialog = UploadProgressDialog(self)
        self.setCentralWidget(self.files_page)
        self._build_menu()

        self.files_page.folder_chosen.connect(self.open_folder)
        self.files_page.item_edited.connect(self.on_file_edited)
        self.files_page.apply_requested.connect(self.apply_renames)
        self.files_page.rescan_requested.connect(self.rescan_folder)
        self.settings_dialog.settings_changed.connect(self.on_settings_changed)
        self.metadata_settings_dialog.settings_changed.connect(self.on_metadata_settings_changed)
        self.archive_settings_dialog.settings_changed.connect(self.on_archive_settings_changed)
        self.metadata_dialog.metadata_saved.connect(self.on_metadata_saved)
        self.metadata_dialog.preview_requested.connect(self.on_metadata_preview_requested)
        self.upload_preview_dialog.upload_requested.connect(self.start_upload)

        self.files_page.set_files(self.session.folder, self.session.files)
        self.statusBar().showMessage("Open a folder to begin reviewing files and metadata.")

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        project_menu = menu_bar.addMenu("Project")
        settings_menu = menu_bar.addMenu("Settings")

        open_folder_action = QAction("Open Folder...", self)
        open_folder_action.setShortcut(QKeySequence("Ctrl+O"))
        open_folder_action.setShortcutContext(Qt.ApplicationShortcut)
        open_folder_action.triggered.connect(self.files_page._choose_folder)
        self.addAction(open_folder_action)
        file_menu.addAction(open_folder_action)

        rescan_action = QAction("Rescan", self)
        rescan_action.setShortcut(QKeySequence("Ctrl+R"))
        rescan_action.setShortcutContext(Qt.ApplicationShortcut)
        rescan_action.triggered.connect(self.rescan_folder)
        self.addAction(rescan_action)
        file_menu.addAction(rescan_action)

        apply_renames_action = QAction("Apply Renames", self)
        apply_renames_action.setShortcut(QKeySequence("Ctrl+Return"))
        apply_renames_action.setShortcutContext(Qt.ApplicationShortcut)
        apply_renames_action.triggered.connect(self.apply_renames)
        self.addAction(apply_renames_action)
        file_menu.addAction(apply_renames_action)

        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Shift+Q"))
        quit_action.setShortcutContext(Qt.ApplicationShortcut)
        quit_action.triggered.connect(self.close)
        self.addAction(quit_action)
        file_menu.addAction(quit_action)

        edit_metadata_action = QAction("Metadata...", self)
        edit_metadata_action.setShortcut(QKeySequence("Ctrl+P"))
        edit_metadata_action.setShortcutContext(Qt.ApplicationShortcut)
        edit_metadata_action.triggered.connect(self.open_metadata_dialog)
        self.addAction(edit_metadata_action)
        project_menu.addAction(edit_metadata_action)

        upload_preview_action = QAction("Upload Preview...", self)
        upload_preview_action.triggered.connect(self.open_upload_preview_dialog)
        project_menu.addAction(upload_preview_action)

        edit_rules_action = QAction("Rules...", self)
        edit_rules_action.setShortcut(QKeySequence("Ctrl+Alt+R"))
        edit_rules_action.setShortcutContext(Qt.ApplicationShortcut)
        edit_rules_action.triggered.connect(self.open_rules_dialog)
        self.addAction(edit_rules_action)
        settings_menu.addAction(edit_rules_action)

        edit_metadata_settings_action = QAction("Metadata...", self)
        edit_metadata_settings_action.setShortcut(QKeySequence("Ctrl+Alt+M"))
        edit_metadata_settings_action.setShortcutContext(Qt.ApplicationShortcut)
        edit_metadata_settings_action.triggered.connect(self.open_metadata_settings_dialog)
        self.addAction(edit_metadata_settings_action)
        settings_menu.addAction(edit_metadata_settings_action)

        edit_archive_settings_action = QAction("Archive.org...", self)
        edit_archive_settings_action.setShortcut(QKeySequence("Ctrl+Alt+A"))
        edit_archive_settings_action.setShortcutContext(Qt.ApplicationShortcut)
        edit_archive_settings_action.triggered.connect(self.open_archive_settings_dialog)
        self.addAction(edit_archive_settings_action)
        settings_menu.addAction(edit_archive_settings_action)

    def open_rules_dialog(self) -> None:
        self.settings_dialog.set_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
        )
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def open_metadata_settings_dialog(self) -> None:
        self.metadata_settings_dialog.set_settings(
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
        )
        self.metadata_settings_dialog.show()
        self.metadata_settings_dialog.raise_()
        self.metadata_settings_dialog.activateWindow()

    def open_archive_settings_dialog(self) -> None:
        self.archive_settings_dialog.set_settings(
            self.session.archive_access_key,
            self.session.archive_secret_key,
        )
        self.archive_settings_dialog.show()
        self.archive_settings_dialog.raise_()
        self.archive_settings_dialog.activateWindow()

    def open_metadata_dialog(self) -> None:
        self.metadata_dialog.set_metadata(self.session.metadata)
        self.metadata_dialog.set_context(
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.files,
        )
        if self.session.folder is None:
            QMessageBox.information(
                self,
                "No Folder",
                "Open a folder before editing project metadata.",
            )
            return
        self.metadata_dialog.show()
        self.metadata_dialog.raise_()
        self.metadata_dialog.activateWindow()

    def open_folder(self, folder: Path) -> None:
        self.session.folder = folder
        self.session.metadata = self.project_store.load_metadata(folder)
        self.metadata_dialog.set_metadata(self.session.metadata)
        self._maybe_warn_about_network_share(folder)
        self._reload_files()
        self._refresh_status_bar()

    def rescan_folder(self) -> None:
        if self.session.folder is not None:
            self._reload_files()

    def on_settings_changed(self, rules: list[Rule], protected_disk_image_extensions: list[str]) -> None:
        self.session.rules = list(rules)
        self.session.protected_disk_image_extensions = list(protected_disk_image_extensions)
        self.settings_store.save_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
            self.session.show_smb_warning,
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.archive_access_key,
            self.session.archive_secret_key,
        )
        self.settings_dialog.set_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
        )
        if self.session.folder is not None:
            self._reload_files()

    def on_metadata_settings_changed(self, title_pattern: str, page_url_pattern: str, default_tags: list[str]) -> None:
        self.session.title_pattern = title_pattern
        self.session.page_url_pattern = page_url_pattern
        self.session.default_tags = list(default_tags)
        self.settings_store.save_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
            self.session.show_smb_warning,
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.archive_access_key,
            self.session.archive_secret_key,
        )
        self.metadata_settings_dialog.set_settings(
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
        )
        self.metadata_dialog.set_context(
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.files,
        )

    def on_archive_settings_changed(self, access_key: str, secret_key: str) -> None:
        self.session.archive_access_key = access_key
        self.session.archive_secret_key = secret_key
        self.settings_store.save_settings(
            self.session.rules,
            self.session.protected_disk_image_extensions,
            self.session.show_smb_warning,
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.archive_access_key,
            self.session.archive_secret_key,
        )
        self.archive_settings_dialog.set_settings(
            self.session.archive_access_key,
            self.session.archive_secret_key,
        )

    def on_metadata_saved(self, metadata: ProjectMetadata) -> None:
        self.session.metadata = metadata
        self.project_store.save_metadata(self.session.folder, self.session.metadata)
        self.metadata_dialog.set_metadata(self.session.metadata)
        self._refresh_status_bar("Project metadata saved.")

    def on_metadata_preview_requested(self, metadata: ProjectMetadata) -> None:
        self.session.metadata = metadata
        self.project_store.save_metadata(self.session.folder, self.session.metadata)
        self.metadata_dialog.set_metadata(self.session.metadata)
        self.open_upload_preview_dialog()

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
        self.metadata_dialog.set_context(
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.files,
        )
        self._refresh_status_bar()

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

    def _maybe_warn_about_network_share(self, folder: Path) -> None:
        mount_details = self.mount_detector.detect(folder)
        if mount_details is None or not mount_details.is_smb_share:
            return

        mount_key = f"{mount_details.mount_point}|{mount_details.filesystem_type}|{mount_details.source}"
        if mount_key in self._warned_mount_points:
            return

        self._warned_mount_points.add(mount_key)
        if not self.session.show_smb_warning:
            return

        message_box = QMessageBox(self)
        message_box.setWindowTitle("SMB Share Detected")
        message_box.setIcon(QMessageBox.Information)
        message_box.setText(
            "This folder appears to be on an SMB/CIFS share.\n\n"
            "Archive Goblin will still work, but file visibility and rename behavior can be flaky on network shares. "
            "For the most reliable results, prefer a local folder when possible."
        )
        dont_show_checkbox = QCheckBox("Acknowledge - don't show again")
        message_box.setCheckBox(dont_show_checkbox)
        message_box.exec()

        if dont_show_checkbox.isChecked():
            self.session.show_smb_warning = False
            self.settings_store.save_settings(
                self.session.rules,
                self.session.protected_disk_image_extensions,
                self.session.show_smb_warning,
                self.session.title_pattern,
                self.session.page_url_pattern,
                self.session.default_tags,
                self.session.archive_access_key,
                self.session.archive_secret_key,
            )

    def _refresh_status_bar(self, message: str | None = None) -> None:
        if message is not None:
            self.statusBar().showMessage(message, 3000)
            return

        metadata_summary = self.session.metadata.readiness_summary
        folder_summary = self.session.folder.name if self.session.folder is not None else "No folder"
        self.statusBar().showMessage(f"{folder_summary} | Metadata: {metadata_summary}")

    def open_upload_preview_dialog(self) -> None:
        summary = self.upload_preview_service.build_summary(
            self.session.folder,
            self.session.files,
            self.session.metadata,
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.archive_access_key,
            self.session.archive_secret_key,
        )
        self.upload_preview_dialog.set_summary(summary)
        self.upload_preview_dialog.show()
        self.upload_preview_dialog.raise_()
        self.upload_preview_dialog.activateWindow()

    def start_upload(self) -> None:
        summary = self.upload_preview_service.build_summary(
            self.session.folder,
            self.session.files,
            self.session.metadata,
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.archive_access_key,
            self.session.archive_secret_key,
        )
        if summary.blocked_issues:
            QMessageBox.warning(
                self,
                "Upload Blocked",
                "\n".join(summary.blocked_issues),
            )
            self.upload_preview_dialog.set_summary(summary)
            return

        if QMessageBox.question(
            self,
            "Confirm Upload",
            f"Upload {summary.file_count} file(s) to Archive.org as '{summary.identifier}'?",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Yes,
        ) != QMessageBox.Yes:
            return

        prepared = self.archive_upload_service.prepare_upload(
            self.session.folder,
            self.session.files,
            self.session.metadata,
            self.session.title_pattern,
            self.session.page_url_pattern,
            self.session.default_tags,
            self.session.archive_access_key,
            self.session.archive_secret_key,
        )
        if not hasattr(prepared, "identifier"):
            QMessageBox.critical(self, "Upload Failed", prepared.message)
            self.open_upload_preview_dialog()
            return

        self._upload_thread = QThread(self)
        self._upload_worker = UploadWorker(self.archive_upload_service, prepared)
        self._upload_worker.moveToThread(self._upload_thread)
        self._upload_thread.started.connect(self._upload_worker.run)
        self._upload_worker.started.connect(self.upload_progress_dialog.start)
        self._upload_worker.file_started.connect(self.upload_progress_dialog.mark_file_started)
        self._upload_worker.file_finished.connect(self.upload_progress_dialog.mark_file_finished)
        self._upload_worker.finished.connect(self._on_upload_finished)
        self._upload_worker.finished.connect(self._upload_thread.quit)
        self._upload_thread.finished.connect(self._cleanup_upload_thread)
        self._upload_thread.start()
        self.upload_progress_dialog.show()
        self.upload_progress_dialog.raise_()
        self.upload_progress_dialog.activateWindow()

    def _on_upload_finished(self, result: object, page_url: str) -> None:
        if not hasattr(result, "success"):
            return
        if result.success:
            self.upload_progress_dialog.finish_success(result.message)
            self._show_rich_message(
                "Upload Complete",
                f"{result.message}<br><br><a href=\"{page_url}\">{page_url}</a>" if page_url else result.message,
                QMessageBox.Information,
            )
            self.upload_progress_dialog.accept()
        else:
            self.upload_progress_dialog.finish_failure(result.message)
            self._show_rich_message(
                "Upload Failed",
                result.message.replace("\n", "<br>"),
                QMessageBox.Critical,
            )

    def _cleanup_upload_thread(self) -> None:
        if self._upload_worker is not None:
            self._upload_worker.deleteLater()
            self._upload_worker = None
        if self._upload_thread is not None:
            self._upload_thread.deleteLater()
            self._upload_thread = None

    def _show_rich_message(self, title: str, html_text: str, icon: QMessageBox.Icon) -> None:
        message_box = QMessageBox(self)
        message_box.setWindowTitle(title)
        message_box.setIcon(icon)
        message_box.setTextFormat(Qt.RichText)
        message_box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        message_box.setText(html_text)
        message_box.exec()
