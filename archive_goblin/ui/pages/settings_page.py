from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from archive_goblin.models.rule import (
    FILE_TYPE_VALUES,
    FileType,
    Rule,
    coerce_file_type,
    file_type_label,
)
from archive_goblin.services.naming import NamingService


class RuleDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        rule: Rule | None = None,
        existing_rules: list[Rule] | None = None,
        editing_row: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rule")
        self.naming_service = NamingService()
        self._existing_rules = list(existing_rules or [])
        self._editing_row = editing_row

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText("Example: A_FRONT")
        self.type_combo = QComboBox()
        for file_type in FILE_TYPE_VALUES:
            self.type_combo.addItem(file_type_label(file_type), file_type)
        self.index_spin = QSpinBox()
        self.index_spin.setMinimum(1)
        self.index_spin.setMaximum(999)
        self.output_name_edit = QLineEdit()
        self.output_name_edit.setPlaceholderText("Only used for Custom rules")
        self.matching_help_label = QLabel("Matches the filename stem exactly, case-insensitive.")
        self.matching_help_label.setStyleSheet("color:#7c8796;")
        self.preview_label = QLabel("Preview")
        self.preview_label.setStyleSheet("font-weight:600;")
        self.preview_value = QLineEdit()
        self.preview_value.setReadOnly(True)

        form_layout.addRow("Pattern", self.pattern_edit)
        form_layout.addRow("", self.matching_help_label)
        form_layout.addRow("Type", self.type_combo)
        form_layout.addRow("Index", self.index_spin)
        form_layout.addRow("Custom Output", self.output_name_edit)
        form_layout.addRow(self.preview_label, self.preview_value)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.type_combo.currentIndexChanged.connect(self._sync_output_name_state)
        self.type_combo.currentIndexChanged.connect(self._refresh_preview)
        self.index_spin.valueChanged.connect(self._refresh_preview)
        self.output_name_edit.textChanged.connect(self._refresh_preview)

        if rule is not None:
            self.pattern_edit.setText(rule.pattern)
            self.index_spin.setValue(rule.index)
            self.output_name_edit.setText(rule.output_name or "")
            for index in range(self.type_combo.count()):
                if self.type_combo.itemData(index) == rule.type:
                    self.type_combo.setCurrentIndex(index)
                    break

        self._sync_output_name_state()
        self._refresh_preview()

    def _sync_output_name_state(self) -> None:
        is_custom = coerce_file_type(self.type_combo.currentData()) == FileType.CUSTOM
        self.output_name_edit.setEnabled(is_custom)
        if not is_custom:
            self.output_name_edit.clear()

    def _refresh_preview(self) -> None:
        preview_rule = Rule(
            pattern=self.pattern_edit.text().strip() or "example",
            type=coerce_file_type(self.type_combo.currentData()),
            index=self.index_spin.value(),
            output_name=self.output_name_edit.text().strip() or None,
        )
        self.preview_value.setText(self.naming_service.build_preview_name(preview_rule))

    def build_rule(self) -> Rule | None:
        pattern = self.pattern_edit.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Invalid Rule", "Pattern is required.")
            return None

        file_type = coerce_file_type(self.type_combo.currentData())
        output_name = self.output_name_edit.text().strip() or None
        if file_type == FileType.CUSTOM and not output_name:
            QMessageBox.warning(self, "Invalid Rule", "Custom rules need an output name.")
            return None

        if self._has_duplicate_pattern(pattern):
            QMessageBox.warning(
                self,
                "Duplicate Pattern",
                "A rule with this pattern already exists. Patterns should stay unique for predictable matching.",
            )
            return None

        return Rule(
            pattern=pattern,
            type=file_type,
            index=self.index_spin.value(),
            output_name=output_name,
        )

    def _has_duplicate_pattern(self, pattern: str) -> bool:
        normalized = pattern.casefold()
        for row, existing_rule in enumerate(self._existing_rules):
            if self._editing_row is not None and row == self._editing_row:
                continue
            if existing_rule.normalized_pattern == normalized:
                return True
        return False


class SettingsPage(QWidget):
    settings_changed = Signal(list, list)

    def __init__(self, rules: list[Rule], protected_disk_image_extensions: list[str]) -> None:
        super().__init__()
        self._rules = list(rules)
        self._protected_disk_image_extensions = list(protected_disk_image_extensions)
        self.naming_service = NamingService()

        layout = QVBoxLayout(self)
        self.rule_table = QTableWidget(0, 4)
        self.rule_table.setHorizontalHeaderLabels(["Pattern", "Type", "Index", "Output Preview"])
        header = self.rule_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.rule_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.rule_table.setSelectionMode(QTableWidget.SingleSelection)
        self.rule_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rule_table.setColumnWidth(0, 180)
        self.rule_table.setColumnWidth(1, 170)
        self.rule_table.setColumnWidth(2, 90)
        layout.addWidget(self.rule_table, 1)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        self.move_up_button = QPushButton("Move Up")
        self.move_down_button = QPushButton("Move Down")
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.move_up_button)
        button_layout.addWidget(self.move_down_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        self.add_button.clicked.connect(self._add_rule)
        self.edit_button.clicked.connect(self._edit_rule)
        self.delete_button.clicked.connect(self._delete_rule)
        self.move_up_button.clicked.connect(lambda: self._move_rule(-1))
        self.move_down_button.clicked.connect(lambda: self._move_rule(1))

        extension_form = QFormLayout()
        self.protected_extensions_edit = QLineEdit()
        self.protected_extensions_edit.setPlaceholderText(".cue, .ccd, .img, .sub, .bin, .iso")
        self.protected_extensions_help = QLabel(
            "Comma-separated extensions treated as protected disk images."
        )
        self.protected_extensions_help.setStyleSheet("color:#7c8796;")
        extension_form.addRow("Protected Extensions", self.protected_extensions_edit)
        extension_form.addRow("", self.protected_extensions_help)
        layout.addLayout(extension_form)

        self.protected_extensions_edit.editingFinished.connect(self._save_protected_extensions)

        self.set_settings(self._rules, self._protected_disk_image_extensions)

    def set_settings(self, rules: list[Rule], protected_disk_image_extensions: list[str]) -> None:
        self._rules = list(rules)
        self._protected_disk_image_extensions = list(protected_disk_image_extensions)
        self.protected_extensions_edit.blockSignals(True)
        self.protected_extensions_edit.setText(", ".join(self._protected_disk_image_extensions))
        self.protected_extensions_edit.blockSignals(False)
        self._refresh_table()

    def _refresh_table(self) -> None:
        self.rule_table.setRowCount(len(self._rules))
        for row, rule in enumerate(self._rules):
            self.rule_table.setItem(row, 0, QTableWidgetItem(rule.pattern))
            self.rule_table.setItem(row, 1, QTableWidgetItem(file_type_label(rule.type)))
            index_item = QTableWidgetItem(str(rule.index))
            index_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.rule_table.setItem(row, 2, index_item)
            self.rule_table.setItem(
                row,
                3,
                QTableWidgetItem(self.naming_service.build_preview_name(rule)),
            )
        self.rule_table.setColumnWidth(0, 220)
        self.rule_table.setColumnWidth(1, 180)
        self.rule_table.setColumnWidth(2, 100)

    def _current_row(self) -> int:
        selected = self.rule_table.selectionModel().selectedRows()
        if not selected:
            return -1
        return selected[0].row()

    def _add_rule(self) -> None:
        dialog = RuleDialog(self, existing_rules=self._rules)
        if dialog.exec() != QDialog.Accepted:
            return

        rule = dialog.build_rule()
        if rule is None:
            return

        self._rules.append(rule)
        self._emit_settings_changed()

    def _edit_rule(self) -> None:
        row = self._current_row()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a rule to edit.")
            return

        dialog = RuleDialog(self, self._rules[row], existing_rules=self._rules, editing_row=row)
        if dialog.exec() != QDialog.Accepted:
            return

        rule = dialog.build_rule()
        if rule is None:
            return

        self._rules[row] = rule
        self._emit_settings_changed()

    def _delete_rule(self) -> None:
        row = self._current_row()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a rule to delete.")
            return

        del self._rules[row]
        self._emit_settings_changed()

    def _move_rule(self, offset: int) -> None:
        row = self._current_row()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a rule to reorder.")
            return

        target = row + offset
        if target < 0 or target >= len(self._rules):
            return

        self._rules[row], self._rules[target] = self._rules[target], self._rules[row]
        self._emit_settings_changed()
        self.rule_table.selectRow(target)

    def _emit_settings_changed(self) -> None:
        self._refresh_table()
        self.settings_changed.emit(list(self._rules), list(self._protected_disk_image_extensions))

    def _save_protected_extensions(self) -> None:
        raw_values = self.protected_extensions_edit.text().split(",")
        normalized = []
        seen: set[str] = set()
        for raw_value in raw_values:
            cleaned = raw_value.strip().casefold()
            if not cleaned:
                continue
            if not cleaned.startswith("."):
                cleaned = f".{cleaned}"
            if cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)

        if not normalized:
            QMessageBox.warning(
                self,
                "Invalid Extensions",
                "Enter at least one extension to keep disk image protection enabled.",
            )
            self.protected_extensions_edit.setText(", ".join(self._protected_disk_image_extensions))
            return

        self._protected_disk_image_extensions = normalized
        self.protected_extensions_edit.setText(", ".join(self._protected_disk_image_extensions))
        self._emit_settings_changed()


class SettingsDialog(QDialog):
    settings_changed = Signal(list, list)

    def __init__(self, rules: list[Rule], protected_disk_image_extensions: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rules")
        self.resize(760, 480)

        layout = QVBoxLayout(self)
        self.settings_page = SettingsPage(rules, protected_disk_image_extensions)
        layout.addWidget(self.settings_page)

        close_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_buttons.rejected.connect(self.reject)
        close_buttons.accepted.connect(self.accept)
        close_buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(close_buttons)

        self.settings_page.settings_changed.connect(self.settings_changed.emit)

    def set_settings(self, rules: list[Rule], protected_disk_image_extensions: list[str]) -> None:
        self.settings_page.set_settings(rules, protected_disk_image_extensions)
