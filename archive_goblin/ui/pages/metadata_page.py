from __future__ import annotations

import html

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from archive_goblin.models.project_metadata import ProjectMetadata
from archive_goblin.models.file_item import FileItem
from archive_goblin.services.archive_metadata import (
    ARCHIVE_COLLECTION_OPTIONS,
    ARCHIVE_LANGUAGE_OPTIONS,
    ARCHIVE_LICENSE_OPTIONS,
    ArchiveMetadataService,
)


class MetadataPage(QWidget):
    metadata_changed = Signal(object)

    def __init__(
        self,
        metadata: ProjectMetadata | None = None,
        title_pattern: str = ArchiveMetadataService.default_title_pattern,
        page_url_pattern: str = ArchiveMetadataService.default_page_url_pattern,
        default_tags: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._metadata = metadata or ProjectMetadata()
        self._title_pattern = title_pattern
        self._page_url_pattern = page_url_pattern
        self._default_tags = list(default_tags or [])
        self._files: list[FileItem] = []
        self._setting_page_url_programmatically = False
        self.archive_metadata_service = ArchiveMetadataService()

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.title_edit = QLineEdit()
        self.title_error_label = self._build_error_label()
        self.date_edit = QLineEdit()
        self.date_edit.setPlaceholderText("YYYY or YYYY-MM-DD")
        self.date_edit.setToolTip("Use YYYY, YYYY-MM, or YYYY-MM-DD.")
        self.developer_edit = QLineEdit()
        self.publisher_edit = QLineEdit()
        self.platform_edit = QLineEdit()
        self.language_combo = self._build_language_combo()
        self.license_combo = self._build_option_combo(ARCHIVE_LICENSE_OPTIONS)
        self.cc_allow_remixing_checkbox = QCheckBox("Allow Remixing")
        self.cc_require_share_alike_checkbox = QCheckBox("Require Share-Alike")
        self.cc_prohibit_commercial_use_checkbox = QCheckBox("Prohibit Commercial Use")
        self.collection_combo = self._build_option_combo(ARCHIVE_COLLECTION_OPTIONS)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("retro pc, dos, big box")
        self.use_default_tags_checkbox = QCheckBox("Use default tags from settings")
        self.description_edit = QTextBrowser()
        self.description_edit.setMinimumHeight(120)
        self.description_edit.setOpenExternalLinks(True)
        self.description_container = QWidget()
        self.description_container_layout = QVBoxLayout(self.description_container)
        self.description_container_layout.setContentsMargins(0, 0, 0, 8)
        self.description_container_layout.addWidget(self.description_edit)
        self.description_error_label = self._build_error_label()
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(100)
        self.page_url_edit = QLineEdit()
        self.check_url_button = QPushButton("Check Availability")
        self.reset_page_url_button = QPushButton("↺")
        self.reset_page_url_button.setFixedWidth(32)
        self.reset_page_url_button.setToolTip("Reset page URL to the generated default")
        self.availability_label = QLabel("")
        self.availability_label.setStyleSheet("color:#7c8796;")
        page_url_layout = QHBoxLayout()
        page_url_layout.addWidget(self.page_url_edit, 1)
        page_url_layout.addWidget(self.check_url_button)
        page_url_layout.addWidget(self.reset_page_url_button)
        self.effective_tags_label = QLabel("")
        self.effective_tags_label.setWordWrap(True)
        self.effective_tags_label.setStyleSheet("color:#7c8796;")

        form_layout.addRow("Title", self.title_edit)
        form_layout.addRow("", self.title_error_label)
        form_layout.addRow("Date", self.date_edit)
        form_layout.addRow("Developer", self.developer_edit)
        form_layout.addRow("Publisher", self.publisher_edit)
        form_layout.addRow("Platform", self.platform_edit)
        form_layout.addRow("Language", self.language_combo)
        form_layout.addRow("License", self.license_combo)
        form_layout.addRow("", self.cc_allow_remixing_checkbox)
        form_layout.addRow("", self.cc_require_share_alike_checkbox)
        form_layout.addRow("", self.cc_prohibit_commercial_use_checkbox)
        form_layout.addRow("Collection", self.collection_combo)
        form_layout.addRow("Page URL", page_url_layout)
        form_layout.addRow("", self.availability_label)
        form_layout.addRow("Tags", self.tags_edit)
        form_layout.addRow("", self.use_default_tags_checkbox)
        form_layout.addRow("Effective Tags", self.effective_tags_label)
        form_layout.addRow("Description Preview", self.description_container)
        form_layout.addRow("Notes", self.notes_edit)
        layout.addLayout(form_layout)

        self.check_url_button.clicked.connect(self._check_page_url_availability)
        self.reset_page_url_button.clicked.connect(self._reset_page_url)
        self.use_default_tags_checkbox.toggled.connect(self._refresh_derived_fields)
        self.tags_edit.textChanged.connect(self._refresh_derived_fields)
        self.title_edit.textChanged.connect(self._refresh_derived_fields)
        self.date_edit.textChanged.connect(self._refresh_derived_fields)
        self.publisher_edit.textChanged.connect(self._refresh_derived_fields)
        self.developer_edit.textChanged.connect(self._refresh_derived_fields)
        self.platform_edit.textChanged.connect(self._refresh_derived_fields)
        self.language_combo.currentTextChanged.connect(self._refresh_derived_fields)
        self.license_combo.currentTextChanged.connect(self._refresh_license_controls)
        self.collection_combo.currentTextChanged.connect(self._refresh_derived_fields)
        self.cc_allow_remixing_checkbox.toggled.connect(self._refresh_license_controls)
        self.cc_prohibit_commercial_use_checkbox.toggled.connect(self._refresh_derived_fields)
        self.cc_require_share_alike_checkbox.toggled.connect(self._refresh_derived_fields)
        self.notes_edit.textChanged.connect(self._refresh_derived_fields)
        self.page_url_edit.textEdited.connect(self._clear_availability_status)

        for line_edit in (
            self.title_edit,
            self.date_edit,
            self.developer_edit,
            self.publisher_edit,
            self.platform_edit,
            self.tags_edit,
            self.page_url_edit,
        ):
            line_edit.editingFinished.connect(lambda edit=line_edit: self._trim_line_edit(edit))

        self.set_metadata(self._metadata)

    def set_metadata(self, metadata: ProjectMetadata) -> None:
        self._metadata = metadata
        self.title_edit.setText(metadata.title)
        self.date_edit.setText(metadata.date)
        self.publisher_edit.setText(metadata.publisher)
        self.developer_edit.setText(metadata.developer)
        self.platform_edit.setText(metadata.platform)
        self._set_language_value(metadata.language)
        self._set_option_value(self.license_combo, ARCHIVE_LICENSE_OPTIONS, metadata.license)
        self.cc_allow_remixing_checkbox.setChecked(metadata.cc_allow_remixing)
        self.cc_require_share_alike_checkbox.setChecked(metadata.cc_require_share_alike)
        self.cc_prohibit_commercial_use_checkbox.setChecked(metadata.cc_prohibit_commercial_use)
        self._set_option_value(self.collection_combo, ARCHIVE_COLLECTION_OPTIONS, metadata.collection)
        self.tags_edit.setText(metadata.tags_text)
        self.use_default_tags_checkbox.setChecked(metadata.use_default_tags)
        self._set_description_preview(metadata.description)
        self.notes_edit.setPlainText(metadata.notes)
        self._set_page_url_text(self.archive_metadata_service.build_page_url(self._page_url_pattern, metadata))
        self._clear_availability_status()
        self._refresh_license_controls()
        self._refresh_derived_fields()

    def set_context(
        self,
        title_pattern: str,
        page_url_pattern: str,
        default_tags: list[str],
        files: list[FileItem] | None = None,
    ) -> None:
        self._title_pattern = title_pattern
        self._page_url_pattern = page_url_pattern
        self._default_tags = list(default_tags)
        self._files = list(files or [])
        self._refresh_derived_fields()

    def build_metadata(self) -> ProjectMetadata | None:
        metadata = ProjectMetadata(
            title=self.title_edit.text().strip(),
            date=self.date_edit.text().strip(),
            publisher=self.publisher_edit.text().strip(),
            developer=self.developer_edit.text().strip(),
            platform=self.platform_edit.text().strip(),
            language=self.archive_metadata_service.language_code_for_value(
                self.language_combo.currentData() or self.language_combo.currentText()
            ),
            license=self.archive_metadata_service.option_value_for_input(
                ARCHIVE_LICENSE_OPTIONS,
                self.license_combo.currentData() or self.license_combo.currentText(),
            ),
            cc_allow_remixing=self.cc_allow_remixing_checkbox.isChecked(),
            cc_require_share_alike=self.cc_require_share_alike_checkbox.isChecked(),
            cc_prohibit_commercial_use=self.cc_prohibit_commercial_use_checkbox.isChecked(),
            collection=self.archive_metadata_service.option_value_for_input(
                ARCHIVE_COLLECTION_OPTIONS,
                self.collection_combo.currentData() or self.collection_combo.currentText(),
            ),
            page_url_override=self.page_url_edit.text().strip(),
            description="",
            notes=self.notes_edit.toPlainText().strip(),
            use_default_tags=self.use_default_tags_checkbox.isChecked(),
        )
        metadata.set_tags_from_text(self.tags_edit.text().strip())
        metadata.description = self.archive_metadata_service.generate_description(
            metadata,
            self._files,
            self._title_pattern,
        )
        return metadata

    def _refresh_derived_fields(self) -> None:
        metadata = self.build_metadata()
        if metadata is None:
            return
        self._refresh_required_field_feedback(metadata)
        metadata.page_url_override = ""
        self._set_page_url_text(self.archive_metadata_service.build_page_url(self._page_url_pattern, metadata))
        effective_tags = self.archive_metadata_service.effective_tags(metadata, self._default_tags)
        self.effective_tags_label.setText(", ".join(effective_tags) if effective_tags else "No tags")
        self._set_description_preview(metadata.description)

    def _check_page_url_availability(self) -> None:
        metadata = self.build_metadata()
        if metadata is None:
            return
        identifier = self.archive_metadata_service.build_identifier(self._page_url_pattern, metadata)
        result = self.archive_metadata_service.check_identifier_availability(identifier)
        self._set_availability_status(result.available, result.message)

    def _reset_page_url(self) -> None:
        metadata = self.build_metadata()
        if metadata is None:
            return
        metadata.page_url_override = ""
        self._set_page_url_text(self.archive_metadata_service.build_page_url(self._page_url_pattern, metadata))
        self._clear_availability_status()

    def validate_page_url(self) -> bool:
        metadata = self.build_metadata()
        if metadata is None:
            return False
        identifier = self.archive_metadata_service.build_identifier(self._page_url_pattern, metadata)
        result = self.archive_metadata_service.check_identifier_availability(identifier)
        self._set_availability_status(result.available, result.message)
        return result.available

    def _refresh_license_controls(self) -> None:
        current_license = self.archive_metadata_service.option_value_for_input(
            ARCHIVE_LICENSE_OPTIONS,
            self.license_combo.currentData() or self.license_combo.currentText(),
        )
        is_creative_commons = current_license == "CC"
        self.cc_allow_remixing_checkbox.setEnabled(is_creative_commons)
        self.cc_prohibit_commercial_use_checkbox.setEnabled(is_creative_commons)

        if not is_creative_commons:
            self.cc_allow_remixing_checkbox.setChecked(False)
            self.cc_require_share_alike_checkbox.setChecked(False)
            self.cc_prohibit_commercial_use_checkbox.setChecked(False)

        allow_share_alike = is_creative_commons and self.cc_allow_remixing_checkbox.isChecked()
        self.cc_require_share_alike_checkbox.setEnabled(allow_share_alike)
        if not allow_share_alike:
            self.cc_require_share_alike_checkbox.setChecked(False)

        self._refresh_derived_fields()

    def _build_option_combo(self, values: list[tuple[str, str]]) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        for option_value, label in values:
            combo.addItem(label, option_value)
        return combo

    def _build_error_label(self) -> QLabel:
        label = QLabel("")
        label.setStyleSheet("color:#d66b6b;")
        return label

    def _build_language_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItem("Choose one...", "")
        for code, label in ARCHIVE_LANGUAGE_OPTIONS:
            combo.addItem(label, code)
        return combo

    def _set_language_value(self, value: str) -> None:
        normalized_code = self.archive_metadata_service.language_code_for_value(value)
        for index in range(self.language_combo.count()):
            if (self.language_combo.itemData(index) or "") == normalized_code:
                self.language_combo.setCurrentIndex(index)
                return

        language_label = self.archive_metadata_service.language_name_for_code(normalized_code)
        self.language_combo.setEditText(language_label)

    def _set_option_value(
        self,
        combo: QComboBox,
        options: list[tuple[str, str]],
        value: str,
    ) -> None:
        normalized_value = self.archive_metadata_service.option_value_for_input(options, value)
        for index in range(combo.count()):
            if (combo.itemData(index) or "") == normalized_value:
                combo.setCurrentIndex(index)
                return

        combo.setEditText(self.archive_metadata_service.option_label_for_value(options, normalized_value))

    def _refresh_required_field_feedback(self, metadata: ProjectMetadata) -> None:
        self._set_required_field_state(
            self.title_edit,
            self.title_error_label,
            bool(metadata.title.strip()),
            "Title cannot be blank.",
        )

    def _set_required_field_state(
        self,
        widget: QWidget,
        error_label: QLabel,
        is_valid: bool,
        error_text: str,
    ) -> None:
        widget.setStyleSheet("" if is_valid else "border:1px solid #d66b6b;")
        error_label.setText("" if is_valid else error_text)

    def _clear_availability_status(self, *_args: object) -> None:
        self.availability_label.setText("")
        self.availability_label.setStyleSheet("color:#7c8796;")

    def _set_availability_status(self, available: bool, message: str) -> None:
        if available:
            self.availability_label.setText(f"✓ {message}")
            self.availability_label.setStyleSheet("color:#5ba66f;")
        else:
            self.availability_label.setText(f"✕ {message}")
            self.availability_label.setStyleSheet("color:#d66b6b;")

    def _set_description_preview(self, description: str) -> None:
        escaped = html.escape(description)
        escaped = escaped.replace(
            "https://github.com/rootifera/archive-goblin",
            '<a href="https://github.com/rootifera/archive-goblin">https://github.com/rootifera/archive-goblin</a>',
        )
        self.description_edit.setHtml(escaped.replace("\n", "<br>"))

    def _set_page_url_text(self, value: str) -> None:
        self._setting_page_url_programmatically = True
        try:
            self.page_url_edit.setText(value)
        finally:
            self._setting_page_url_programmatically = False

    def _trim_line_edit(self, line_edit: QLineEdit) -> None:
        trimmed = line_edit.text().strip()
        if trimmed == line_edit.text():
            return
        line_edit.setText(trimmed)


class MetadataDialog(QDialog):
    metadata_saved = Signal(object)
    preview_requested = Signal(object)

    def __init__(
        self,
        metadata: ProjectMetadata | None = None,
        title_pattern: str = ArchiveMetadataService.default_title_pattern,
        page_url_pattern: str = ArchiveMetadataService.default_page_url_pattern,
        default_tags: list[str] | None = None,
        files: list[FileItem] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Project Metadata")
        self.resize(860, 900)

        layout = QVBoxLayout(self)
        self.help_label = QLabel(
            "This metadata stays local for now and prepares the folder for a later Archive.org upload workflow."
        )
        self.help_label.setWordWrap(True)
        self.help_label.setStyleSheet("color:#7c8796;")
        layout.addWidget(self.help_label)

        self.page = MetadataPage(metadata, title_pattern, page_url_pattern, default_tags)
        self.page.set_context(title_pattern, page_url_pattern, default_tags or [], files)
        layout.addWidget(self.page, 1)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_and_preview_button = self.buttons.addButton("Save and Preview Upload", QDialogButtonBox.ActionRole)
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        self.save_and_preview_button.clicked.connect(self._save_and_preview)
        layout.addWidget(self.buttons)

    def set_metadata(self, metadata: ProjectMetadata) -> None:
        self.page.set_metadata(metadata)

    def set_context(
        self,
        title_pattern: str,
        page_url_pattern: str,
        default_tags: list[str],
        files: list[FileItem] | None = None,
    ) -> None:
        self.page.set_context(title_pattern, page_url_pattern, default_tags, files)

    def _save(self) -> None:
        metadata = self.page.build_metadata()
        if metadata is None:
            QMessageBox.warning(self, "Invalid Metadata", "Could not build project metadata.")
            return

        if not self.page.validate_page_url():
            return

        self.metadata_saved.emit(metadata)
        self.accept()

    def _save_and_preview(self) -> None:
        metadata = self.page.build_metadata()
        if metadata is None:
            QMessageBox.warning(self, "Invalid Metadata", "Could not build project metadata.")
            return

        if not self.page.validate_page_url():
            return

        self.metadata_saved.emit(metadata)
        self.preview_requested.emit(metadata)
        self.accept()
