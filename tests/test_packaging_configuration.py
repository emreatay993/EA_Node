from __future__ import annotations

import ast
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 uses tomli in this repo venv.
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
SPEC_PATH = REPO_ROOT / "ea_node_editor.spec"
BUILD_PACKAGE_PATH = REPO_ROOT / "scripts" / "build_windows_package.ps1"
BUILD_INSTALLER_PATH = REPO_ROOT / "scripts" / "build_windows_installer.ps1"
SIGN_RELEASE_PATH = REPO_ROOT / "scripts" / "sign_release_artifacts.ps1"


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


def test_optional_dependency_groups_wire_ansys_and_viewer_into_all_and_dev() -> None:
    pyproject = _load_pyproject()
    optional_dependencies = pyproject["project"]["optional-dependencies"]

    expected_ansys = {
        "ansys-dpf-core>=0.15",
        "ansys-dpf-post>=0.11",
    }
    expected_viewer = {"pyvista>=0.47", "pyvistaqt>=0.11", "vtk>=9.6"}

    assert set(optional_dependencies["ansys"]) == expected_ansys
    assert set(optional_dependencies["viewer"]) == expected_viewer
    assert expected_ansys.issubset(set(optional_dependencies["all"]))
    assert expected_viewer.issubset(set(optional_dependencies["all"]))
    assert expected_ansys.issubset(set(optional_dependencies["dev"]))
    assert expected_viewer.issubset(set(optional_dependencies["dev"]))


def test_spec_declares_viewer_profile_hooks_and_runtime_assets() -> None:
    spec_source = SPEC_PATH.read_text(encoding="utf-8")
    assignments = _literal_assignments(SPEC_PATH)

    assert assignments["PACKAGE_PROFILE_ENV_VAR"] == "EA_NODE_EDITOR_PACKAGE_PROFILE"
    assert assignments["BASE_PACKAGE_PROFILE"] == "base"
    assert assignments["VIEWER_PACKAGE_PROFILE"] == "viewer"
    assert {
        "ansys.dpf.core",
        "ansys.dpf.post",
        "pyvista",
        "pyvistaqt",
        "vtkmodules",
    }.issubset(set(assignments["VIEWER_RUNTIME_HIDDENIMPORT_PACKAGES"]))
    assert {
        "ansys-dpf-core",
        "ansys-dpf-post",
        "pyvista",
        "pyvistaqt",
        "vtk",
    }.issubset(set(assignments["VIEWER_RUNTIME_METADATA_DISTRIBUTIONS"]))
    assert assignments["VIEWER_NAMESPACE_BINARY_PATTERNS"]["ansys.dpf.gatebin"] == ("*.dll",)
    assert assignments["VIEWER_SIBLING_BINARY_PATTERNS"]["vtkmodules"]["vtk.libs"] == ("*.dll",)
    assert assignments["VIEWER_DATA_FILE_PATTERNS"]["pyvistaqt"] == ("data/*.png",)

    assert "viewer_profile_enabled = package_profile == VIEWER_PACKAGE_PROFILE" in spec_source
    assert "if viewer_profile_enabled:" in spec_source
    assert "hiddenimports += _collect_viewer_hiddenimports()" in spec_source
    assert "datas += _collect_viewer_datas()" in spec_source
    assert "binaries += _collect_viewer_namespace_binaries()" in spec_source
    assert "binaries += _collect_viewer_sibling_binaries()" in spec_source
    assert "binaries=binaries" in spec_source


def test_windows_build_scripts_use_profile_specific_packaging_switches() -> None:
    build_package_source = BUILD_PACKAGE_PATH.read_text(encoding="utf-8")
    build_installer_source = BUILD_INSTALLER_PATH.read_text(encoding="utf-8")
    sign_release_source = SIGN_RELEASE_PATH.read_text(encoding="utf-8")

    assert '[ValidateSet("base", "viewer")]' in build_package_source
    assert '$PackageProfile = "base"' in build_package_source
    assert 'EA_NODE_EDITOR_PACKAGE_PROFILE' in build_package_source
    assert 'Assert-PackageProfileDependencies' in build_package_source
    assert 'artifacts\\pyinstaller' in build_package_source
    assert 'artifacts\\releases\\packaging\\$PackageProfile\\dependency_matrix.csv' in build_package_source
    assert 'Join-Path (Join-Path $artifactRoot "dist") $PackageProfile' in build_package_source
    assert 'Join-Path (Join-Path $artifactRoot "build") $PackageProfile' in build_package_source
    assert '[System.IO.Path]::GetTempFileName()' in build_package_source
    assert 'Path(sys.argv[1]).write_text' in build_package_source
    assert 'Start-Process -FilePath $PythonExecutable -ArgumentList @($probeScriptPath, $probeOutputPath) -PassThru -Wait' in build_package_source
    assert 'Start-Process -FilePath $pythonExe -ArgumentList $buildArgs -PassThru -Wait -NoNewWindow' in build_package_source

    assert '[ValidateSet("base", "viewer")]' in build_installer_source
    assert '$DistPath = "artifacts\\pyinstaller\\dist\\$PackageProfile\\COREX_Node_Editor"' in build_installer_source
    assert '$OutputRoot = "artifacts\\releases\\installer\\$PackageProfile"' in build_installer_source
    assert 'package_profile = $PackageProfile' in build_installer_source
    assert 'New-InstallerBundleZip' in build_installer_source
    assert 'Get-Command "tar.exe"' in build_installer_source
    assert 'Resolve-PowerShellHostPath' in build_installer_source
    assert '$validationShellPath = Resolve-PowerShellHostPath' in build_installer_source
    assert 'Invoke-PowerShellScriptFile -HostPath $validationShellPath' in build_installer_source

    assert '[ValidateSet("base", "viewer")]' in sign_release_source
    assert '$PackageProfile = "base"' in sign_release_source
    assert 'artifacts\\releases\\signing\\$PackageProfile' in sign_release_source
    assert 'artifacts\\pyinstaller\\dist\\$PackageProfile\\COREX_Node_Editor\\COREX_Node_Editor.exe' in sign_release_source
    assert 'artifacts\\releases\\installer\\$PackageProfile' in sign_release_source
    assert 'package_profile = $PackageProfile' in sign_release_source
