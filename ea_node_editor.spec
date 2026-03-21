# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

import importlib.util
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


PROJECT_ROOT = Path(__file__).resolve().parent


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


hiddenimports = collect_submodules("ea_node_editor.nodes.builtins")
hiddenimports += [
    "PyQt6.QtPdf",
    "PyQt6.QtQml",
    "PyQt6.QtQuick",
    "PyQt6.QtQuickControls2",
    "PyQt6.QtQuickWidgets",
    "PyQt6.QtSvg",
]

if _module_available("openpyxl"):
    hiddenimports += collect_submodules("openpyxl")

if _module_available("paramiko"):
    hiddenimports += collect_submodules("paramiko")

datas = []
datas += collect_data_files(
    "ea_node_editor.ui_qml",
    includes=["*.qml", "**/*.qml", "*.js", "**/*.js", "*.svg", "**/*.svg"],
)
datas += collect_data_files(
    "ea_node_editor.ui.theme",
    includes=["icons/*.svg"],
)
datas += collect_data_files(
    "ea_node_editor",
    includes=["assets/app_icon/*.svg", "assets/app_icon/*.png", "assets/app_icon/*.ico"],
)

hiddenimports = sorted(set(hiddenimports))
datas = list(dict.fromkeys(datas))

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="COREX_Node_Editor",
    icon=str(PROJECT_ROOT / "ea_node_editor" / "assets" / "app_icon" / "corex_app.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="COREX_Node_Editor",
)
