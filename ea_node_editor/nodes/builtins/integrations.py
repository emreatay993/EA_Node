from __future__ import annotations

import smtplib
import sys

from ea_node_editor.nodes.builtins.integrations_email import EMAIL_NODE_DESCRIPTORS, EmailSendNodePlugin
from ea_node_editor.nodes.builtins.integrations_file_io import (
    FILE_IO_NODE_DESCRIPTORS,
    FileReadNodePlugin,
    FileWriteNodePlugin,
    PathPointerNodePlugin,
)
from ea_node_editor.nodes.builtins.integrations_process import PROCESS_NODE_DESCRIPTORS, ProcessRunNodePlugin
from ea_node_editor.nodes.builtins.integrations_spreadsheet import (
    SPREADSHEET_NODE_DESCRIPTORS,
    ExcelReadNodePlugin,
    ExcelWriteNodePlugin,
    openpyxl,
)

INTEGRATION_NODE_DESCRIPTORS = (
    *SPREADSHEET_NODE_DESCRIPTORS,
    *FILE_IO_NODE_DESCRIPTORS,
    *EMAIL_NODE_DESCRIPTORS,
    *PROCESS_NODE_DESCRIPTORS,
)

__all__ = [
    "ExcelReadNodePlugin",
    "ExcelWriteNodePlugin",
    "FileReadNodePlugin",
    "FileWriteNodePlugin",
    "PathPointerNodePlugin",
    "EmailSendNodePlugin",
    "ProcessRunNodePlugin",
    "INTEGRATION_NODE_DESCRIPTORS",
    "openpyxl",
    "smtplib",
    "sys",
]
