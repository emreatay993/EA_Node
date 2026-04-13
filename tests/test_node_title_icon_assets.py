from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from ea_node_editor.nodes.builtins.ansys_dpf_compute import (
    DpfExportNodePlugin,
    DpfFieldOpsNodePlugin,
    DpfMeshExtractNodePlugin,
    DpfMeshScopingNodePlugin,
    DpfModelNodePlugin,
    DpfResultFieldNodePlugin,
    DpfResultFileNodePlugin,
    DpfTimeScopingNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_viewer import DpfViewerNodePlugin
from ea_node_editor.nodes.builtins.core import (
    BranchNodePlugin,
    ConstantNodePlugin,
    EndNodePlugin,
    LoggerNodePlugin,
    OnFailureNodePlugin,
    PythonScriptNodePlugin,
    StartNodePlugin,
)
from ea_node_editor.nodes.builtins.hpc import (
    HPCFetchResultNodePlugin,
    HPCMonitorNodePlugin,
    HPCOnStatusNodePlugin,
    HPCSubmitNodePlugin,
)
from ea_node_editor.nodes.builtins.integrations_email import EmailSendNodePlugin
from ea_node_editor.nodes.builtins.integrations_file_io import FileReadNodePlugin, FileWriteNodePlugin
from ea_node_editor.nodes.builtins.integrations_process import ProcessRunNodePlugin
from ea_node_editor.nodes.builtins.integrations_spreadsheet import (
    ExcelReadNodePlugin,
    ExcelWriteNodePlugin,
)
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_TYPE_ID,
    SubnodeInputNodePlugin,
    SubnodeNodePlugin,
    SubnodeOutputNodePlugin,
)
from ea_node_editor.ui_qml.node_title_icon_sources import (
    NODE_TITLE_ICON_ASSET_ROOT,
    SUPPORTED_NODE_TITLE_ICON_SUFFIXES,
    resolve_node_title_icon_source,
    title_icon_source_for_node_payload,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
SPEC_PATH = PROJECT_ROOT / "ea_node_editor.spec"

_MIGRATED_TITLE_ICON_SPECS = {
    "core.start": (StartNodePlugin, "core/play_arrow.svg"),
    "core.end": (EndNodePlugin, "core/stop.svg"),
    "core.constant": (ConstantNodePlugin, "core/data_object.svg"),
    "core.logger": (LoggerNodePlugin, "core/article.svg"),
    "core.python_script": (PythonScriptNodePlugin, "core/code.svg"),
    "core.on_failure": (OnFailureNodePlugin, "core/error_outline.svg"),
    "core.branch": (BranchNodePlugin, "core/call_split.svg"),
    "hpc.submit": (HPCSubmitNodePlugin, "hpc/cloud_upload.svg"),
    "hpc.monitor": (HPCMonitorNodePlugin, "hpc/monitor_heart.svg"),
    "hpc.on_status": (HPCOnStatusNodePlugin, "hpc/alt_route.svg"),
    "hpc.fetch_result": (HPCFetchResultNodePlugin, "hpc/cloud_download.svg"),
    "io.email_send": (EmailSendNodePlugin, "integrations/mail.svg"),
    "io.file_read": (FileReadNodePlugin, "integrations/description.svg"),
    "io.file_write": (FileWriteNodePlugin, "integrations/save.svg"),
    "io.process_run": (ProcessRunNodePlugin, "integrations/terminal.svg"),
    "io.excel_read": (ExcelReadNodePlugin, "integrations/table_view.svg"),
    "io.excel_write": (ExcelWriteNodePlugin, "integrations/download.svg"),
    SUBNODE_TYPE_ID: (SubnodeNodePlugin, "subnode/account_tree.svg"),
    SUBNODE_INPUT_TYPE_ID: (SubnodeInputNodePlugin, "subnode/input.svg"),
    SUBNODE_OUTPUT_TYPE_ID: (SubnodeOutputNodePlugin, "subnode/output.svg"),
    "dpf.result_file": (DpfResultFileNodePlugin, "dpf/database.svg"),
    "dpf.model": (DpfModelNodePlugin, "dpf/cube.svg"),
    "dpf.scoping.mesh": (DpfMeshScopingNodePlugin, "dpf/filter.svg"),
    "dpf.scoping.time": (DpfTimeScopingNodePlugin, "dpf/clock.svg"),
    "dpf.result_field": (DpfResultFieldNodePlugin, "dpf/query_stats.svg"),
    "dpf.field_ops": (DpfFieldOpsNodePlugin, "dpf/calculate.svg"),
    "dpf.mesh_extract": (DpfMeshExtractNodePlugin, "dpf/hub.svg"),
    "dpf.export": (DpfExportNodePlugin, "dpf/download.svg"),
    "dpf.viewer": (DpfViewerNodePlugin, "dpf/monitor.svg"),
}

_LEGACY_SYMBOLIC_ICON_NAMES = frozenset(
    {
        "account_tree",
        "alt_route",
        "article",
        "calculate",
        "call_split",
        "clock",
        "cloud_download",
        "cloud_upload",
        "code",
        "cube",
        "data_object",
        "database",
        "description",
        "download",
        "error_outline",
        "filter",
        "hub",
        "input",
        "mail",
        "monitor",
        "monitor_heart",
        "output",
        "play_arrow",
        "query_stats",
        "save",
        "stop",
        "table_view",
        "terminal",
    }
)

_EXPECTED_PACKAGE_DATA_PATTERNS = {
    "assets/node_title_icons/**/*.svg",
    "assets/node_title_icons/**/*.png",
    "assets/node_title_icons/**/*.jpg",
    "assets/node_title_icons/**/*.jpeg",
}


class NodeTitleIconAssetTests(unittest.TestCase):
    def test_title_icon_assets_exist_for_all_migrated_non_passive_builtins(self) -> None:
        self.assertEqual(NODE_TITLE_ICON_ASSET_ROOT, PROJECT_ROOT / "ea_node_editor" / "assets" / "node_title_icons")

        observed_specs = {}
        for expected_type_id, (factory, expected_icon_path) in _MIGRATED_TITLE_ICON_SPECS.items():
            spec = factory().spec()
            observed_specs[spec.type_id] = spec
            self.assertEqual(spec.type_id, expected_type_id)
            self.assertEqual(spec.icon, expected_icon_path)
            self.assertIn(spec.runtime_behavior, {"active", "compile_only"})

            asset_path = NODE_TITLE_ICON_ASSET_ROOT / expected_icon_path
            self.assertTrue(asset_path.is_file(), msg=f"missing asset for {spec.type_id}: {asset_path}")
            self.assertIn(asset_path.suffix.casefold(), SUPPORTED_NODE_TITLE_ICON_SUFFIXES)
            self.assertEqual(resolve_node_title_icon_source(spec.icon), asset_path.resolve().as_uri())
            self.assertEqual(title_icon_source_for_node_payload(spec), asset_path.resolve().as_uri())

        self.assertEqual(set(observed_specs), set(_MIGRATED_TITLE_ICON_SPECS))

    def test_title_icon_asset_inventory_matches_expected_relative_paths(self) -> None:
        self.assertTrue(NODE_TITLE_ICON_ASSET_ROOT.is_dir())
        inventory = {
            asset_path.relative_to(NODE_TITLE_ICON_ASSET_ROOT).as_posix()
            for asset_path in NODE_TITLE_ICON_ASSET_ROOT.rglob("*")
            if asset_path.is_file()
        }

        self.assertEqual(inventory, {expected_path for _factory, expected_path in _MIGRATED_TITLE_ICON_SPECS.values()})
        self.assertTrue(all(Path(relative_path).suffix.casefold() in SUPPORTED_NODE_TITLE_ICON_SUFFIXES for relative_path in inventory))

    def test_title_icon_symbolic_icon_names_remain_unrendered_without_local_asset_paths(self) -> None:
        for icon_name in _LEGACY_SYMBOLIC_ICON_NAMES:
            with self.subTest(icon_name=icon_name):
                self.assertEqual(resolve_node_title_icon_source(icon_name), "")

    def test_title_icon_packaging_metadata_includes_node_title_icon_assets(self) -> None:
        pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
        package_data = set(pyproject["tool"]["setuptools"]["package-data"]["ea_node_editor"])
        self.assertTrue(_EXPECTED_PACKAGE_DATA_PATTERNS.issubset(package_data))

        spec_text = SPEC_PATH.read_text(encoding="utf-8")
        for pattern in _EXPECTED_PACKAGE_DATA_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, spec_text)


if __name__ == "__main__":
    unittest.main()
