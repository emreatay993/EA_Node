from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class ProjectSaveAsDialog(QDialog):
    SELF_CONTAINED_COPY = "self_contained_copy"
    PROJECT_FILE_ONLY = "project_file_only"

    def __init__(
        self,
        *,
        referenced_managed_count: int = 0,
        referenced_staged_count: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save Project As")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("Choose how project-managed data should be handled for the new project path.", self)
        header.setWordWrap(True)
        layout.addWidget(header)

        managed_count = max(0, int(referenced_managed_count))
        staged_count = max(0, int(referenced_staged_count))

        self.self_contained_copy_radio = QRadioButton(self._copy_option_label(managed_count), self)
        self.self_contained_copy_radio.setObjectName("projectSaveAsSelfContainedCopyRadio")
        self.self_contained_copy_radio.setChecked(True)
        layout.addWidget(self.self_contained_copy_radio)

        copy_details = QLabel(
            self._copy_option_details(managed_count=managed_count, staged_count=staged_count),
            self,
        )
        copy_details.setWordWrap(True)
        copy_details.setContentsMargins(20, 0, 0, 0)
        layout.addWidget(copy_details)

        self.project_file_only_radio = QRadioButton("Save the project file only", self)
        self.project_file_only_radio.setObjectName("projectSaveAsProjectFileOnlyRadio")
        layout.addWidget(self.project_file_only_radio)

        project_only_details = QLabel(
            "Managed files are not copied. Existing managed references stay in the project and may be unresolved "
            "until their files are copied into the new sidecar later. External file links stay external.",
            self,
        )
        project_only_details.setWordWrap(True)
        project_only_details.setContentsMargins(20, 0, 0, 0)
        layout.addWidget(project_only_details)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @classmethod
    def _copy_option_label(cls, managed_count: int) -> str:
        if managed_count == 1:
            return "Create a self-contained copy and copy 1 referenced managed file"
        return f"Create a self-contained copy and copy {managed_count} referenced managed files"

    @classmethod
    def _copy_option_details(cls, *, managed_count: int, staged_count: int) -> str:
        if managed_count:
            managed_clause = "Referenced managed files are copied into the new sibling .data sidecar."
        else:
            managed_clause = "No referenced managed files are currently recorded, so only the new project file is written."
        if staged_count == 1:
            staging_clause = "1 staged scratch item is left behind and is not copied."
        elif staged_count > 1:
            staging_clause = f"{staged_count} staged scratch items are left behind and are not copied."
        else:
            staging_clause = "Staging scratch is not copied."
        return f"{managed_clause} {staging_clause} External file links stay external."

    def selected_mode(self) -> str:
        if self.project_file_only_radio.isChecked():
            return self.PROJECT_FILE_ONLY
        return self.SELF_CONTAINED_COPY
