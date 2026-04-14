from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from archive_goblin.services.upload_preview import UploadPreviewSummary


class UploadPreviewPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.identifier_label = QLabel("—")
        self.page_url_label = QLabel("—")
        self.page_url_label.setOpenExternalLinks(True)
        self.file_count_label = QLabel("0")
        self.total_size_label = QLabel("0 B")
        self.collection_label = QLabel("—")
        self.license_label = QLabel("—")
        self.language_label = QLabel("—")
        self.tags_label = QLabel("—")
        self.tags_label.setWordWrap(True)
        self.blocked_label = QLabel("No blocking issues.")
        self.blocked_label.setWordWrap(True)
        self.warning_label = QLabel("No warnings.")
        self.warning_label.setWordWrap(True)
        self.description_view = QTextBrowser()
        self.description_view.setMinimumHeight(220)

        form_layout.addRow("Identifier", self.identifier_label)
        form_layout.addRow("Page URL", self.page_url_label)
        form_layout.addRow("Files", self.file_count_label)
        form_layout.addRow("Total Size", self.total_size_label)
        form_layout.addRow("Collection", self.collection_label)
        form_layout.addRow("License", self.license_label)
        form_layout.addRow("Language", self.language_label)
        form_layout.addRow("Effective Tags", self.tags_label)
        form_layout.addRow("Blocking Issues", self.blocked_label)
        form_layout.addRow("Warnings", self.warning_label)
        form_layout.addRow("Description", self.description_view)
        layout.addLayout(form_layout)

    def set_summary(self, summary: UploadPreviewSummary) -> None:
        self.identifier_label.setText(summary.identifier or "—")
        if summary.page_url:
            self.page_url_label.setText(f'<a href="{summary.page_url}">{summary.page_url}</a>')
        else:
            self.page_url_label.setText("—")
        self.file_count_label.setText(str(summary.file_count))
        self.total_size_label.setText(self._format_bytes(summary.total_size_bytes))
        self.collection_label.setText(summary.collection_label or "—")
        self.license_label.setText(summary.license_label or "—")
        self.language_label.setText(summary.language_label or "—")
        self.tags_label.setText(", ".join(summary.effective_tags) if summary.effective_tags else "No tags")
        self.blocked_label.setText("\n".join(summary.blocked_issues) if summary.blocked_issues else "No blocking issues.")
        self.warning_label.setText("\n".join(summary.warnings) if summary.warnings else "No warnings.")
        self.blocked_label.setStyleSheet("color:#d66b6b;" if summary.blocked_issues else "color:#7c8796;")
        self.warning_label.setStyleSheet("color:#d6b26b;" if summary.warnings else "color:#7c8796;")
        self.description_view.setPlainText(summary.description)

    def _format_bytes(self, size: int) -> str:
        value = float(size)
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if value < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{int(size)} B"


class UploadPreviewDialog(QDialog):
    upload_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Upload Preview")
        self.resize(860, 760)

        layout = QVBoxLayout(self)
        self.help_label = QLabel(
            "This is a preflight summary only. No files or metadata are uploaded from this screen yet."
        )
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color:#7c8796;")
        layout.addWidget(self.help_label)

        self.page = UploadPreviewPage()
        layout.addWidget(self.page, 1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self.upload_button = self.buttons.addButton("Start Upload", QDialogButtonBox.AcceptRole)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)
        self.buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        self.upload_button.clicked.connect(self.upload_requested.emit)
        layout.addWidget(self.buttons)

    def set_summary(self, summary: UploadPreviewSummary) -> None:
        self.page.set_summary(summary)
        self.upload_button.setEnabled(not summary.blocked_issues)
