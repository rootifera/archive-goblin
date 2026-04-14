from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from archive_goblin.services.archive_connection import ArchiveConnectionService


class ArchiveSettingsPage(QWidget):
    settings_changed = Signal(str, str)

    def __init__(self, access_key: str, secret_key: str) -> None:
        super().__init__()
        self.archive_connection_service = ArchiveConnectionService()
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.access_key_edit = QLineEdit()
        self.access_key_edit.setPlaceholderText("Archive.org S3 API access key")
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setPlaceholderText("Archive.org S3 secret key")
        self.secret_key_edit.setEchoMode(QLineEdit.Password)
        self.secret_key_edit.setClearButtonEnabled(True)
        self.test_connection_button = QPushButton("Test Connection")
        self.connection_status_label = QLabel("")
        self.connection_status_label.setWordWrap(True)
        self.connection_status_label.setStyleSheet("color:#7c8796;")
        self.help_label = QLabel(
            "These credentials stay local and will be used later for Archive.org upload integration."
        )
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color:#7c8796;")
        button_row = QHBoxLayout()
        button_row.addWidget(self.test_connection_button)
        button_row.addStretch(1)

        form_layout.addRow("S3 API Access Key", self.access_key_edit)
        form_layout.addRow("S3 Secret Key", self.secret_key_edit)
        form_layout.addRow("", button_row)
        form_layout.addRow("", self.connection_status_label)
        form_layout.addRow("", self.help_label)
        layout.addLayout(form_layout)

        self.access_key_edit.editingFinished.connect(self._emit_settings_changed)
        self.secret_key_edit.editingFinished.connect(self._emit_settings_changed)
        self.access_key_edit.textEdited.connect(self._clear_connection_status)
        self.secret_key_edit.textEdited.connect(self._clear_connection_status)
        self.test_connection_button.clicked.connect(self._test_connection)

        self.set_settings(access_key, secret_key)

    def set_settings(self, access_key: str, secret_key: str) -> None:
        self.access_key_edit.blockSignals(True)
        self.secret_key_edit.blockSignals(True)
        self.access_key_edit.setText(access_key)
        self.secret_key_edit.setText(secret_key)
        self.access_key_edit.blockSignals(False)
        self.secret_key_edit.blockSignals(False)
        self._clear_connection_status()

    def _emit_settings_changed(self) -> None:
        access_key = self.access_key_edit.text().strip()
        secret_key = self.secret_key_edit.text().strip()
        self.access_key_edit.setText(access_key)
        self.secret_key_edit.setText(secret_key)
        self.settings_changed.emit(access_key, secret_key)

    def _test_connection(self) -> None:
        self._emit_settings_changed()
        result = self.archive_connection_service.test_credentials(
            self.access_key_edit.text(),
            self.secret_key_edit.text(),
        )
        if result.success:
            self.connection_status_label.setText(f"✓ {result.message}")
            self.connection_status_label.setStyleSheet("color:#5ba66f;")
        else:
            self.connection_status_label.setText(f"✕ {result.message}")
            self.connection_status_label.setStyleSheet("color:#d66b6b;")

    def _clear_connection_status(self, *_args: object) -> None:
        self.connection_status_label.setText("")
        self.connection_status_label.setStyleSheet("color:#7c8796;")


class ArchiveSettingsDialog(QDialog):
    settings_changed = Signal(str, str)

    def __init__(self, access_key: str, secret_key: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Archive.org Settings")
        self.resize(620, 260)

        layout = QVBoxLayout(self)
        self.settings_page = ArchiveSettingsPage(access_key, secret_key)
        layout.addWidget(self.settings_page)

        close_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_buttons.rejected.connect(self.reject)
        close_buttons.accepted.connect(self.accept)
        close_buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(close_buttons)

        self.settings_page.settings_changed.connect(self.settings_changed.emit)

    def set_settings(self, access_key: str, secret_key: str) -> None:
        self.settings_page.set_settings(access_key, secret_key)
