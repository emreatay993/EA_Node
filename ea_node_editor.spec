# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

import importlib.util
import os
from pathlib import Path, PurePosixPath

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


_SPEC_PATH = Path(globals().get("__file__", Path.cwd() / "ea_node_editor.spec")).resolve()
PROJECT_ROOT = _SPEC_PATH.parent
PACKAGE_PROFILE_ENV_VAR = "EA_NODE_EDITOR_PACKAGE_PROFILE"
BASE_PACKAGE_PROFILE = "base"
VIEWER_PACKAGE_PROFILE = "viewer"
VIEWER_RUNTIME_HIDDENIMPORT_PACKAGES = (
    "ansys.dpf.core",
    "ansys.dpf.post",
    "ansys.dpf.gate",
    "ansys.grpc.dpf",
    "pyvista",
    "pyvistaqt",
    "qtpy",
    "vtkmodules",
)
VIEWER_RUNTIME_METADATA_DISTRIBUTIONS = (
    "ansys-dpf-core",
    "ansys-dpf-post",
    "pyvista",
    "pyvistaqt",
    "vtk",
)
VIEWER_NAMESPACE_BINARY_PATTERNS = {
    "ansys.dpf.gatebin": ("*.dll",),
}
VIEWER_SIBLING_BINARY_PATTERNS = {
    "vtkmodules": {
        "vtk.libs": ("*.dll",),
    },
}
VIEWER_DATA_FILE_PATTERNS = {
    "pyvistaqt": ("data/*.png",),
}


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _module_roots(name: str) -> list[Path]:
    spec = importlib.util.find_spec(name)
    if spec is None:
        return []
    if spec.submodule_search_locations:
        return [Path(location).resolve() for location in spec.submodule_search_locations]
    if spec.origin:
        return [Path(spec.origin).resolve().parent]
    return []


def _package_profile() -> str:
    profile = os.environ.get(PACKAGE_PROFILE_ENV_VAR, BASE_PACKAGE_PROFILE).strip().lower()
    if profile not in {BASE_PACKAGE_PROFILE, VIEWER_PACKAGE_PROFILE}:
        raise RuntimeError(
            f"Unsupported {PACKAGE_PROFILE_ENV_VAR}={profile!r}. "
            f"Expected {BASE_PACKAGE_PROFILE!r} or {VIEWER_PACKAGE_PROFILE!r}."
        )
    return profile


def _target_dir(dest_root: str, source_root: Path, source_path: Path) -> str:
    relative_parent = source_path.parent.relative_to(source_root)
    target = PurePosixPath(dest_root)
    if str(relative_parent) not in {"", "."}:
        target /= PurePosixPath(relative_parent.as_posix())
    return target.as_posix()


def _collect_globbed_files(source_root: Path, dest_root: str, patterns: tuple[str, ...]) -> list[tuple[str, str]]:
    collected: list[tuple[str, str]] = []
    for pattern in patterns:
        for source_path in sorted(source_root.glob(pattern)):
            if not source_path.is_file():
                continue
            collected.append((str(source_path), _target_dir(dest_root, source_root, source_path)))
    return collected


def _collect_viewer_hiddenimports() -> list[str]:
    hidden_imports: list[str] = []
    for package_name in VIEWER_RUNTIME_HIDDENIMPORT_PACKAGES:
        if _module_available(package_name):
            hidden_imports += collect_submodules(package_name)
    return hidden_imports


def _collect_viewer_datas() -> list[tuple[str, str]]:
    data_files: list[tuple[str, str]] = []
    for package_name, patterns in VIEWER_DATA_FILE_PATTERNS.items():
        if _module_available(package_name):
            data_files += collect_data_files(package_name, includes=list(patterns))
    for distribution_name in VIEWER_RUNTIME_METADATA_DISTRIBUTIONS:
        data_files += copy_metadata(distribution_name)
    return data_files


def _collect_viewer_namespace_binaries() -> list[tuple[str, str]]:
    binaries: list[tuple[str, str]] = []
    for package_name, patterns in VIEWER_NAMESPACE_BINARY_PATTERNS.items():
        for source_root in _module_roots(package_name):
            binaries += _collect_globbed_files(source_root, package_name.replace(".", "/"), patterns)
    return binaries


def _collect_viewer_sibling_binaries() -> list[tuple[str, str]]:
    binaries: list[tuple[str, str]] = []
    for anchor_module, sibling_patterns in VIEWER_SIBLING_BINARY_PATTERNS.items():
        for anchor_root in _module_roots(anchor_module):
            site_packages_root = anchor_root.parent
            for sibling_dir, patterns in sibling_patterns.items():
                source_root = site_packages_root / sibling_dir
                if source_root.is_dir():
                    binaries += _collect_globbed_files(source_root, sibling_dir, patterns)
    return binaries


def _require_viewer_stack() -> None:
    missing = [
        package_name
        for package_name in ("ansys.dpf.core", "pyvista", "pyvistaqt", "vtkmodules")
        if not _module_available(package_name)
    ]
    if missing:
        raise RuntimeError(
            "Viewer packaging profile requires the optional viewer stack in the build environment. "
            f"Missing modules: {', '.join(missing)}."
        )


package_profile = _package_profile()
viewer_profile_enabled = package_profile == VIEWER_PACKAGE_PROFILE

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
    includes=[
        "assets/app_icon/*.svg",
        "assets/app_icon/*.png",
        "assets/app_icon/*.ico",
        "assets/node_title_icons/**/*.svg",
        "assets/node_title_icons/**/*.png",
        "assets/node_title_icons/**/*.jpg",
        "assets/node_title_icons/**/*.jpeg",
    ],
)
binaries = []

# The viewer payload is opt-in so base Windows packages stay lean.
if viewer_profile_enabled:
    _require_viewer_stack()
    hiddenimports += _collect_viewer_hiddenimports()
    datas += _collect_viewer_datas()
    binaries += _collect_viewer_namespace_binaries()
    binaries += _collect_viewer_sibling_binaries()

hiddenimports = sorted(set(hiddenimports))
datas = list(dict.fromkeys(datas))
binaries = list(dict.fromkeys(binaries))

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
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
