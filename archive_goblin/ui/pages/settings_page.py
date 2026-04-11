from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
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
    def __init__(self, parent: QWidget | None = None, rule: Rule | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rule")

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.pattern_edit = QLineEdit()
        self.type_combo = QComboBox()
        for file_type in FILE_TYPE_VALUES:
            self.type_combo.addItem(file_type_label(file_type), file_type)
        self.index_spin = QSpinBox()
        self.index_spin.setMinimum(1)
        self.index_spin.setMaximum(999)
        self.output_name_edit = QLineEdit()

        form_layout.addRow("Pattern", self.pattern_edit)
        form_layout.addRow("Type", self.type_combo)
        form_layout.addRow("Index", self.index_spin)
        form_layout.addRow("Output Name", self.output_name_edit)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.type_combo.currentIndexChanged.connect(self._sync_output_name_state)

        if rule is not None:
            self.pattern_edit.setText(rule.pattern)
            self.index_spin.setValue(rule.index)
            self.output_name_edit.setText(rule.output_name or "")
            for index in range(self.type_combo.count()):
                if self.type_combo.itemData(index) == rule.type:
                    self.type_combo.setCurrentIndex(index)
                    break

        self._sync_output_name_state()

    def _sync_output_name_state(self) -> None:
        is_custom = coerce_file_type(self.type_combo.currentData()) == FileType.CUSTOM
        self.output_name_edit.setEnabled(is_custom)
        if not is_custom:
            self.output_name_edit.clear()

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

        return Rule(
            pattern=pattern,
            type=file_type,
            index=self.index_spin.value(),
            output_name=output_name,
        )


class SettingsPage(QWidget):
    rules_changed = Signal(list)

    def __init__(self, rules: list[Rule]) -> None:
        super().__init__()
        self._rules = list(rules)
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

        self.set_rules(self._rules)

    def set_rules(self, rules: list[Rule]) -> None:
        self._rules = list(rules)
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
        dialog = RuleDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        rule = dialog.build_rule()
        if rule is None:
            return

        self._rules.append(rule)
        self._emit_rules_changed()

    def _edit_rule(self) -> None:
        row = self._current_row()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a rule to edit.")
            return

        dialog = RuleDialog(self, self._rules[row])
        if dialog.exec() != QDialog.Accepted:
            return

        rule = dialog.build_rule()
        if rule is None:
            return

        self._rules[row] = rule
        self._emit_rules_changed()

    def _delete_rule(self) -> None:
        row = self._current_row()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a rule to delete.")
            return

        del self._rules[row]
        self._emit_rules_changed()

    def _move_rule(self, offset: int) -> None:
        row = self._current_row()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Select a rule to reorder.")
            return

        target = row + offset
        if target < 0 or target >= len(self._rules):
            return

        self._rules[row], self._rules[target] = self._rules[target], self._rules[row]
        self._emit_rules_changed()
        self.rule_table.selectRow(target)

    def _emit_rules_changed(self) -> None:
        self._refresh_table()
        self.rules_changed.emit(list(self._rules))


class SettingsDialog(QDialog):
    rules_changed = Signal(list)

    def __init__(self, rules: list[Rule], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rules")
        self.resize(760, 480)

        layout = QVBoxLayout(self)
        self.settings_page = SettingsPage(rules)
        layout.addWidget(self.settings_page)

        close_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_buttons.rejected.connect(self.reject)
        close_buttons.accepted.connect(self.accept)
        close_buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(close_buttons)

        self.settings_page.rules_changed.connect(self.rules_changed.emit)

    def set_rules(self, rules: list[Rule]) -> None:
        self.settings_page.set_rules(rules)
