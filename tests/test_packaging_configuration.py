from __future__ import annotations

import ast
import fnmatch
import json
import shutil
import subprocess
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 uses tomli in this repo venv.
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
GITIGNORE_PATH = REPO_ROOT / ".gitignore"
SPEC_PATH = REPO_ROOT / "ea_node_editor.spec"
BUILD_PACKAGE_PATH = REPO_ROOT / "scripts" / "build_windows_package.ps1"
BUILD_INSTALLER_PATH = REPO_ROOT / "scripts" / "build_windows_installer.ps1"
BUILD_MCF_DPF_GUI_PATH = REPO_ROOT / "scripts" / "build_mcf_dpf_section_resultants_gui.ps1"
RUNTIME_MANIFEST_PATH = REPO_ROOT / "runtime" / "runtime_manifest.json"
BUILD_EXCALIDRAW_HOST_PATH = REPO_ROOT / "scripts" / "build_excalidraw_host.ps1"
SIGN_RELEASE_PATH = REPO_ROOT / "scripts" / "sign_release_artifacts.ps1"
PYINSTALLER_PYARROW_HOOK_PATH = REPO_ROOT / "scripts" / "pyinstaller_hooks" / "hook-pyarrow.py"
WEB_ASSET_PACKAGE_DATA_GLOBS = {
    "web_assets/**/*.html",
    "web_assets/**/*.css",
    "web_assets/**/*.js",
    "web_assets/**/*.mjs",
    "web_assets/**/*.cjs",
    "web_assets/**/*.chunk.js",
    "web_assets/**/*.chunk.css",
    "web_assets/**/*.json",
    "web_assets/**/*.webmanifest",
    "web_assets/**/asset-manifest.*",
    "web_assets/**/*.wasm",
    "web_assets/**/*.svg",
    "web_assets/**/*.png",
    "web_assets/**/*.jpg",
    "web_assets/**/*.jpeg",
    "web_assets/**/*.gif",
    "web_assets/**/*.webp",
    "web_assets/**/*.ico",
    "web_assets/**/*.woff",
    "web_assets/**/*.woff2",
    "web_assets/**/*.ttf",
    "web_assets/**/*.otf",
    "web_assets/**/*.eot",
    "web_assets/excalidraw_host/*",
    "web_assets/excalidraw_host/**/*",
}
WEB_RUNTIME_HIDDENIMPORT_MODULES = {
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineQuick",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebChannel",
}
QT_MULTIMEDIA_RUNTIME_HIDDENIMPORT_MODULES = {"PyQt6.QtMultimedia"}
UI_QML_RUNTIME_ASSET_GLOBS = {
    "ui_qml/*.qml",
    "ui_qml/**/*.qml",
    "ui_qml/**/*.js",
    "ui_qml/**/*.svg",
    "ui_qml/**/*.json",
    "ui_qml/**/*.txt",
}
MOCKUP_RUNTIME_ASSET_GLOBS = {
    "mockups/**/*.qml",
    "mockups/**/*.js",
}
DPF_OPERATOR_CATALOG_PACKAGE_DATA_GLOB = "addons/ansys_dpf/operator_catalog.json"
DPF_WORKFLOW_HELP_ASSET_GLOB = "addons/ansys_dpf/workflow_docs/*.md"
MARS_ICON_PACKAGE_DATA_GLOB = "addons/mars/icons/mars_icon_64.png"
APPLICATION_FONT_PACKAGE_DATA_GLOBS = {"assets/fonts/*.ttf", "assets/fonts/*.txt"}
EXCALIDRAW_HOST_ASSET_ROOT = REPO_ROOT / "ea_node_editor" / "web_assets" / "excalidraw_host"


def _load_pyproject() -> dict:
    return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))


def _literal_assignments(path: Path) -> dict[str, object]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            values[target.id] = ast.literal_eval(node.value)
        except Exception:
            continue
    return values


def _excalidraw_host_asset_paths() -> list[str]:
    package_root = REPO_ROOT / "ea_node_editor"
    return sorted(
        path.relative_to(package_root).as_posix()
        for path in EXCALIDRAW_HOST_ASSET_ROOT.rglob("*")
        if path.is_file()
    )


def _uncovered_asset_paths(asset_paths: list[str], glob_patterns: set[str]) -> list[str]:
    return [
        asset_path
        for asset_path in asset_paths
        if not any(fnmatch.fnmatchcase(asset_path, pattern) for pattern in glob_patterns)
    ]


def test_optional_dependency_groups_wire_ansys_and_viewer_into_all_and_dev() -> None:
    pyproject = _load_pyproject()
    optional_dependencies = pyproject["project"]["optional-dependencies"]

    expected_ansys = {
        "ansys-dpf-core>=0.16,<0.17",
        "ansys-dpf-post>=0.11",
        "ansys-mechanical-core>=0.12.6",
    }
    expected_viewer = {
        "cadquery-ocp-novtk==7.9.3.1.1",
        "matplotlib>=3.8",
        "mplcursors>=0.7.1",
        "pyqtgraph>=0.13",
        "pyvista>=0.47",
        "pyvistaqt>=0.11",
        "vtk>=9.6",
    }
    expected_presentation = {
        "python-pptx>=1.0",
    }
    expected_acceleration = {
        "numba>=0.65.1",
    }
    expected_tabular = {
        "duckdb>=1.5",
        "h5py>=3.16",
        "numpy>=2.0",
        "openpyxl>=3.1",
        "pandas>=2.3",
        "polars>=1.40",
        "pyarrow>=24.0",
        "tables>=3.11",
    }
    tabular_package_names = {
        "duckdb",
        "h5py",
        "numpy",
        "openpyxl",
        "pandas",
        "polars",
        "pyarrow",
        "tables",
    }

    assert set(optional_dependencies["ansys"]) == expected_ansys
    assert set(optional_dependencies["viewer"]) == expected_viewer
    assert set(optional_dependencies["presentation"]) == expected_presentation
    assert set(optional_dependencies["acceleration"]) == expected_acceleration
    assert set(optional_dependencies["tabular"]) == expected_tabular
    assert expected_ansys.issubset(set(optional_dependencies["all"]))
    assert expected_viewer.issubset(set(optional_dependencies["all"]))
    assert expected_presentation.issubset(set(optional_dependencies["all"]))
    assert expected_acceleration.issubset(set(optional_dependencies["all"]))
    assert expected_tabular.issubset(set(optional_dependencies["all"]))
    assert expected_ansys.issubset(set(optional_dependencies["dev"]))
    assert expected_viewer.issubset(set(optional_dependencies["dev"]))
    assert expected_presentation.issubset(set(optional_dependencies["dev"]))
    assert expected_acceleration.issubset(set(optional_dependencies["dev"]))
    assert expected_tabular.issubset(set(optional_dependencies["dev"]))
    assert "build>=1.2" in set(optional_dependencies["dev"])
    assert "ruff>=0.8" in set(optional_dependencies["dev"])
    assert "imageio-ffmpeg>=0.6" in set(pyproject["project"]["dependencies"])
    assert "paramiko>=4,<5" in set(pyproject["project"]["dependencies"])
    assert "xy==0.0.6" in set(pyproject["project"]["dependencies"])
    assert pyproject["project"]["requires-python"] == ">=3.11"
    assert {"hpc", "ssh"}.isdisjoint(optional_dependencies)
    assert all(
        not any(dependency.startswith("paramiko") for dependency in dependencies)
        for dependencies in optional_dependencies.values()
    )
    assert not any(
        dependency.split(">=", 1)[0] in tabular_package_names
        for dependency in pyproject["project"]["dependencies"]
    )


def test_generated_egg_info_output_is_ignored() -> None:
    ignore_lines = {
        line.strip()
        for line in GITIGNORE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "*.egg-info/" in ignore_lines


def test_source_runtime_manifest_uses_only_local_package_targets() -> None:
    manifest = json.loads(RUNTIME_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 2
    assert manifest["package_profile"] == "source"
    assert manifest["packages"]["corex"]["source"] == ".."
    assert manifest["packages"]["mars"]["source"] == "../../MARS_"
    assert manifest["packages"]["mars"]["distribution"] == "mars-modal-response-solver"
    assert manifest["packages"]["mars"]["console_scripts"] == ["MARSBatch"]
    assert all(package["editable"] is True for package in manifest["packages"].values())
    assert all("wheel" not in package for package in manifest["packages"].values())


def test_frozen_spec_collects_corex_owned_mars_addon() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assert 'collect_submodules("ea_node_editor.addons.mars")' in spec_source


def test_static_tooling_baseline_is_narrow_ruff_check_only() -> None:
    pyproject = _load_pyproject()
    optional_dependencies = pyproject["project"]["optional-dependencies"]
    dev_dependencies = {dependency.lower() for dependency in optional_dependencies["dev"]}
    blocked_static_tool_names = {"pyright", "mypy", "black", "coverage"}
    tool_config = pyproject.get("tool", {})
    ruff_config = tool_config["ruff"]

    assert any(dependency.startswith("ruff>=") for dependency in dev_dependencies)
    for tool_name in blocked_static_tool_names:
        assert not any(
            dependency == tool_name
            or dependency.startswith(f"{tool_name}>")
            or dependency.startswith(f"{tool_name}<")
            or dependency.startswith(f"{tool_name}=")
            for dependency in dev_dependencies
        )
        assert tool_name not in tool_config

    assert set(ruff_config) == {"target-version", "lint"}
    assert ruff_config["target-version"] == "py311"
    assert ruff_config["lint"] == {"select": ["E9", "F63", "F7", "F82"]}


def test_web_asset_package_data_globs_cover_local_host_bundle() -> None:
    pyproject = _load_pyproject()
    package_data = set(pyproject["tool"]["setuptools"]["package-data"]["ea_node_editor"])

    assert WEB_ASSET_PACKAGE_DATA_GLOBS.issubset(package_data)


def test_windows_package_dependency_probe_executes_exact_python_and_xy_gate(tmp_path: Path) -> None:
    pwsh = shutil.which("pwsh")
    assert pwsh is not None
    matrix = tmp_path / "dependency_matrix.csv"
    completed = subprocess.run(
        [
            pwsh,
            "-NoProfile",
            "-File",
            str(BUILD_PACKAGE_PATH),
            "-PackageProfile",
            "base",
            "-DependencyProbeOnly",
            "-DependencyMatrixPath",
            str(matrix),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Dependency probe passed: Python 3.11 and xy==0.0.6." in completed.stdout
    assert matrix.is_file()
    source = BUILD_PACKAGE_PATH.read_text(encoding="utf-8")
    assert '$Availability.python_major_minor -ne "3.11"' in source
    assert '$Availability.xy_version -ne "0.0.6"' in source


def test_ui_qml_runtime_assets_are_packaged_for_pyinstaller_and_setuptools() -> None:
    pyproject = _load_pyproject()
    package_data = set(pyproject["tool"]["setuptools"]["package-data"]["ea_node_editor"])
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    contract_asset = "ui_qml/components/graph/GraphNodeSurfaceMetricContract.json"

    assert UI_QML_RUNTIME_ASSET_GLOBS.issubset(package_data)
    assert not _uncovered_asset_paths([contract_asset], package_data)
    assert '"ea_node_editor.ui_qml"' in spec_source
    assert '"ea_node_editor.ui.tooltips"' in spec_source
    assert 'includes=["*.json"]' in spec_source
    for asset_glob in (
        '"*.qml"',
        '"**/*.qml"',
        '"*.js"',
        '"**/*.js"',
        '"*.svg"',
        '"**/*.svg"',
        '"*.json"',
        '"**/*.json"',
        '"*.txt"',
        '"**/*.txt"',
    ):
        assert asset_glob in spec_source


def test_dpf_operator_catalog_is_packaged_and_required_for_full_profile_only() -> None:
    pyproject = _load_pyproject()
    package_data = set(pyproject["tool"]["setuptools"]["package-data"]["ea_node_editor"])
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)

    assert DPF_OPERATOR_CATALOG_PACKAGE_DATA_GLOB in package_data
    assert assignments["DPF_OPERATOR_CATALOG_SCHEMA_VERSION"] == 1
    assert '"ea_node_editor.addons.ansys_dpf"' in spec_source
    assert 'includes=["operator_catalog.json"]' in spec_source
    assert "def _require_matching_dpf_operator_catalog()" in spec_source
    assert (
        "if full_profile_enabled:\n"
        "        _require_full_stack()\n"
        "        _require_matching_dpf_operator_catalog()"
    ) in spec_source
    assert "if viewer_payload_enabled:\n    _require_matching_dpf_operator_catalog()" not in spec_source


def test_mockup_qml_runtime_assets_are_packaged_for_pyinstaller_and_setuptools() -> None:
    pyproject = _load_pyproject()
    package_data = set(pyproject["tool"]["setuptools"]["package-data"]["ea_node_editor"])
    spec_source = SPEC_PATH.read_text(encoding="utf-8")

    assert MOCKUP_RUNTIME_ASSET_GLOBS.issubset(package_data)
    assert '"mockups/**/*.qml"' in spec_source
    assert '"mockups/**/*.js"' in spec_source


def test_curated_dpf_workflow_help_is_packaged_for_pyinstaller_and_setuptools() -> None:
    pyproject = _load_pyproject()
    package_data = set(pyproject["tool"]["setuptools"]["package-data"]["ea_node_editor"])
    spec_source = SPEC_PATH.read_text(encoding="utf-8")

    assert DPF_WORKFLOW_HELP_ASSET_GLOB in package_data
    assert f'"{DPF_WORKFLOW_HELP_ASSET_GLOB}"' in spec_source


def test_mars_icon_is_packaged_for_pyinstaller_and_setuptools() -> None:
    pyproject = _load_pyproject()
    package_data = set(pyproject["tool"]["setuptools"]["package-data"]["ea_node_editor"])
    spec_source = SPEC_PATH.read_text(encoding="utf-8")

    assert MARS_ICON_PACKAGE_DATA_GLOB in package_data
    assert f'"{MARS_ICON_PACKAGE_DATA_GLOB}"' in spec_source


def test_application_fonts_are_packaged_for_pyinstaller_and_setuptools() -> None:
    pyproject = _load_pyproject()
    package_data = set(pyproject["tool"]["setuptools"]["package-data"]["ea_node_editor"])
    spec_source = SPEC_PATH.read_text(encoding="utf-8")

    assert APPLICATION_FONT_PACKAGE_DATA_GLOBS.issubset(package_data)
    for asset_glob in APPLICATION_FONT_PACKAGE_DATA_GLOBS:
        assert f'"{asset_glob}"' in spec_source


def test_web_asset_package_data_and_pyinstaller_includes_cover_generated_excalidraw_bundle() -> None:
    pyproject = _load_pyproject()
    package_data = set(pyproject["tool"]["setuptools"]["package-data"]["ea_node_editor"])
    assignments = _literal_assignments(SPEC_PATH)
    pyinstaller_includes = set(assignments["WEB_ASSET_DATA_INCLUDES"])
    asset_paths = _excalidraw_host_asset_paths()

    assert "web_assets/excalidraw_host/index.html" in asset_paths
    assert asset_paths
    assert not _uncovered_asset_paths(asset_paths, package_data)
    assert not _uncovered_asset_paths(asset_paths, pyinstaller_includes)


def test_spec_declares_viewer_profile_hooks_and_runtime_assets() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)

    assert assignments["PACKAGE_PROFILE_ENV_VAR"] == "EA_NODE_EDITOR_PACKAGE_PROFILE"
    assert assignments["BASE_PACKAGE_PROFILE"] == "base"
    assert assignments["VIEWER_PACKAGE_PROFILE"] == "viewer"
    assert assignments["FULL_PACKAGE_PROFILE"] == "full"
    assert assignments["PACKAGE_PROFILES"] == ("base", "viewer", "web", "full")
    assert {
        "OCP",
        "pyvista",
        "pyvistaqt",
        "vtkmodules",
    }.issubset(set(assignments["VIEWER_RUNTIME_HIDDENIMPORT_PACKAGES"]))
    assert not {
        "ansys.dpf.core",
        "ansys.dpf.post",
        "ansys.dpf.gate",
        "ansys.grpc.dpf",
    }.intersection(assignments["VIEWER_RUNTIME_HIDDENIMPORT_PACKAGES"])
    assert {
        "cadquery-ocp-novtk",
        "cadquery-ocp-proxy",
        "pyvista",
        "pyvistaqt",
        "vtk",
    }.issubset(set(assignments["VIEWER_RUNTIME_METADATA_DISTRIBUTIONS"]))
    assert not {"ansys-dpf-core", "ansys-dpf-post"}.intersection(
        assignments["VIEWER_RUNTIME_METADATA_DISTRIBUTIONS"]
    )
    assert assignments["VIEWER_SIBLING_BINARY_PATTERNS"]["vtkmodules"]["vtk.libs"] == ("*.dll",)
    assert assignments["VIEWER_SIBLING_BINARY_PATTERNS"]["OCP"]["cadquery_ocp_novtk.libs"] == ("*.dll",)
    assert assignments["VIEWER_DATA_FILE_PATTERNS"]["pyvistaqt"] == ("data/*.png",)

    assert "viewer_payload_enabled = package_profile in {VIEWER_PACKAGE_PROFILE, FULL_PACKAGE_PROFILE}" in spec_source
    assert "if viewer_payload_enabled:" in spec_source
    assert "hiddenimports += _collect_viewer_hiddenimports()" in spec_source
    assert "datas += _collect_viewer_datas()" in spec_source
    assert "binaries += _collect_viewer_sibling_binaries()" in spec_source
    assert 'PROJECT_ROOT / "THIRD_PARTY_NOTICES.md"' in spec_source
    assert 'PROJECT_ROOT / "licenses"' in spec_source
    assert "binaries=binaries" in spec_source


def test_spec_declares_full_profile_as_all_runtime_stack() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)

    expected_required_modules = {
        "OCP",
        "ansys.dpf.core",
        "ansys.dpf.post",
        "ansys.mechanical.core",
        "duckdb",
        "h5py",
        "llvmlite",
        "matplotlib",
        "numba",
        "numpy",
        "openpyxl",
        "pandas",
        "polars",
        "pyarrow",
        "pyqtgraph",
        "pyvista",
        "pyvistaqt",
        "scipy",
        "tables",
        "vtkmodules",
    }
    expected_hiddenimports = {
        "ansys.dpf.core",
        "ansys.dpf.gate",
        "ansys.dpf.post",
        "ansys.grpc.dpf",
        "ansys.mechanical.core",
        "matplotlib",
        "numba",
        "pyqtgraph",
        "scipy",
    }
    expected_metadata = {
        "ansys-dpf-core",
        "ansys-dpf-post",
        "ansys-mechanical-core",
        "llvmlite",
        "matplotlib",
        "numba",
        "pyqtgraph",
        "scipy",
    }

    assert expected_required_modules.issubset(set(assignments["FULL_RUNTIME_REQUIRED_PACKAGES"]))
    assert expected_hiddenimports.issubset(set(assignments["FULL_RUNTIME_HIDDENIMPORT_PACKAGES"]))
    assert expected_metadata.issubset(set(assignments["FULL_RUNTIME_METADATA_DISTRIBUTIONS"]))
    assert "paramiko" not in assignments["FULL_RUNTIME_REQUIRED_PACKAGES"]
    assert "paramiko" not in assignments["FULL_RUNTIME_HIDDENIMPORT_PACKAGES"]
    assert "paramiko" not in assignments["FULL_RUNTIME_METADATA_DISTRIBUTIONS"]
    assert '_require_modules("Every", ("paramiko", "xy"))' in spec_source
    assert 'hiddenimports += collect_submodules("paramiko")' in spec_source
    assert 'datas += copy_metadata("paramiko")' in spec_source
    assert 'hiddenimports += ["xy.components"]' in spec_source
    assert 'datas += copy_metadata("xy")' in spec_source
    assert 'collect_data_files("xy", includes=["_native_lib/*"])' in spec_source
    assert 'PROJECT_ROOT / "licenses" / "PARAMIKO-LGPL-2.1.txt"' in spec_source
    assert (REPO_ROOT / "licenses" / "PARAMIKO-LGPL-2.1.txt").is_file()
    assert "## Paramiko" in (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "## XY" in (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert (REPO_ROOT / "licenses" / "XY-APACHE-2.0-NOTICE.txt").is_file()
    assert assignments["FULL_NAMESPACE_BINARY_PATTERNS"]["ansys.dpf.gatebin"] == ("*.dll",)
    assert assignments["QT_BINDING_EXCLUDES"] == ("PyQt5", "PySide2", "PySide6")
    assert "full_profile_enabled = package_profile == FULL_PACKAGE_PROFILE" in spec_source
    assert "def _require_full_stack()" in spec_source
    assert "_require_modules(\"Full\", FULL_RUNTIME_REQUIRED_PACKAGES)" in spec_source
    assert "hiddenimports += _collect_full_hiddenimports()" in spec_source
    assert "datas += _collect_full_datas()" in spec_source
    assert "binaries += _collect_full_namespace_binaries()" in spec_source
    assert 'hookspath=[str(PROJECT_ROOT / "scripts" / "pyinstaller_hooks")]' in spec_source
    assert "excludes=analysis_excludes" in spec_source


def test_local_pyarrow_hook_limits_full_profile_collection_to_runtime_modules() -> None:
    hook_source = PYINSTALLER_PYARROW_HOOK_PATH.read_text(encoding="utf-8")

    assert "collect_submodules" not in hook_source
    assert "collect_dynamic_libs(\"pyarrow\")" in hook_source
    assert "copy_metadata(\"pyarrow\")" in hook_source
    for module_name in (
        "pyarrow.compute",
        "pyarrow.csv",
        "pyarrow.dataset",
        "pyarrow.fs",
        "pyarrow.parquet",
    ):
        assert f'"{module_name}"' in hook_source
    for excluded_pattern in (
        "**/benchmark*",
        "**/conftest.py",
        "**/tests/**",
        "**/*_tests.*",
    ):
        assert f'"{excluded_pattern}"' in hook_source


def test_spec_declares_tabular_optional_hiddenimports_and_metadata() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)
    expected_tabular_modules = (
        "numpy",
        "pandas",
        "polars",
        "pyarrow",
        "pyarrow.compute",
        "pyarrow.csv",
        "pyarrow.dataset",
        "pyarrow.fs",
        "pyarrow.parquet",
        "duckdb",
        "openpyxl",
        "h5py",
        "tables",
    )

    assert assignments["TABULAR_RUNTIME_HIDDENIMPORT_MODULES"] == expected_tabular_modules
    assert assignments["TABULAR_RUNTIME_METADATA_DISTRIBUTIONS"] == (
        "numpy",
        "pandas",
        "polars",
        "pyarrow",
        "duckdb",
        "openpyxl",
        "h5py",
        "tables",
    )
    assert "def _collect_tabular_hiddenimports()" in spec_source
    assert "def _collect_tabular_datas()" in spec_source
    assert "hiddenimports += _collect_tabular_hiddenimports()" in spec_source
    assert "collect_submodules(package_name, filter=_include_tabular_hiddenimport)" not in spec_source
    assert "TABULAR_RUNTIME_HIDDENIMPORT_EXCLUDED_SEGMENTS" not in spec_source
    assert "datas += _collect_tabular_datas()" in spec_source
    assert "if _module_available(module_name)" in spec_source
    assert "data_files += copy_metadata(distribution_name)" in spec_source


def test_spec_excludes_unowned_ml_and_vision_stacks_from_pyinstaller_analysis() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)

    assert assignments["PYINSTALLER_EXCLUDES"] == (
        "PyQt5",
        "PySide2",
        "PySide6",
        "accelerate",
        "cv2",
        "huggingface_hub",
        "onnxruntime",
        "safetensors",
        "tensorflow",
        "tokenizers",
        "torch",
        "torchvision",
        "transformers",
    )
    assert 'NON_FULL_RUNTIME_EXCLUDES = ("ansys",)' in spec_source
    assert assignments["NON_FULL_RUNTIME_DATA_EXCLUDE_PREFIXES"] == ("ansys_",)
    assert "analysis_excludes = list(PYINSTALLER_EXCLUDES)" in spec_source
    assert "if not full_profile_enabled:" in spec_source
    assert "analysis_excludes.extend(NON_FULL_RUNTIME_EXCLUDES)" in spec_source
    assert "excludes=analysis_excludes" in spec_source
    assert "if not _matches_module_prefix(module_name, analysis_excludes)" in spec_source
    assert "def _matches_data_target_prefix(target_name: str, prefixes) -> bool:" in spec_source
    assert "if not _matches_data_target_prefix(entry[0], NON_FULL_RUNTIME_DATA_EXCLUDE_PREFIXES)" in spec_source


def test_spec_suppresses_native_crashers_in_bindepend_child_imports() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)

    assert assignments["BINDEPEND_IMPORT_SUPPRESSIONS"] == (
        "ea_node_editor",
        "llvmlite",
        "numba",
        "pyarrow",
    )
    assert "def _suppress_bindepend_native_imports()" in spec_source
    assert "from PyInstaller.building import build_main" in spec_source
    assert "find_binary_dependencies_without_native_crashers" in spec_source
    assert "def _matches_module_prefix(module_name: str, prefixes) -> bool:" in spec_source
    assert "module_name == prefix or module_name.startswith(f\"{prefix}.\")" in spec_source
    assert "if not _matches_module_prefix(package_name, BINDEPEND_IMPORT_SUPPRESSIONS)" in spec_source
    assert "_suppress_bindepend_native_imports()\n\na = Analysis(" in spec_source


def test_spec_declares_web_profile_assets_and_guarded_webengine_hiddenimports() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)

    assert assignments["WEB_PACKAGE_PROFILE"] == "web"
    assert assignments["PACKAGE_PROFILES"] == ("base", "viewer", "web", "full")
    assert set(assignments["WEB_RUNTIME_HIDDENIMPORT_MODULES"]) == WEB_RUNTIME_HIDDENIMPORT_MODULES
    assert WEB_ASSET_PACKAGE_DATA_GLOBS.issubset(set(assignments["WEB_ASSET_DATA_INCLUDES"]))

    assert "hiddenimports += _collect_web_hiddenimports(require=True)" in spec_source
    assert "if missing and require:" in spec_source
    assert "Packaging requires the PyQt6 WebEngine/WebChannel runtime stack" in spec_source
    assert "datas += collect_data_files(\n    \"ea_node_editor\",\n    includes=list(WEB_ASSET_DATA_INCLUDES)," in spec_source


def test_spec_declares_qt_multimedia_hiddenimports_for_video_panel() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)

    assert set(assignments["QT_MULTIMEDIA_RUNTIME_HIDDENIMPORT_MODULES"]) == QT_MULTIMEDIA_RUNTIME_HIDDENIMPORT_MODULES
    assert "def _collect_qt_multimedia_hiddenimports" in spec_source
    assert "hiddenimports += _collect_qt_multimedia_hiddenimports(require=True)" in spec_source
    assert "Packaging requires the PyQt6 Qt Multimedia runtime stack" in spec_source


def test_spec_declares_imageio_ffmpeg_payload_for_video_trim() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)

    assert assignments["IMAGEIO_FFMPEG_RUNTIME_MODULES"] == ("imageio_ffmpeg",)
    assert assignments["IMAGEIO_FFMPEG_METADATA_DISTRIBUTIONS"] == ("imageio-ffmpeg",)
    assert assignments["IMAGEIO_FFMPEG_DATA_INCLUDES"] == ("binaries/*",)
    assert "def _collect_imageio_ffmpeg_payload" in spec_source
    assert "Packaging requires imageio-ffmpeg for bundled Video Panel trimming." in spec_source
    assert 'collect_data_files("imageio_ffmpeg", includes=list(IMAGEIO_FFMPEG_DATA_INCLUDES))' in spec_source
    assert "data_files += copy_metadata(distribution_name)" in spec_source
    assert "imageio_ffmpeg_hiddenimports, imageio_ffmpeg_datas = _collect_imageio_ffmpeg_payload(require=True)" in spec_source
    assert "hiddenimports += imageio_ffmpeg_hiddenimports" in spec_source
    assert "datas += imageio_ffmpeg_datas" in spec_source


def test_mcf_dpf_standalone_build_bundles_native_dpf_clients() -> None:
    build_source = BUILD_MCF_DPF_GUI_PATH.read_text(encoding="utf-8")

    assert '"ansys.dpf.gatebin"' in build_source
    assert '"--collect-all", "ansys.dpf.gatebin"' in build_source
    assert '$dpfGateBinFolder = Join-Path $internalFolder "ansys\\dpf\\gatebin"' in build_source
    assert '"Ans.Dpf.GrpcClient.dll"' in build_source
    assert '"DPFClientAPI.dll"' in build_source
    assert "Expected bundled DPF client DLL was not created" in build_source


def test_mcf_dpf_standalone_build_bundles_animation_icons() -> None:
    build_source = BUILD_MCF_DPF_GUI_PATH.read_text(encoding="utf-8")

    assert (
        '"scripts\\mcf_dpf_section_resultants\\assets\\icons"'
        in build_source
    )
    assert '"mcf_dpf_section_resultants\\icons"' in build_source
    for asset_name in (
        "player-track-prev.svg",
        "player-play.svg",
        "player-pause.svg",
        "player-track-next.svg",
        "player-stop.svg",
        "loader-2.svg",
        "TABLER_SOURCES.txt",
        "TABLER_LICENSE.txt",
    ):
        assert f'"{asset_name}"' in build_source
    assert '"--add-data"' in build_source
    assert '"--hidden-import", "PyQt6.QtSvg"' in build_source
    assert "Expected bundled animation icon asset was not created" in build_source


def test_windows_build_scripts_use_profile_specific_packaging_switches() -> None:
    build_package_source = BUILD_PACKAGE_PATH.read_text(encoding="utf-8")
    build_installer_source = BUILD_INSTALLER_PATH.read_text(encoding="utf-8")
    build_excalidraw_host_source = BUILD_EXCALIDRAW_HOST_PATH.read_text(encoding="utf-8")
    sign_release_source = SIGN_RELEASE_PATH.read_text(encoding="utf-8")

    assert '[ValidateSet("base", "viewer", "web", "full")]' in build_package_source
    assert '$PackageProfile = "base"' in build_package_source
    assert 'EA_NODE_EDITOR_PACKAGE_PROFILE' in build_package_source
    assert 'Assert-PackageProfileDependencies' in build_package_source
    assert 'pyqt6_webengine_core = [bool]$parsed.pyqt6_webengine_core' in build_package_source
    assert 'pyqt6_webengine_quick = [bool]$parsed.pyqt6_webengine_quick' in build_package_source
    assert 'pyqt6_webengine_widgets = [bool]$parsed.pyqt6_webengine_widgets' in build_package_source
    assert 'pyqt6_webchannel = [bool]$parsed.pyqt6_webchannel' in build_package_source
    assert '"pyqt6_qtmultimedia": "PyQt6.QtMultimedia"' in build_package_source
    assert 'pyqt6_qtmultimedia = [bool]$parsed.pyqt6_qtmultimedia' in build_package_source
    assert '"imageio_ffmpeg": "imageio_ffmpeg"' in build_package_source
    assert 'imageio_ffmpeg = [bool]$parsed.imageio_ffmpeg' in build_package_source
    assert 'imageio_ffmpeg_binary = [bool]$parsed.imageio_ffmpeg_binary' in build_package_source
    assert 'ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()' in build_package_source
    assert '"pypa_build": "build.__main__"' in build_package_source
    assert 'pypa_build = [bool]$parsed.pypa_build' in build_package_source
    assert '"ocp": "OCP"' in build_package_source
    assert 'ocp = [bool]$parsed.ocp' in build_package_source
    for full_dependency in (
        ("ansys_dpf_core", "ansys.dpf.core"),
        ("ansys_dpf_post", "ansys.dpf.post"),
        ("ansys_mechanical_core", "ansys.mechanical.core"),
        ("llvmlite", "llvmlite"),
        ("matplotlib", "matplotlib"),
        ("numba", "numba"),
        ("paramiko", "paramiko"),
        ("xy", "xy"),
        ("pyqtgraph", "pyqtgraph"),
        ("scipy", "scipy"),
    ):
        key, import_name = full_dependency
        assert f'"{key}": "{import_name}"' in build_package_source
        assert f'{key} = [bool]$parsed.{key}' in build_package_source
    for tabular_dependency in ("numpy", "pandas", "polars", "pyarrow", "duckdb", "openpyxl", "h5py", "tables"):
        assert f'"{tabular_dependency}": "{tabular_dependency}"' in build_package_source
        assert f'{tabular_dependency} = [bool]$parsed.{tabular_dependency}' in build_package_source
        assert f'dependency = "{tabular_dependency}"' in build_package_source
    assert 'dependency = "PyQt6-WebEngine"' in build_package_source
    assert 'dependency = "PyQt6.QtWebChannel"' in build_package_source
    assert 'dependency = "PyQt6.QtMultimedia"' in build_package_source
    assert 'dependency = "imageio-ffmpeg"' in build_package_source
    assert 'dependency = "build"' in build_package_source
    assert 'Required packaging tool for every package profile.' in build_package_source
    assert 'dependency = "scipy"' in build_package_source
    assert 'dependency = "paramiko"' in build_package_source
    assert 'dependency = "xy==0.0.6"' in build_package_source
    assert 'dependency = "matplotlib"' in build_package_source
    assert 'dependency = "numba"' in build_package_source
    assert 'dependency = "llvmlite"' in build_package_source
    assert 'dependency = "pyqtgraph"' in build_package_source
    assert 'dependency = "ansys-dpf-post"' in build_package_source
    assert 'dependency = "ansys-mechanical-core"' in build_package_source
    assert 'dependency = "cadquery-ocp-novtk"' in build_package_source
    assert '@{ Key = "ocp"; Display = "cadquery-ocp-novtk" }' in build_package_source
    assert 'Ansys DPF is excluded from base, viewer, and web package profiles.' in build_package_source
    assert 'dependency_group = "media"' in build_package_source
    assert 'dependency_group = "ssh_sftp"' in build_package_source
    assert 'dependency_group = "hpc"' not in build_package_source
    assert 'dependency_group = "plot"' in build_package_source
    assert 'dependency_group = "acceleration"' in build_package_source
    assert 'Video Panel playback uses Qt Multimedia MediaPlayer, VideoOutput, and AudioOutput.' in build_package_source
    assert 'Video Panel trim-save uses imageio-ffmpeg' in build_package_source
    assert 'dependency_group = "tabular"' in build_package_source
    assert 'Tabular Data stays optional' in build_package_source
    assert 'Full profile bundles every current runtime extra' in build_package_source
    assert 'Full profile bundles the Numba acceleration backend' in build_package_source
    assert 'Full profile bundles every tabular backend' in build_package_source
    assert 'Install the all/dev dependency stack before running a full-profile package build.' in build_package_source
    assert 'Install the tabular extra before packaging when tabular workflows are required.' in build_package_source
    assert 'All package profiles bundle the local WebEngine/WebChannel runtime' in build_package_source
    assert 'All package profiles bundle Paramiko for built-in SSH/SFTP nodes' in build_package_source
    assert 'Required dependency for every package profile.' in build_package_source
    assert build_package_source.count('@{ Key = "paramiko"; Display = "paramiko" }') == 1
    assert build_package_source.count('@{ Key = "xy"; Display = "xy==0.0.6" }') == 1
    assert 'artifacts\\pyinstaller' in build_package_source
    assert '$runtimeBundleDirName = "runtime"' in build_package_source
    assert '$runtimeManifestFileName = "runtime_manifest.json"' in build_package_source
    assert '$runtimeWheelPattern = "corex_node_editor-*.whl"' in build_package_source
    assert "[System.IO.File]::WriteAllText(" in build_package_source
    assert "[System.Text.UTF8Encoding]::new($false)" in build_package_source
    assert r'$MarsSourcePath = "..\MARS_"' in build_package_source
    assert '$MarsWheelPath = ""' in build_package_source
    assert 'function New-CorexRuntimeBundle' in build_package_source
    assert 'function Get-WheelPackageMetadata' in build_package_source
    assert '"build"' in build_package_source
    assert '"--wheel"' in build_package_source
    assert 'schema_version = 2' in build_package_source
    assert 'packages = [ordered]@{' in build_package_source
    assert 'console_scripts = @("MARSBatch")' in build_package_source
    assert 'foreach ($packageId in @("corex", "mars"))' in build_package_source
    assert 'extras = @("all")' in build_package_source
    assert 'Assert-CorexRuntimeBundle -RuntimeBundlePath $runtimeBundlePath' in build_package_source
    assert 'New-CorexRuntimeBundle -DistPath $distDir -Profile $PackageProfile' in build_package_source
    assert 'artifacts\\releases\\packaging\\$PackageProfile\\dependency_matrix.csv' in build_package_source
    assert 'Resolve-PyInstallerProfilePath -Kind "dist" -Profile $PackageProfile' in build_package_source
    assert 'Resolve-PyInstallerProfilePath -Kind "build" -Profile $PackageProfile' in build_package_source
    assert '[System.IO.Path]::GetTempFileName()' in build_package_source
    assert 'Path(sys.argv[1]).write_text' in build_package_source
    assert 'Start-Process -FilePath $PythonExecutable -ArgumentList @($probeScriptPath, $probeOutputPath) -PassThru -Wait' in build_package_source
    assert 'Start-Process -FilePath $pythonExe -ArgumentList $buildArgs -PassThru -Wait -NoNewWindow' in build_package_source
    assert '$SmokeSeconds = 30' in build_package_source
    assert 'EA_PROFILE_AUTOQUIT' in build_package_source
    assert 'EA_PROFILE_STARTUP' in build_package_source
    assert 'EA_SIGNAL_PLOT_PACKAGE_SMOKE' in build_package_source
    assert '-SignalPlotRender' in build_package_source
    assert 'Signal Plot render smoke test' in build_package_source
    assert '$process.WaitForExit($TimeoutSeconds * 1000)' in build_package_source
    assert 'executable did not complete autoquit startup' in build_package_source
    assert 'A modal error dialog or startup hang may be blocking the packaged app.' in build_package_source
    assert '$processStartInfo.UseShellExecute = $false' in build_package_source
    assert '$processStartInfo.RedirectStandardError = $true' in build_package_source
    assert 'process stayed alive' not in build_package_source

    assert '[ValidateSet("base", "viewer", "web", "full")]' in build_installer_source
    assert '$runtimeBundleDirName = "runtime"' in build_installer_source
    assert '$runtimeManifestFileName = "runtime_manifest.json"' in build_installer_source
    assert '$manifest.schema_version -ne 2' in build_installer_source
    assert 'foreach ($packageId in @("corex", "mars"))' in build_installer_source
    assert 'function Assert-CorexRuntimeBundlePayload' in build_installer_source
    assert 'Assert-CorexRuntimeBundlePayload -AppRoot $payloadRoot -Label "Installer payload"' in build_installer_source
    assert 'Assert-CorexRuntimeBundlePayload -AppRoot (Join-Path $validationInstallRoot $packageAppName) -Label "Installed app"' in build_installer_source
    assert 'Resolve-PyInstallerDistPath -Profile $PackageProfile' in build_installer_source
    assert 'Resolve-InstallerOutputRoot -Profile $PackageProfile' in build_installer_source
    assert 'package_profile = $PackageProfile' in build_installer_source
    assert 'New-InstallerBundleZip' in build_installer_source
    assert 'Get-Command "tar.exe"' in build_installer_source
    assert 'Resolve-PowerShellHostPath' in build_installer_source
    assert '$validationShellPath = Resolve-PowerShellHostPath' in build_installer_source
    assert 'Invoke-PowerShellScriptFile -HostPath $validationShellPath' in build_installer_source
    assert '$SmokeSeconds = 30' in build_installer_source
    assert 'EA_PROFILE_AUTOQUIT' in build_installer_source
    assert 'EA_PROFILE_STARTUP' in build_installer_source
    assert '$process.WaitForExit($TimeoutSeconds * 1000)' in build_installer_source
    assert 'executable did not complete autoquit startup' in build_installer_source
    assert 'A modal error dialog or startup hang may be blocking the packaged app.' in build_installer_source
    assert '$processStartInfo.UseShellExecute = $false' in build_installer_source
    assert '$processStartInfo.RedirectStandardError = $true' in build_installer_source
    assert 'process stayed alive' not in build_installer_source

    assert 'ea_node_editor\\web_assets\\excalidraw_host' in build_excalidraw_host_source
    assert 'npm ci' in build_excalidraw_host_source
    assert 'npm run build' in build_excalidraw_host_source
    assert 'Select-String -Pattern "https?://"' in build_excalidraw_host_source
    assert 'Excalidraw host bundle contains remote URL references' in build_excalidraw_host_source

    assert '[ValidateSet("base", "viewer", "web", "full")]' in sign_release_source
    assert '$PackageProfile = "base"' in sign_release_source
    assert 'Resolve-SigningOutputRoot -Profile $PackageProfile' in sign_release_source
    assert 'Resolve-PackagedExecutablePath -Profile $PackageProfile' in sign_release_source
    assert 'Resolve-InstallerRoot -Profile $PackageProfile' in sign_release_source
    assert 'package_profile = $PackageProfile' in sign_release_source
