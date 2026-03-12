from __future__ import annotations

import copy
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ea_node_editor.settings import DEFAULT_WORKFLOW_SETTINGS
from ea_node_editor.ui.dialogs.sectioned_settings_dialog import SectionedSettingsDialog


class WorkflowSettingsDialog(SectionedSettingsDialog):
    _SECTIONS = [
        ("general", "General"),
        ("solver_config", "Solver Config"),
        ("environment", "Environment"),
        ("plugins", "Plugins"),
        ("logging", "Logging"),
    ]

    def __init__(self, initial_settings: dict[str, Any] | None = None, parent=None) -> None:
        super().__init__(
            window_title="Workflow Settings",
            header_text="Configure workflow defaults and runtime behavior.",
            sections=self._SECTIONS,
            section_list_object_name="workflowSettingsSectionList",
            header_object_name="workflowSettingsHeader",
            parent=parent,
        )
        self.set_values(initial_settings or {})

    def _build_pages(self) -> None:
        self.add_section_page(self._build_general_page())
        self.add_section_page(self._build_solver_page())
        self.add_section_page(self._build_environment_page())
        self.add_section_page(self._build_plugins_page())
        self.add_section_page(self._build_logging_page())

    def _build_general_page(self) -> QWidget:
        page = QWidget(self)
        form = QFormLayout(page)
        self.project_name_edit = QLineEdit(page)
        self.author_edit = QLineEdit(page)
        self.description_edit = QTextEdit(page)
        self.description_edit.setMinimumHeight(100)
        form.addRow("Project Name", self.project_name_edit)
        form.addRow("Author", self.author_edit)
        form.addRow("Description", self.description_edit)
        return page

    def _build_solver_page(self) -> QWidget:
        page = QWidget(self)
        form = QFormLayout(page)
        self.parallel_check = QCheckBox("Enable parallel processing", page)
        self.thread_count_spin = QSpinBox(page)
        self.thread_count_spin.setRange(1, 256)
        self.memory_limit_spin = QSpinBox(page)
        self.memory_limit_spin.setRange(1, 1024)
        self.memory_limit_spin.setSuffix(" GB")
        form.addRow(self.parallel_check)
        form.addRow("Thread Count", self.thread_count_spin)
        form.addRow("Memory Limit", self.memory_limit_spin)
        return page

    def _build_environment_page(self) -> QWidget:
        page = QWidget(self)
        form = QFormLayout(page)
        self.python_path_edit = QLineEdit(page)
        self.workdir_edit = QLineEdit(page)
        form.addRow("Python Path", self.python_path_edit)
        form.addRow("Working Directory", self.workdir_edit)
        return page

    def _build_plugins_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        info = QLabel("One plugin id per line.")
        info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.plugins_text = QTextEdit(page)
        self.plugins_text.setPlaceholderText("plugin.alpha\nplugin.beta")
        layout.addWidget(info)
        layout.addWidget(self.plugins_text, stretch=1)
        return page

    def _build_logging_page(self) -> QWidget:
        page = QWidget(self)
        form = QFormLayout(page)
        self.log_level_combo = QComboBox(page)
        for level in ("debug", "info", "warning", "error"):
            self.log_level_combo.addItem(level, level)
        self.capture_console_check = QCheckBox("Capture console output", page)
        form.addRow("Log Level", self.log_level_combo)
        form.addRow(self.capture_console_check)
        return page

    @staticmethod
    def _normalize(initial_settings: dict[str, Any]) -> dict[str, Any]:
        normalized = copy.deepcopy(DEFAULT_WORKFLOW_SETTINGS)
        for key, section in initial_settings.items():
            if key not in normalized or not isinstance(section, dict):
                continue
            for field, value in section.items():
                normalized[key][field] = value
        return normalized

    def set_values(self, initial_settings: dict[str, Any]) -> None:
        settings = self._normalize(initial_settings)
        self.project_name_edit.setText(str(settings["general"].get("project_name", "")))
        self.author_edit.setText(str(settings["general"].get("author", "")))
        self.description_edit.setPlainText(str(settings["general"].get("description", "")))
        self.parallel_check.setChecked(bool(settings["solver_config"].get("enable_parallel", True)))
        self.thread_count_spin.setValue(int(settings["solver_config"].get("thread_count", 8)))
        self.memory_limit_spin.setValue(int(settings["solver_config"].get("memory_limit_gb", 12)))
        self.python_path_edit.setText(str(settings["environment"].get("python_path", "")))
        self.workdir_edit.setText(str(settings["environment"].get("working_directory", "")))
        plugins = settings["plugins"].get("enabled", [])
        if isinstance(plugins, list):
            self.plugins_text.setPlainText("\n".join(str(item) for item in plugins))
        else:
            self.plugins_text.setPlainText("")
        level = str(settings["logging"].get("level", "info"))
        idx = self.log_level_combo.findData(level)
        self.log_level_combo.setCurrentIndex(idx if idx >= 0 else 1)
        self.capture_console_check.setChecked(bool(settings["logging"].get("capture_console", True)))

    def values(self) -> dict[str, Any]:
        plugins = [
            line.strip()
            for line in self.plugins_text.toPlainText().splitlines()
            if line.strip()
        ]
        return {
            "general": {
                "project_name": self.project_name_edit.text().strip(),
                "author": self.author_edit.text().strip(),
                "description": self.description_edit.toPlainText().strip(),
            },
            "solver_config": {
                "enable_parallel": self.parallel_check.isChecked(),
                "thread_count": int(self.thread_count_spin.value()),
                "memory_limit_gb": int(self.memory_limit_spin.value()),
            },
            "environment": {
                "python_path": self.python_path_edit.text().strip(),
                "working_directory": self.workdir_edit.text().strip(),
            },
            "plugins": {
                "enabled": plugins,
            },
            "logging": {
                "level": str(self.log_level_combo.currentData()),
                "capture_console": self.capture_console_check.isChecked(),
            },
        }
