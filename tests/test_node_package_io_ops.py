from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ea_node_editor.nodes.types import NodeTypeSpec, PluginDescriptor, PluginProvenance
from ea_node_editor.ui.shell.controllers.workspace_io_ops import WorkspaceIOOps


class _SignalStub:
    def __init__(self) -> None:
        self.calls = 0

    def emit(self) -> None:
        self.calls += 1


class _RegistryStub:
    def __init__(self) -> None:
        self._descriptors: list[PluginDescriptor] = []
        self._specs: dict[str, object] = {}

    def add_available(self, type_id: str) -> None:
        self._specs[type_id] = SimpleNamespace(type_id=type_id)

    def add_descriptor(self, descriptor: PluginDescriptor) -> None:
        self._descriptors.append(descriptor)
        self._specs[descriptor.spec.type_id] = descriptor.spec

    def all_descriptors(self) -> list[PluginDescriptor]:
        return list(self._descriptors)

    def spec_or_none(self, type_id: str) -> object | None:
        return self._specs.get(type_id)


class _ControllerStub:
    def __init__(self) -> None:
        self._definitions: list[dict[str, object]] = []

    def _custom_workflow_definitions(self) -> list[dict[str, object]]:
        return list(self._definitions)

    def _set_custom_workflow_definitions(self, definitions: list[dict[str, object]]) -> None:
        self._definitions = list(definitions)

    def _prompt_custom_workflow_export_definition(
        self,
        definitions: list[dict[str, object]],
    ) -> dict[str, object] | None:
        if not definitions:
            return None
        return definitions[0]


class _HostStub:
    def __init__(self) -> None:
        self.registry = _RegistryStub()
        self.node_library_changed = _SignalStub()
        self.project_meta_changed = _SignalStub()


class WorkspaceIONodePackageTests(unittest.TestCase):
    def test_import_node_package_reports_success_when_declared_nodes_become_available(self) -> None:
        host = _HostStub()
        ops = WorkspaceIOOps(host, _ControllerStub())  # type: ignore[arg-type]
        manifest = SimpleNamespace(name="packet_pkg", version="2.0.0", nodes=["packet.alpha"])

        def _discover(registry: _RegistryStub) -> list[str]:
            registry.add_available("packet.alpha")
            return ["packet.alpha"]

        with (
            patch(
                "PyQt6.QtWidgets.QFileDialog.getOpenFileName",
                return_value=("C:/tmp/packet_pkg.eanp", "Node Package (*.eanp)"),
            ),
            patch("ea_node_editor.nodes.package_manager.import_package", return_value=manifest),
            patch(
                "ea_node_editor.nodes.plugin_loader.discover_and_load_plugins",
                side_effect=_discover,
            ),
            patch("PyQt6.QtWidgets.QMessageBox.information") as info_mock,
            patch("PyQt6.QtWidgets.QMessageBox.warning") as warning_mock,
        ):
            ops.import_node_package()

        self.assertEqual(host.node_library_changed.calls, 1)
        self.assertEqual(info_mock.call_count, 1)
        self.assertEqual(warning_mock.call_count, 0)
        self.assertIn("with 1 node(s)", info_mock.call_args.args[2])
        self.assertIn("now available in the Node Library", info_mock.call_args.args[2])

    def test_import_node_package_accepts_already_available_declared_nodes(self) -> None:
        host = _HostStub()
        host.registry.add_available("packet.alpha")
        ops = WorkspaceIOOps(host, _ControllerStub())  # type: ignore[arg-type]
        manifest = SimpleNamespace(name="packet_pkg", version="2.1.0", nodes=["packet.alpha"])

        with (
            patch(
                "PyQt6.QtWidgets.QFileDialog.getOpenFileName",
                return_value=("C:/tmp/packet_pkg.eanp", "Node Package (*.eanp)"),
            ),
            patch("ea_node_editor.nodes.package_manager.import_package", return_value=manifest),
            patch("ea_node_editor.nodes.plugin_loader.discover_and_load_plugins", return_value=[]),
            patch("PyQt6.QtWidgets.QMessageBox.information") as info_mock,
            patch("PyQt6.QtWidgets.QMessageBox.warning") as warning_mock,
        ):
            ops.import_node_package()

        self.assertEqual(host.node_library_changed.calls, 1)
        self.assertEqual(info_mock.call_count, 1)
        self.assertEqual(warning_mock.call_count, 0)
        self.assertIn("already available", info_mock.call_args.args[2])

    def test_import_node_package_warns_when_declared_nodes_remain_unavailable(self) -> None:
        host = _HostStub()
        ops = WorkspaceIOOps(host, _ControllerStub())  # type: ignore[arg-type]
        manifest = SimpleNamespace(name="packet_pkg", version="2.0.0", nodes=["packet.alpha"])

        with (
            patch(
                "PyQt6.QtWidgets.QFileDialog.getOpenFileName",
                return_value=("C:/tmp/packet_pkg.eanp", "Node Package (*.eanp)"),
            ),
            patch("ea_node_editor.nodes.package_manager.import_package", return_value=manifest),
            patch("ea_node_editor.nodes.plugin_loader.discover_and_load_plugins", return_value=[]),
            patch("PyQt6.QtWidgets.QMessageBox.information") as info_mock,
            patch("PyQt6.QtWidgets.QMessageBox.warning") as warning_mock,
        ):
            ops.import_node_package()

        self.assertEqual(host.node_library_changed.calls, 0)
        self.assertEqual(info_mock.call_count, 0)
        self.assertEqual(warning_mock.call_count, 1)
        self.assertEqual(warning_mock.call_args.args[1], "Import Incomplete")
        self.assertIn("not currently available", warning_mock.call_args.args[2])

    def test_import_node_package_allows_approved_no_node_outcome(self) -> None:
        host = _HostStub()
        ops = WorkspaceIOOps(host, _ControllerStub())  # type: ignore[arg-type]
        manifest = SimpleNamespace(name="packet_pkg", version="2.0.0", nodes=[])

        with (
            patch(
                "PyQt6.QtWidgets.QFileDialog.getOpenFileName",
                return_value=("C:/tmp/packet_pkg.eanp", "Node Package (*.eanp)"),
            ),
            patch("ea_node_editor.nodes.package_manager.import_package", return_value=manifest),
            patch("ea_node_editor.nodes.plugin_loader.discover_and_load_plugins", return_value=[]),
            patch("PyQt6.QtWidgets.QMessageBox.information") as info_mock,
            patch("PyQt6.QtWidgets.QMessageBox.warning") as warning_mock,
        ):
            ops.import_node_package()

        self.assertEqual(host.node_library_changed.calls, 0)
        self.assertEqual(info_mock.call_count, 1)
        self.assertEqual(warning_mock.call_count, 0)
        self.assertIn("declares no node types", info_mock.call_args.args[2])

    def test_export_node_package_passes_explicit_package_sources(self) -> None:
        host = _HostStub()
        ops = WorkspaceIOOps(host, _ControllerStub())  # type: ignore[arg-type]

        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_root = Path(temp_dir) / "plugins"
            package_dir = plugins_root / "packet_pkg"
            package_dir.mkdir(parents=True, exist_ok=True)
            (package_dir / "helper.py").write_text('DISPLAY_NAME = "Packet"\n', encoding="utf-8")
            (package_dir / "package_plugin.py").write_text("VALUE = 'plugin'\n", encoding="utf-8")
            (package_dir / "node_package.json").write_text(
                json.dumps(
                    {
                        "name": "packet_pkg",
                        "version": "3.2.1",
                        "author": "Packet Tests",
                        "description": "Exportable package",
                        "nodes": ["packet.alpha"],
                        "dependencies": ["dep.alpha"],
                    }
                ),
                encoding="utf-8",
            )
            host.registry.add_descriptor(
                PluginDescriptor(
                    spec=NodeTypeSpec(
                        type_id="packet.alpha",
                        display_name="Packet",
                        category="Packet Tests",
                        icon="packet",
                        ports=(),
                        properties=(),
                    ),
                    factory=type("PacketPlugin", (), {}),
                    provenance=PluginProvenance(
                        kind="package",
                        source_path=(package_dir / "package_plugin.py").resolve(),
                        package_root=package_dir.resolve(),
                        package_name="packet_pkg",
                    ),
                )
            )

            with (
                patch(
                    "ea_node_editor.ui.shell.controllers.workspace_io_ops.plugins_dir",
                    return_value=plugins_root,
                ),
                patch(
                    "PyQt6.QtWidgets.QInputDialog.getText",
                    return_value=("packet_pkg_export", True),
                ),
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(Path(temp_dir) / "exports" / "packet_pkg_export.eanp"), "Node Package (*.eanp)"),
                ),
                patch(
                    "ea_node_editor.nodes.package_manager.export_package",
                    return_value=Path(temp_dir) / "exports" / "packet_pkg_export.eanp",
                ) as export_mock,
                patch("PyQt6.QtWidgets.QMessageBox.information") as info_mock,
                patch("PyQt6.QtWidgets.QMessageBox.warning") as warning_mock,
            ):
                ops.export_node_package()

        self.assertEqual(export_mock.call_count, 1)
        export_sources, manifest, output_path = export_mock.call_args.args
        export_descriptors = export_mock.call_args.kwargs["descriptors"]
        self.assertEqual(
            [source.archive_name for source in export_sources],
            ["helper.py", "package_plugin.py"],
        )
        self.assertEqual([descriptor.spec.type_id for descriptor in export_descriptors], ["packet.alpha"])
        self.assertEqual(export_descriptors[0].provenance.kind, "package")
        self.assertEqual(manifest.name, "packet_pkg_export")
        self.assertEqual(manifest.version, "3.2.1")
        self.assertEqual(manifest.author, "Packet Tests")
        self.assertEqual(manifest.description, "Exportable package")
        self.assertEqual(manifest.dependencies, ["dep.alpha"])
        self.assertEqual(manifest.nodes, ["packet.alpha"])
        self.assertEqual(output_path, Path(temp_dir) / "exports" / "packet_pkg_export.eanp")
        self.assertEqual(info_mock.call_count, 1)
        self.assertEqual(warning_mock.call_count, 0)

    def test_custom_workflow_and_node_package_import_filters_remain_separate(self) -> None:
        host = _HostStub()
        ops = WorkspaceIOOps(host, _ControllerStub())  # type: ignore[arg-type]
        dialog_calls: list[tuple[str, str]] = []

        def _fake_get_open_file_name(
            _parent: object,
            title: str,
            _directory: str,
            file_filter: str,
        ) -> tuple[str, str]:
            dialog_calls.append((title, file_filter))
            return ("", file_filter)

        with patch("PyQt6.QtWidgets.QFileDialog.getOpenFileName", side_effect=_fake_get_open_file_name):
            ops.import_custom_workflow()
            ops.import_node_package()

        self.assertEqual(
            dialog_calls,
            [
                ("Import Custom Workflow", "Custom Workflow (*.eawf)"),
                ("Import Node Package", "Node Package (*.eanp)"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
