from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from archive_goblin.services.archive_metadata import ArchiveMetadataService


class MetadataSettingsPage(QWidget):
    settings_changed = Signal(str, list)

    def __init__(self, page_url_pattern: str, default_tags: list[str]) -> None:
        super().__init__()
        self._page_url_pattern = page_url_pattern
        self._default_tags = list(default_tags)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.page_url_pattern_edit = QLineEdit()
        self.page_url_pattern_edit.setPlaceholderText("{title}-{release_year}-{language}")
        self.page_url_pattern_help = QLabel(
            "Available placeholders: {title}, {date}, {release_year}, {language}, {publisher}, {developer}, {platform}, {collection}"
        )
        self.page_url_pattern_help.setWordWrap(True)
        self.page_url_pattern_help.setStyleSheet("color:#7c8796;")
        self.default_tags_edit = QLineEdit()
        self.default_tags_edit.setPlaceholderText("software, retro pc, big box")
        self.default_tags_help = QLabel(
            "Comma-separated tags added to each project by default unless disabled in the project metadata window."
        )
        self.default_tags_help.setWordWrap(True)
        self.default_tags_help.setStyleSheet("color:#7c8796;")
        form_layout.addRow("Page URL Pattern", self.page_url_pattern_edit)
        form_layout.addRow("", self.page_url_pattern_help)
        form_layout.addRow("Default Tags", self.default_tags_edit)
        form_layout.addRow("", self.default_tags_help)
        layout.addLayout(form_layout)

        self.page_url_pattern_edit.editingFinished.connect(self._emit_settings_changed)
        self.default_tags_edit.editingFinished.connect(self._emit_settings_changed)

        self.set_settings(self._page_url_pattern, self._default_tags)

    def set_settings(self, page_url_pattern: str, default_tags: list[str]) -> None:
        self._page_url_pattern = page_url_pattern
        self._default_tags = list(default_tags)
        self.page_url_pattern_edit.blockSignals(True)
        self.page_url_pattern_edit.setText(self._page_url_pattern)
        self.page_url_pattern_edit.blockSignals(False)
        self.default_tags_edit.blockSignals(True)
        self.default_tags_edit.setText(", ".join(self._default_tags))
        self.default_tags_edit.blockSignals(False)

    def _emit_settings_changed(self, *_args: object) -> None:
        pattern = self.page_url_pattern_edit.text().strip() or ArchiveMetadataService.default_page_url_pattern
        default_tags = self._normalize_tags(self.default_tags_edit.text())
        self._page_url_pattern = pattern
        self._default_tags = default_tags
        self.page_url_pattern_edit.setText(self._page_url_pattern)
        self.default_tags_edit.setText(", ".join(self._default_tags))
        self.settings_changed.emit(self._page_url_pattern, list(self._default_tags))

    def _normalize_tags(self, raw_text: str) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_value in raw_text.split(","):
            cleaned = raw_value.strip()
            if not cleaned:
                continue
            lowered = cleaned.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned)
        return normalized


class MetadataSettingsDialog(QDialog):
    settings_changed = Signal(str, list)

    def __init__(
        self,
        page_url_pattern: str,
        default_tags: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Metadata Settings")
        self.resize(760, 260)

        layout = QVBoxLayout(self)
        self.settings_page = MetadataSettingsPage(page_url_pattern, default_tags)
        layout.addWidget(self.settings_page)

        close_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_buttons.rejected.connect(self.reject)
        close_buttons.accepted.connect(self.accept)
        close_buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(close_buttons)

        self.settings_page.settings_changed.connect(self.settings_changed.emit)

    def set_settings(self, page_url_pattern: str, default_tags: list[str]) -> None:
        self.settings_page.set_settings(page_url_pattern, default_tags)
