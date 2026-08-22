from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.excalidraw import (
    EXCALIDRAW_BOARD_TYPE_ID,
    EXCALIDRAW_PREVIEW_REF_PROPERTY,
    EXCALIDRAW_STATE_PROPERTY,
)
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.artifact_refs import (
    format_managed_artifact_ref,
    format_staged_artifact_ref,
)
from ea_node_editor.persistence.artifact_store import format_workspace_artifact_folder
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.runtime_contracts import (
    GRAPH_DATA_TYPE_ID,
    DataTypeFamilySpec,
    DataTypeSpec,
    RuntimeArtifactRef,
)
from ea_node_editor.ui.dialogs.project_save_as_dialog import ProjectSaveAsDialog
from ea_node_editor.ui.shell.controllers.project_session_controller import (
    ProjectSessionController,
)
from ea_node_editor.ui.shell.state import ShellProjectSessionState

_TYPED_ARTIFACT_NODE_TYPE_ID = "tests.typed_artifact_save"
_TYPED_ARTIFACT_DATA_TYPE_ID = "Tests.SaveFlow.Artifact"
_OTHER_TYPED_ARTIFACT_DATA_TYPE_ID = "Tests.SaveFlow.OtherArtifact"


def _typed_artifact_registry() -> NodeRegistry:
    registry = NodeRegistry()
    family = DataTypeFamilySpec(
        "tests.save_flow",
        "Save Flow",
        "data.test",
        "test",
    )
    registry.data_types.register_many(
        families=(family,),
        types=(
            DataTypeSpec(
                _TYPED_ARTIFACT_DATA_TYPE_ID,
                "Typed Artifact",
                family.family_id,
                lambda value: isinstance(value, RuntimeArtifactRef),
                parents=(GRAPH_DATA_TYPE_ID,),
                carriers=frozenset({"artifact"}),
                persistence="saved_artifact",
            ),
            DataTypeSpec(
                _OTHER_TYPED_ARTIFACT_DATA_TYPE_ID,
                "Other Typed Artifact",
                family.family_id,
                lambda value: isinstance(value, RuntimeArtifactRef),
                parents=(GRAPH_DATA_TYPE_ID,),
                carriers=frozenset({"artifact"}),
                persistence="saved_artifact",
            ),
        ),
        owner_id="tests.save_flow",
    )
    spec = NodeTypeSpec(
        _TYPED_ARTIFACT_NODE_TYPE_ID,
        "Typed Artifact Save",
        ("Tests",),
        "",
        (PortSpec("result", "out", "data", GRAPH_DATA_TYPE_ID),),
        (
            PropertySpec(
                "artifact",
                "path",
                "",
                "Artifact",
                persistence_data_type_id=_TYPED_ARTIFACT_DATA_TYPE_ID,
            ),
        ),
    )
    registry.register_descriptor(spec, lambda: None)  # type: ignore[arg-type]
    return registry


def _typed_artifact_document(runtime_ref: RuntimeArtifactRef) -> dict[str, object]:
    return {
        "schema_version": 5,
        "project_id": "proj_typed_artifact_save",
        "name": "Typed Artifact Save",
        "active_workspace_id": "ws_1",
        "workspace_order": ["ws_1"],
        "workspaces": [
            {
                "workspace_id": "ws_1",
                "name": "Main",
                "dirty": True,
                "active_view_id": "view_1",
                "views": [
                    {
                        "view_id": "view_1",
                        "name": "Main",
                        "zoom": 1.0,
                        "pan_x": 0.0,
                        "pan_y": 0.0,
                        "scope_path": [],
                    },
                ],
                "nodes": [
                    {
                        "node_id": "node_typed_artifact",
                        "type_id": _TYPED_ARTIFACT_NODE_TYPE_ID,
                        "title": "Typed Artifact",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {"artifact": runtime_ref},
                        "exposed_ports": {},
                    },
                ],
                "edges": [],
            },
        ],
        "metadata": {
            "artifact_store": {
                "artifacts": {},
                "staged": {
                    runtime_ref.artifact_id: {
                        "relative_path": (
                            "nodes/Typed Artifact [33333333]/tmp/in/"
                            f"{runtime_ref.artifact_id}.bin"
                        ),
                        "runtime_artifact": runtime_ref.to_descriptor(),
                    },
                },
            },
        },
    }


def _invalid_typed_literal_artifact_document(
    runtime_ref: RuntimeArtifactRef,
    *,
    case: str,
) -> dict[str, object]:
    document = _typed_artifact_document(runtime_ref)
    document["workspaces"][0]["nodes"][0]["properties"]["artifact"] = runtime_ref.ref
    staged = document["metadata"]["artifact_store"]["staged"]
    if case == "unowned":
        document["metadata"]["artifact_store"]["staged"] = {}
    elif case == "mismatched":
        staged[runtime_ref.artifact_id]["runtime_artifact"]["data_type_id"] = (
            _OTHER_TYPED_ARTIFACT_DATA_TYPE_ID
        )
    elif case == "malformed":
        staged[runtime_ref.artifact_id]["runtime_artifact"]["schema_version"] = True
    else:
        raise ValueError(f"unsupported invalid literal case {case!r}")
    return document


class _SignalStub:
    def __init__(self) -> None:
        self.emit_count = 0

    def emit(self) -> None:
        self.emit_count += 1


class _ScriptEditorStub:
    def __init__(self) -> None:
        self.visible = False
        self.floating = False
        self.panel_width = 0.0


class _WorkspaceLibraryControllerStub:
    def __init__(self) -> None:
        self.save_active_view_state_calls = 0
        self.refresh_workspace_tabs_calls = 0

    def save_active_view_state(self) -> None:
        self.save_active_view_state_calls += 1

    def refresh_workspace_tabs(self) -> None:
        self.refresh_workspace_tabs_calls += 1


class _SerializerStub:
    def __init__(self, persistent_document: dict) -> None:
        self._persistent_document = copy.deepcopy(persistent_document)
        self.saved_documents: list[tuple[str, dict]] = []

    def to_persistent_document(self, project) -> dict:  # noqa: ANN001
        document = copy.deepcopy(self._persistent_document)
        document["metadata"] = copy.deepcopy(project.metadata)
        return document

    def save_document(self, path: str, document: dict) -> None:
        target = Path(path).with_suffix(".cxproj")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = copy.deepcopy(document)
        target.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )
        self.saved_documents.append((str(target), payload))

    def to_document(self, project) -> dict:  # noqa: ANN001
        document = copy.deepcopy(self._persistent_document)
        document["metadata"] = copy.deepcopy(project.metadata)
        return document


class _SessionStoreStub:
    def __init__(self) -> None:
        self.discard_calls = 0
        self.persist_calls: list[dict] = []

    def discard_autosave_snapshot(self) -> None:
        self.discard_calls += 1

    def autosave_if_changed(self, **kwargs) -> str:  # noqa: ANN003
        return str(kwargs.get("last_fingerprint") or "stub-autosave-fingerprint")

    def persist_session(self, **kwargs) -> None:  # noqa: ANN003
        self.persist_calls.append(copy.deepcopy(kwargs))


class _SceneStub:
    @staticmethod
    def selected_node_id() -> str:
        return ""


class _ProjectHostStub:
    def __init__(self, *, project_path: str, persistent_document: dict) -> None:
        self.project_session_state = ShellProjectSessionState()
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.model.project.project_id = str(
            persistent_document.get("project_id", "proj_save_as")
        )
        self.model.project.name = str(persistent_document.get("name", "Save As Demo"))
        workspace = self.model.active_workspace
        workspace_docs = persistent_document.get("workspaces", [])
        if workspace_docs:
            workspace_doc = workspace_docs[0]
            workspace.name = str(workspace_doc.get("name", workspace.name))
            for node_doc in workspace_doc.get("nodes", []):
                self.model.add_node(
                    workspace.workspace_id,
                    str(node_doc.get("type_id", "")),
                    str(node_doc.get("title", "")),
                    float(node_doc.get("x", 0.0)),
                    float(node_doc.get("y", 0.0)),
                    properties=copy.deepcopy(node_doc.get("properties", {})),
                    exposed_ports=copy.deepcopy(node_doc.get("exposed_ports", {})),
                )
        self.model.project.metadata = copy.deepcopy(
            persistent_document.get("metadata", {})
        )
        for workspace in self.model.project.workspaces.values():
            workspace.dirty = True
        self.project_path = project_path
        self.session_store = _SessionStoreStub()
        self.serializer = _SerializerStub(persistent_document)
        self.workspace_library_controller = _WorkspaceLibraryControllerStub()
        self.workspace_navigation_controller = self.workspace_library_controller
        self.script_editor = _ScriptEditorStub()
        self.action_toggle_script_editor = object()
        self.scene = _SceneStub()
        self.project_meta_changed = _SignalStub()
        self.refresh_calls = 0

    def _refresh_recent_projects_menu(self) -> None:
        self.refresh_calls += 1


class _AcceptingSelfContainedSaveAsDialog:
    DialogCode = ProjectSaveAsDialog.DialogCode
    SELF_CONTAINED_COPY = ProjectSaveAsDialog.SELF_CONTAINED_COPY

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.args = args
        self.kwargs = kwargs

    def exec(self) -> int:
        return self.DialogCode.Accepted

    def selected_mode(self) -> str:
        return self.SELF_CONTAINED_COPY


class ProjectSaveAsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_defaults_to_self_contained_copy(self) -> None:
        dialog = ProjectSaveAsDialog(
            referenced_managed_count=2, referenced_staged_count=1
        )
        self.addCleanup(dialog.deleteLater)

        self.assertTrue(dialog.self_contained_copy_radio.isChecked())
        self.assertEqual(
            dialog.selected_mode(), ProjectSaveAsDialog.SELF_CONTAINED_COPY
        )
        self.assertIn(
            "2 referenced saved files", dialog.self_contained_copy_radio.text()
        )


class ProjectSaveAsFlowTests(unittest.TestCase):
    maxDiff = None

    @staticmethod
    def _workspace_relative(
        relative_path: str, *, workspace_id: str = "ws_1", workspace_name: str = "Main"
    ) -> str:
        workspace_folder = format_workspace_artifact_folder(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
        )
        return f"workspaces/{workspace_folder}/{relative_path}"

    @classmethod
    def _workspace_path(
        cls,
        sidecar_root: Path,
        relative_path: str,
        *,
        workspace_id: str = "ws_1",
        workspace_name: str = "Main",
    ) -> Path:
        return sidecar_root.joinpath(
            *Path(
                cls._workspace_relative(
                    relative_path,
                    workspace_id=workspace_id,
                    workspace_name=workspace_name,
                )
            ).parts
        )

    @staticmethod
    def _typed_host(
        *,
        project_path: Path,
        document: dict[str, object],
    ) -> tuple[_ProjectHostStub, ProjectSessionController]:
        host = _ProjectHostStub(
            project_path=str(project_path),
            persistent_document=document,
        )
        registry = _typed_artifact_registry()
        host.registry = registry
        host.serializer = JsonProjectSerializer(registry)
        return host, ProjectSessionController(host)  # type: ignore[arg-type]

    @staticmethod
    def _typed_staged_path(
        project_path: Path,
        runtime_ref: RuntimeArtifactRef,
    ) -> Path:
        return (
            project_path.with_name(f"{project_path.stem}.data")
            / "nodes"
            / "Typed Artifact [33333333]"
            / "tmp"
            / "in"
            / f"{runtime_ref.artifact_id}.bin"
        )


    def _build_persistent_document(self, *, external_path: str) -> dict:
        return {
            "schema_version": 1,
            "project_id": "proj_save_as",
            "name": "Save As Demo",
            "active_workspace_id": "ws_1",
            "workspace_order": ["ws_1"],
            "workspaces": [
                {
                    "workspace_id": "ws_1",
                    "name": "Main",
                    "dirty": True,
                    "active_view_id": "view_1",
                    "views": [
                        {
                            "view_id": "view_1",
                            "name": "Main",
                            "zoom": 1.0,
                            "pan_x": 0.0,
                            "pan_y": 0.0,
                            "scope_path": [],
                        }
                    ],
                    "nodes": [
                        {
                            "node_id": "node_managed",
                            "type_id": "passive.media.image_panel",
                            "title": "Managed",
                            "x": 0.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {
                                "source_path": format_managed_artifact_ref(
                                    "managed_image"
                                ),
                            },
                            "exposed_ports": {},
                        },
                        {
                            "node_id": "node_staged",
                            "type_id": "passive.media.image_panel",
                            "title": "Staged",
                            "x": 120.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {
                                "source_path": format_staged_artifact_ref(
                                    "pending_output"
                                ),
                            },
                            "exposed_ports": {},
                        },
                        {
                            "node_id": "node_external",
                            "type_id": "passive.media.image_panel",
                            "title": "External",
                            "x": 240.0,
                            "y": 0.0,
                            "collapsed": False,
                            "properties": {
                                "source_path": external_path,
                            },
                            "exposed_ports": {},
                        },
                    ],
                    "edges": [],
                }
            ],
            "metadata": {
                "artifact_store": {
                    "artifacts": {
                        "managed_image": {
                            "relative_path": "nodes/Image Panel - Managed [11111111]/in/media/diagram.png",
                        }
                    },
                    "staged": {
                        "pending_output": {
                            "relative_path": "nodes/Image Panel - Staged [22222222]/tmp/out/outputs/run.txt",
                            "slot": "process_run.stdout",
                        }
                    },
                }
            },
        }

    def test_save_promotes_typed_staged_carrier_and_rewrites_live_property(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_project = Path(temp_dir) / "source" / "typed_save.cxproj"
            runtime_ref = RuntimeArtifactRef.staged(
                "typed_output",
                data_type_id=_TYPED_ARTIFACT_DATA_TYPE_ID,
                schema_version=1,
                format="bin",
                size_bytes=13,
                sha256="a" * 64,
                provenance="save-flow",
            )
            staged_path = self._typed_staged_path(source_project, runtime_ref)
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_bytes(b"typed payload")
            host, controller = self._typed_host(
                project_path=source_project,
                document=_typed_artifact_document(runtime_ref),
            )

            with patch.object(
                controller._project_files_service,
                "prompt_project_files_action",
                return_value=True,
            ):
                controller.save_project()

            saved_doc = json.loads(source_project.read_text(encoding="utf-8"))
            saved_property = saved_doc["workspaces"][0]["nodes"][0]["properties"][
                "artifact"
            ]
            managed_ref = format_managed_artifact_ref(runtime_ref.artifact_id)
            self.assertEqual(saved_property, managed_ref)
            managed_entry = saved_doc["metadata"]["artifact_store"]["artifacts"][
                runtime_ref.artifact_id
            ]
            self.assertEqual(
                managed_entry["runtime_artifact"],
                runtime_ref.to_descriptor(),
            )
            managed_path = source_project.with_name(
                f"{source_project.stem}.data"
            ).joinpath(*managed_entry["relative_path"].split("/"))
            self.assertEqual(managed_path.read_bytes(), b"typed payload")
            live_node = next(iter(host.model.active_workspace.nodes.values()))
            self.assertEqual(live_node.properties["artifact"], managed_ref)
            self.assertEqual(
                host.model.project.metadata["artifact_store"]["artifacts"][
                    runtime_ref.artifact_id
                ]["runtime_artifact"],
                runtime_ref.to_descriptor(),
            )
            self.assertNotIn("temp://", json.dumps(saved_doc, sort_keys=True))

    def test_save_as_promotes_typed_staged_carrier_and_rewrites_live_property(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "typed_source.cxproj"
            target_project = root / "target" / "typed_copy.cxproj"
            runtime_ref = RuntimeArtifactRef.staged(
                "typed_output",
                data_type_id=_TYPED_ARTIFACT_DATA_TYPE_ID,
                schema_version=1,
                format="bin",
                size_bytes=13,
                sha256="b" * 64,
                provenance="save-as-flow",
            )
            staged_path = self._typed_staged_path(source_project, runtime_ref)
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_bytes(b"typed payload")
            host, controller = self._typed_host(
                project_path=source_project,
                document=_typed_artifact_document(runtime_ref),
            )

            with (
                patch.object(
                    controller._project_files_service,
                    "prompt_project_files_action",
                    return_value=True,
                ),
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(target_project), "COREX Project (*.cxproj)"),
                ),
                patch(
                    "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                    _AcceptingSelfContainedSaveAsDialog,
                ),
            ):
                controller.save_project_as()

            saved_doc = json.loads(target_project.read_text(encoding="utf-8"))
            managed_ref = format_managed_artifact_ref(runtime_ref.artifact_id)
            self.assertEqual(
                saved_doc["workspaces"][0]["nodes"][0]["properties"]["artifact"],
                managed_ref,
            )
            managed_entry = saved_doc["metadata"]["artifact_store"]["artifacts"][
                runtime_ref.artifact_id
            ]
            self.assertEqual(
                managed_entry["runtime_artifact"],
                runtime_ref.to_descriptor(),
            )
            managed_path = target_project.with_name(
                f"{target_project.stem}.data"
            ).joinpath(*managed_entry["relative_path"].split("/"))
            self.assertEqual(managed_path.read_bytes(), b"typed payload")
            live_node = next(iter(host.model.active_workspace.nodes.values()))
            self.assertEqual(live_node.properties["artifact"], managed_ref)
            self.assertEqual(host.project_path, str(target_project))
            self.assertNotIn("temp://", json.dumps(saved_doc, sort_keys=True))

    def test_save_rejects_invalid_typed_staging_metadata_before_promotion(
        self,
    ) -> None:
        cases = ("unowned", "mismatched", "invalid")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp_dir:
                source_project = Path(temp_dir) / "source" / f"typed_{case}.cxproj"
                runtime_ref = RuntimeArtifactRef.staged(
                    "typed_output",
                    data_type_id=_TYPED_ARTIFACT_DATA_TYPE_ID,
                    schema_version=1,
                    format="bin",
                    size_bytes=13,
                    sha256="c" * 64,
                    provenance="invalid-flow",
                )
                document = _typed_artifact_document(runtime_ref)
                staged_entry = document["metadata"]["artifact_store"]["staged"][
                    runtime_ref.artifact_id
                ]
                if case == "unowned":
                    document["metadata"]["artifact_store"]["staged"] = {}
                elif case == "mismatched":
                    staged_entry["runtime_artifact"]["sha256"] = "d" * 64
                else:
                    staged_entry["runtime_artifact"]["schema_version"] = True
                staged_path = self._typed_staged_path(source_project, runtime_ref)
                staged_path.parent.mkdir(parents=True, exist_ok=True)
                staged_path.write_bytes(b"typed payload")
                host, controller = self._typed_host(
                    project_path=source_project,
                    document=document,
                )
                artifact_metadata_before = copy.deepcopy(
                    host.model.project.metadata["artifact_store"]
                )
                live_node = next(iter(host.model.active_workspace.nodes.values()))

                with (
                    patch.object(
                        controller._project_files_service,
                        "prompt_project_files_action",
                        return_value=True,
                    ),
                    self.assertRaisesRegex(
                        ValueError,
                        "unowned staged artifact|descriptor is invalid",
                    ),
                ):
                    controller.save_project()

                self.assertFalse(source_project.exists())
                self.assertTrue(staged_path.exists())
                self.assertEqual(
                    host.model.project.metadata["artifact_store"],
                    artifact_metadata_before,
                )
                self.assertEqual(live_node.properties["artifact"], runtime_ref)

    def test_save_as_rejects_unowned_typed_staging_before_destination_mutation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "typed_source.cxproj"
            target_project = root / "target" / "typed_copy.cxproj"
            runtime_ref = RuntimeArtifactRef.staged(
                "typed_output",
                data_type_id=_TYPED_ARTIFACT_DATA_TYPE_ID,
                schema_version=1,
                format="bin",
                size_bytes=13,
                sha256="e" * 64,
                provenance="invalid-save-as",
            )
            document = _typed_artifact_document(runtime_ref)
            document["metadata"]["artifact_store"]["staged"] = {}
            staged_path = self._typed_staged_path(source_project, runtime_ref)
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_bytes(b"typed payload")
            host, controller = self._typed_host(
                project_path=source_project,
                document=document,
            )
            artifact_metadata_before = copy.deepcopy(
                host.model.project.metadata["artifact_store"]
            )
            live_node = next(iter(host.model.active_workspace.nodes.values()))

            with (
                patch.object(
                    controller._project_files_service,
                    "prompt_project_files_action",
                    return_value=True,
                ),
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(target_project), "COREX Project (*.cxproj)"),
                ),
                self.assertRaisesRegex(ValueError, "unowned staged artifact"),
            ):
                controller.save_project_as()

            self.assertFalse(target_project.exists())
            self.assertTrue(staged_path.exists())
            self.assertEqual(
                host.model.project.metadata["artifact_store"],
                artifact_metadata_before,
            )
            self.assertEqual(live_node.properties["artifact"], runtime_ref)

    def test_save_rejects_invalid_typed_literal_staging_before_promotion(
        self,
    ) -> None:
        for case in ("unowned", "mismatched", "malformed"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp_dir:
                source_project = Path(temp_dir) / "source" / f"literal_{case}.cxproj"
                source_project.parent.mkdir(parents=True, exist_ok=True)
                source_project.write_bytes(b"original project")
                runtime_ref = RuntimeArtifactRef.staged(
                    "typed_literal",
                    data_type_id=_TYPED_ARTIFACT_DATA_TYPE_ID,
                    schema_version=1,
                    format="bin",
                    size_bytes=13,
                    sha256="6" * 64,
                    provenance="literal-save",
                )
                document = _invalid_typed_literal_artifact_document(
                    runtime_ref,
                    case=case,
                )
                staged_path = self._typed_staged_path(source_project, runtime_ref)
                staged_path.parent.mkdir(parents=True, exist_ok=True)
                staged_path.write_bytes(b"literal payload")
                host, controller = self._typed_host(
                    project_path=source_project,
                    document=document,
                )
                artifact_metadata_before = copy.deepcopy(
                    host.model.project.metadata["artifact_store"]
                )
                live_node = next(iter(host.model.active_workspace.nodes.values()))
                workspaces_root = (
                    source_project.with_name(f"{source_project.stem}.data")
                    / "workspaces"
                )

                with (
                    patch.object(
                        controller._project_files_service,
                        "prompt_project_files_action",
                        return_value=True,
                    ),
                    self.assertRaisesRegex(
                        ValueError,
                        "unowned staged artifact|descriptor is invalid",
                    ),
                ):
                    controller.save_project()

                self.assertEqual(source_project.read_bytes(), b"original project")
                self.assertEqual(staged_path.read_bytes(), b"literal payload")
                self.assertFalse(workspaces_root.exists())
                self.assertEqual(
                    host.model.project.metadata["artifact_store"],
                    artifact_metadata_before,
                )
                self.assertEqual(live_node.properties["artifact"], runtime_ref.ref)
                self.assertEqual(host.project_path, str(source_project))

    def test_save_as_rejects_invalid_typed_literal_before_destination_mutation(
        self,
    ) -> None:
        for case in ("unowned", "mismatched", "malformed"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                source_project = root / "source" / f"literal_{case}.cxproj"
                target_project = root / "target" / f"literal_{case}.cxproj"
                source_project.parent.mkdir(parents=True, exist_ok=True)
                source_project.write_bytes(b"source project")
                target_project.parent.mkdir(parents=True, exist_ok=True)
                target_project.write_bytes(b"target project")
                target_sentinel = (
                    target_project.with_name(f"{target_project.stem}.data")
                    / "workspaces"
                    / "existing"
                    / "sentinel.bin"
                )
                target_sentinel.parent.mkdir(parents=True, exist_ok=True)
                target_sentinel.write_bytes(b"target sentinel")
                runtime_ref = RuntimeArtifactRef.staged(
                    "typed_literal",
                    data_type_id=_TYPED_ARTIFACT_DATA_TYPE_ID,
                    schema_version=1,
                    format="bin",
                    size_bytes=13,
                    sha256="7" * 64,
                    provenance="literal-save-as",
                )
                document = _invalid_typed_literal_artifact_document(
                    runtime_ref,
                    case=case,
                )
                staged_path = self._typed_staged_path(source_project, runtime_ref)
                staged_path.parent.mkdir(parents=True, exist_ok=True)
                staged_path.write_bytes(b"literal payload")
                host, controller = self._typed_host(
                    project_path=source_project,
                    document=document,
                )
                artifact_metadata_before = copy.deepcopy(
                    host.model.project.metadata["artifact_store"]
                )
                live_node = next(iter(host.model.active_workspace.nodes.values()))

                with (
                    patch.object(
                        controller._project_files_service,
                        "prompt_project_files_action",
                        return_value=True,
                    ),
                    patch(
                        "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                        return_value=(
                            str(target_project),
                            "COREX Project (*.cxproj)",
                        ),
                    ),
                    self.assertRaisesRegex(
                        ValueError,
                        "unowned staged artifact|descriptor is invalid",
                    ),
                ):
                    controller.save_project_as()

                self.assertEqual(source_project.read_bytes(), b"source project")
                self.assertEqual(staged_path.read_bytes(), b"literal payload")
                self.assertEqual(target_project.read_bytes(), b"target project")
                self.assertEqual(target_sentinel.read_bytes(), b"target sentinel")
                self.assertEqual(
                    host.model.project.metadata["artifact_store"],
                    artifact_metadata_before,
                )
                self.assertEqual(live_node.properties["artifact"], runtime_ref.ref)
                self.assertEqual(host.project_path, str(source_project))

    def test_save_promotes_and_rewrites_excalidraw_staged_refs_in_nested_payloads(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "source_project.cxproj"
            source_layout = source_project.with_name("source_project.data")
            staged_image_path = (
                source_layout
                / "nodes"
                / "Excalidraw - Board [33333333]"
                / "tmp"
                / "in"
                / "excalidraw"
                / "image.png"
            )
            staged_preview_path = (
                source_layout
                / "nodes"
                / "Excalidraw - Board [33333333]"
                / "tmp"
                / "out"
                / "excalidraw"
                / "preview.png"
            )
            scratch_path = (
                source_layout
                / "nodes"
                / "Excalidraw - Board [33333333]"
                / "tmp"
                / "out"
                / "excalidraw"
                / "scratch.png"
            )
            staged_image_path.parent.mkdir(parents=True, exist_ok=True)
            staged_image_path.write_text("image payload", encoding="utf-8")
            staged_preview_path.parent.mkdir(parents=True, exist_ok=True)
            staged_preview_path.write_text("preview payload", encoding="utf-8")
            scratch_path.write_text("scratch payload", encoding="utf-8")
            image_ref = format_staged_artifact_ref("pending_excalidraw_image")
            preview_ref = format_staged_artifact_ref("pending_excalidraw_preview")
            persistent_document = {
                "schema_version": 1,
                "project_id": "proj_excalidraw_save",
                "name": "Excalidraw Save",
                "active_workspace_id": "ws_1",
                "workspace_order": ["ws_1"],
                "workspaces": [
                    {
                        "workspace_id": "ws_1",
                        "name": "Main",
                        "dirty": True,
                        "active_view_id": "view_1",
                        "views": [
                            {
                                "view_id": "view_1",
                                "name": "Main",
                                "zoom": 1.0,
                                "pan_x": 0.0,
                                "pan_y": 0.0,
                                "scope_path": [],
                            }
                        ],
                        "nodes": [
                            {
                                "node_id": "node_excalidraw",
                                "type_id": EXCALIDRAW_BOARD_TYPE_ID,
                                "title": "Board",
                                "x": 0.0,
                                "y": 0.0,
                                "collapsed": False,
                                "properties": {
                                    EXCALIDRAW_STATE_PROPERTY: {
                                        "type": "excalidraw",
                                        "version": 2,
                                        "elements": [
                                            {
                                                "id": "image-element",
                                                "type": "image",
                                                "fileId": "file-pending",
                                            }
                                        ],
                                        "files": [
                                            {
                                                "id": "file-pending",
                                                "mimeType": "image/png",
                                                "artifact_ref": image_ref,
                                            }
                                        ],
                                        "appState": {"viewBackgroundColor": "#ffffff"},
                                    },
                                    EXCALIDRAW_PREVIEW_REF_PROPERTY: {
                                        "artifact_ref": preview_ref,
                                        "mime_type": "image/png",
                                    },
                                },
                                "exposed_ports": {},
                            }
                        ],
                        "edges": [],
                    }
                ],
                "metadata": {
                    "artifact_store": {
                        "artifacts": {},
                        "staged": {
                            "pending_excalidraw_image": {
                                "relative_path": "nodes/Excalidraw - Board [33333333]/tmp/in/excalidraw/image.png",
                                "slot": "excalidraw.node_excalidraw.image",
                            },
                            "pending_excalidraw_preview": {
                                "relative_path": "nodes/Excalidraw - Board [33333333]/tmp/out/excalidraw/preview.png",
                                "slot": "excalidraw.node_excalidraw.preview",
                            },
                            "unused_excalidraw_scratch": {
                                "relative_path": "nodes/Excalidraw - Board [33333333]/tmp/out/excalidraw/scratch.png",
                                "slot": "excalidraw.node_excalidraw.scratch",
                            },
                        },
                    }
                },
            }

            host = _ProjectHostStub(
                project_path=str(source_project),
                persistent_document=persistent_document,
            )
            host.script_editor.panel_width = 640.0
            controller = ProjectSessionController(host)  # type: ignore[arg-type]

            with patch.object(
                controller._project_files_service,
                "prompt_project_files_action",
                return_value=True,
            ):
                controller.save_project()

            saved_doc = json.loads(source_project.read_text(encoding="utf-8"))
            self.assertEqual(
                saved_doc["metadata"]["ui"]["script_editor"]["width"], 640.0
            )
            saved_properties = saved_doc["workspaces"][0]["nodes"][0]["properties"]
            managed_image_path = self._workspace_path(
                source_layout,
                "nodes/Excalidraw - Board [33333333]/in/excalidraw/image.png",
                workspace_id=host.model.active_workspace.workspace_id,
            )
            managed_preview_path = self._workspace_path(
                source_layout,
                "nodes/Excalidraw - Board [33333333]/out/excalidraw/preview.png",
                workspace_id=host.model.active_workspace.workspace_id,
            )

            self.assertEqual(
                saved_properties[EXCALIDRAW_STATE_PROPERTY]["files"][0]["artifact_ref"],
                format_managed_artifact_ref("pending_excalidraw_image"),
            )
            self.assertEqual(
                saved_properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]["artifact_ref"],
                format_managed_artifact_ref("pending_excalidraw_preview"),
            )
            artifact_store = saved_doc["metadata"]["artifact_store"]
            self.assertEqual(artifact_store["staged"], {})
            self.assertEqual(
                artifact_store["artifacts"]["pending_excalidraw_image"][
                    "relative_path"
                ],
                self._workspace_relative(
                    "nodes/Excalidraw - Board [33333333]/in/excalidraw/image.png",
                    workspace_id=host.model.active_workspace.workspace_id,
                ),
            )
            self.assertEqual(
                artifact_store["artifacts"]["pending_excalidraw_preview"][
                    "relative_path"
                ],
                self._workspace_relative(
                    "nodes/Excalidraw - Board [33333333]/out/excalidraw/preview.png",
                    workspace_id=host.model.active_workspace.workspace_id,
                ),
            )
            self.assertEqual(
                artifact_store["artifacts"]["pending_excalidraw_image"]["slot"],
                "excalidraw.node_excalidraw.image",
            )
            self.assertEqual(
                artifact_store["artifacts"]["pending_excalidraw_image"][
                    "node_workspace_name"
                ],
                "Main",
            )
            self.assertEqual(
                managed_image_path.read_text(encoding="utf-8"), "image payload"
            )
            self.assertEqual(
                managed_preview_path.read_text(encoding="utf-8"), "preview payload"
            )
            self.assertFalse(staged_image_path.exists())
            self.assertFalse(staged_preview_path.exists())
            self.assertFalse(scratch_path.exists())
            serialized_doc = json.dumps(saved_doc, sort_keys=True)
            self.assertNotIn("temp://", serialized_doc)
            self.assertNotIn("data:image", serialized_doc)
            self.assertNotIn("base64", serialized_doc)

    def test_save_as_copies_referenced_saved_files_and_promotes_temp_by_default(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "source_project.cxproj"
            source_managed_path = (
                source_project.with_name("source_project.data")
                / "nodes"
                / "Image Panel - Managed [11111111]"
                / "in"
                / "media"
                / "diagram.png"
            )
            source_managed_path.parent.mkdir(parents=True, exist_ok=True)
            source_managed_path.write_text("managed payload", encoding="utf-8")
            source_staging_path = (
                source_project.with_name("source_project.data")
                / "nodes"
                / "Image Panel - Staged [22222222]"
                / "tmp"
                / "out"
                / "outputs"
                / "run.txt"
            )
            source_staging_path.parent.mkdir(parents=True, exist_ok=True)
            source_staging_path.write_text("staged payload", encoding="utf-8")
            external_path = str((root / "external" / "linked.png").resolve())
            Path(external_path).parent.mkdir(parents=True, exist_ok=True)
            Path(external_path).write_text("external payload", encoding="utf-8")
            persistent_document = self._build_persistent_document(
                external_path=external_path
            )

            target_project = root / "copies" / "clone_project.cxproj"
            stale_managed_path = (
                target_project.with_name("clone_project.data")
                / "nodes"
                / "Old Node [99999999]"
                / "out"
                / "stale.txt"
            )
            stale_managed_path.parent.mkdir(parents=True, exist_ok=True)
            stale_managed_path.write_text("stale", encoding="utf-8")
            stale_staging_path = (
                target_project.with_name("clone_project.data")
                / "nodes"
                / "Old Node [99999999]"
                / "tmp"
                / "out"
                / "outputs"
                / "old.txt"
            )
            stale_staging_path.parent.mkdir(parents=True, exist_ok=True)
            stale_staging_path.write_text("stale staging", encoding="utf-8")

            host = _ProjectHostStub(
                project_path=str(source_project),
                persistent_document=persistent_document,
            )
            controller = ProjectSessionController(host)  # type: ignore[arg-type]

            with (
                patch.object(
                    controller._project_files_service,
                    "prompt_project_files_action",
                    return_value=True,
                ),
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(target_project), "COREX Project (*.cxproj)"),
                ),
                patch(
                    "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                    _AcceptingSelfContainedSaveAsDialog,
                ),
            ):
                controller.save_project_as()

            saved_path = target_project.with_suffix(".cxproj")
            saved_doc = json.loads(saved_path.read_text(encoding="utf-8"))
            target_layout = saved_path.with_name("clone_project.data")
            copied_managed_path = self._workspace_path(
                target_layout,
                "nodes/Image Panel - Managed [11111111]/in/media/diagram.png",
                workspace_id=host.model.active_workspace.workspace_id,
            )
            copied_output_path = self._workspace_path(
                target_layout,
                "nodes/Image Panel - Staged [22222222]/out/outputs/run.txt",
                workspace_id=host.model.active_workspace.workspace_id,
            )
            copied_temp_path = self._workspace_path(
                target_layout,
                "nodes/Image Panel - Staged [22222222]/tmp/out/outputs/run.txt",
                workspace_id=host.model.active_workspace.workspace_id,
            )

            self.assertEqual(host.project_path, str(saved_path))
            self.assertEqual(
                host.project_session_state.recent_project_paths, [str(saved_path)]
            )
            self.assertFalse(next(iter(host.model.project.workspaces.values())).dirty)
            self.assertEqual(host.project_meta_changed.emit_count, 1)
            self.assertEqual(
                host.workspace_library_controller.refresh_workspace_tabs_calls, 1
            )
            self.assertEqual(host.session_store.discard_calls, 1)
            self.assertEqual(len(host.session_store.persist_calls), 1)
            self.assertNotIn("project_doc", host.session_store.persist_calls[0])
            artifact_store = saved_doc["metadata"]["artifact_store"]
            self.assertEqual(artifact_store["staged"], {})
            self.assertEqual(
                artifact_store["artifacts"]["managed_image"]["relative_path"],
                self._workspace_relative(
                    "nodes/Image Panel - Managed [11111111]/in/media/diagram.png",
                    workspace_id=host.model.active_workspace.workspace_id,
                ),
            )
            self.assertEqual(
                artifact_store["artifacts"]["pending_output"]["relative_path"],
                self._workspace_relative(
                    "nodes/Image Panel - Staged [22222222]/out/outputs/run.txt",
                    workspace_id=host.model.active_workspace.workspace_id,
                ),
            )
            self.assertEqual(
                artifact_store["artifacts"]["pending_output"]["slot"],
                "process_run.stdout",
            )
            self.assertEqual(
                artifact_store["artifacts"]["pending_output"]["node_workspace_name"],
                "Main",
            )
            self.assertEqual(
                copied_managed_path.read_text(encoding="utf-8"), "managed payload"
            )
            self.assertEqual(
                copied_output_path.read_text(encoding="utf-8"), "staged payload"
            )
            self.assertFalse(copied_temp_path.exists())
            self.assertFalse(stale_managed_path.exists())
            self.assertFalse(stale_staging_path.exists())

            workspace_doc = saved_doc["workspaces"][0]
            saved_nodes = {node["node_id"]: node for node in workspace_doc["nodes"]}
            self.assertEqual(
                saved_nodes["node_managed"]["properties"]["source_path"],
                format_managed_artifact_ref("managed_image"),
            )
            self.assertEqual(
                saved_nodes["node_staged"]["properties"]["source_path"],
                format_managed_artifact_ref("pending_output"),
            )
            self.assertEqual(
                saved_nodes["node_external"]["properties"]["source_path"], external_path
            )

    def test_save_as_self_contained_copy_preserves_excalidraw_managed_assets_and_excludes_scratch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "source_project.cxproj"
            source_layout = source_project.with_name("source_project.data")
            source_image_path = (
                source_layout
                / "nodes"
                / "Excalidraw - Board [33333333]"
                / "in"
                / "excalidraw"
                / "image.png"
            )
            source_preview_path = (
                source_layout
                / "nodes"
                / "Excalidraw - Board [33333333]"
                / "out"
                / "excalidraw"
                / "preview.png"
            )
            source_scratch_path = (
                source_layout
                / "nodes"
                / "Excalidraw - Board [33333333]"
                / "tmp"
                / "out"
                / "excalidraw"
                / "scratch.png"
            )
            source_image_path.parent.mkdir(parents=True, exist_ok=True)
            source_image_path.write_text("managed image", encoding="utf-8")
            source_preview_path.parent.mkdir(parents=True, exist_ok=True)
            source_preview_path.write_text("managed preview", encoding="utf-8")
            source_scratch_path.parent.mkdir(parents=True, exist_ok=True)
            source_scratch_path.write_text("scratch payload", encoding="utf-8")
            image_ref = format_managed_artifact_ref("managed_excalidraw_image")
            preview_ref = format_managed_artifact_ref("managed_excalidraw_preview")
            persistent_document = {
                "schema_version": 1,
                "project_id": "proj_excalidraw_save_as",
                "name": "Excalidraw Save As",
                "active_workspace_id": "ws_1",
                "workspace_order": ["ws_1"],
                "workspaces": [
                    {
                        "workspace_id": "ws_1",
                        "name": "Main",
                        "dirty": True,
                        "active_view_id": "view_1",
                        "views": [
                            {
                                "view_id": "view_1",
                                "name": "Main",
                                "zoom": 1.0,
                                "pan_x": 0.0,
                                "pan_y": 0.0,
                                "scope_path": [],
                            }
                        ],
                        "nodes": [
                            {
                                "node_id": "node_excalidraw",
                                "type_id": EXCALIDRAW_BOARD_TYPE_ID,
                                "title": "Board",
                                "x": 0.0,
                                "y": 0.0,
                                "collapsed": False,
                                "properties": {
                                    EXCALIDRAW_STATE_PROPERTY: {
                                        "type": "excalidraw",
                                        "version": 2,
                                        "elements": [
                                            {
                                                "id": "image-element",
                                                "type": "image",
                                                "fileId": "file-managed",
                                            }
                                        ],
                                        "files": [
                                            {
                                                "id": "file-managed",
                                                "mimeType": "image/png",
                                                "artifact_ref": image_ref,
                                            }
                                        ],
                                        "appState": {"viewBackgroundColor": "#ffffff"},
                                    },
                                    EXCALIDRAW_PREVIEW_REF_PROPERTY: {
                                        "artifact_ref": preview_ref,
                                        "mime_type": "image/png",
                                    },
                                },
                                "exposed_ports": {},
                            }
                        ],
                        "edges": [],
                    }
                ],
                "metadata": {
                    "artifact_store": {
                        "artifacts": {
                            "managed_excalidraw_image": {
                                "relative_path": "nodes/Excalidraw - Board [33333333]/in/excalidraw/image.png",
                            },
                            "managed_excalidraw_preview": {
                                "relative_path": "nodes/Excalidraw - Board [33333333]/out/excalidraw/preview.png",
                            },
                        },
                        "staged": {
                            "unused_excalidraw_scratch": {
                                "relative_path": "nodes/Excalidraw - Board [33333333]/tmp/out/excalidraw/scratch.png",
                                "slot": "excalidraw.node_excalidraw.scratch",
                            },
                        },
                    }
                },
            }
            target_project = root / "copies" / "clone_project.cxproj"
            stale_target_scratch = (
                target_project.with_name("clone_project.data")
                / "nodes"
                / "Old Node [99999999]"
                / "tmp"
                / "out"
                / "old.txt"
            )
            stale_target_scratch.parent.mkdir(parents=True, exist_ok=True)
            stale_target_scratch.write_text("stale", encoding="utf-8")

            host = _ProjectHostStub(
                project_path=str(source_project),
                persistent_document=persistent_document,
            )
            controller = ProjectSessionController(host)  # type: ignore[arg-type]

            with (
                patch.object(
                    controller._project_files_service,
                    "prompt_project_files_action",
                    return_value=True,
                ),
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(target_project), "COREX Project (*.cxproj)"),
                ),
                patch(
                    "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                    _AcceptingSelfContainedSaveAsDialog,
                ),
            ):
                controller.save_project_as()

            saved_doc = json.loads(target_project.read_text(encoding="utf-8"))
            saved_properties = saved_doc["workspaces"][0]["nodes"][0]["properties"]
            target_layout = target_project.with_name("clone_project.data")
            copied_image_path = self._workspace_path(
                target_layout,
                "nodes/Excalidraw - Board [33333333]/in/excalidraw/image.png",
                workspace_id=host.model.active_workspace.workspace_id,
            )
            copied_preview_path = self._workspace_path(
                target_layout,
                "nodes/Excalidraw - Board [33333333]/out/excalidraw/preview.png",
                workspace_id=host.model.active_workspace.workspace_id,
            )
            copied_scratch_path = self._workspace_path(
                target_layout,
                "nodes/Excalidraw - Board [33333333]/tmp/out/excalidraw/scratch.png",
                workspace_id=host.model.active_workspace.workspace_id,
            )

            self.assertEqual(
                saved_properties[EXCALIDRAW_STATE_PROPERTY]["files"][0]["artifact_ref"],
                image_ref,
            )
            self.assertEqual(
                saved_properties[EXCALIDRAW_PREVIEW_REF_PROPERTY]["artifact_ref"],
                preview_ref,
            )
            artifact_store = saved_doc["metadata"]["artifact_store"]
            self.assertEqual(artifact_store["staged"], {})
            self.assertEqual(
                artifact_store["artifacts"]["managed_excalidraw_image"][
                    "relative_path"
                ],
                self._workspace_relative(
                    "nodes/Excalidraw - Board [33333333]/in/excalidraw/image.png",
                    workspace_id=host.model.active_workspace.workspace_id,
                ),
            )
            self.assertEqual(
                artifact_store["artifacts"]["managed_excalidraw_preview"][
                    "relative_path"
                ],
                self._workspace_relative(
                    "nodes/Excalidraw - Board [33333333]/out/excalidraw/preview.png",
                    workspace_id=host.model.active_workspace.workspace_id,
                ),
            )
            self.assertEqual(
                artifact_store["artifacts"]["managed_excalidraw_image"][
                    "node_workspace_name"
                ],
                "Main",
            )
            self.assertEqual(
                copied_image_path.read_text(encoding="utf-8"), "managed image"
            )
            self.assertEqual(
                copied_preview_path.read_text(encoding="utf-8"), "managed preview"
            )
            self.assertFalse(copied_scratch_path.exists())
            self.assertFalse(stale_target_scratch.exists())
            serialized_doc = json.dumps(saved_doc, sort_keys=True)
            self.assertNotIn("data:image", serialized_doc)
            self.assertNotIn("base64", serialized_doc)

    def test_save_as_prompts_with_staged_and_broken_summary_before_file_selection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "source_project.cxproj"
            managed_path = (
                source_project.with_name("source_project.data")
                / "nodes"
                / "Image Panel - Managed [11111111]"
                / "in"
                / "media"
                / "diagram.png"
            )
            managed_path.parent.mkdir(parents=True, exist_ok=True)
            managed_path.write_text("managed payload", encoding="utf-8")
            staged_path = (
                source_project.with_name("source_project.data")
                / "nodes"
                / "Image Panel - Staged [22222222]"
                / "tmp"
                / "out"
                / "outputs"
                / "run.txt"
            )
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_text("staged payload", encoding="utf-8")
            missing_external_path = str((root / "external" / "missing.png").resolve())
            persistent_document = self._build_persistent_document(
                external_path=missing_external_path
            )

            host = _ProjectHostStub(
                project_path=str(source_project),
                persistent_document=persistent_document,
            )
            controller = ProjectSessionController(host)  # type: ignore[arg-type]
            target_project = root / "copies" / "clone_project.cxproj"

            with (
                patch.object(
                    controller._project_files_service,
                    "prompt_project_files_action",
                    return_value=True,
                ) as prompt,
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(target_project), "COREX Project (*.cxproj)"),
                ),
                patch(
                    "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                    _AcceptingSelfContainedSaveAsDialog,
                ),
            ):
                controller.save_project_as()

        self.assertEqual(prompt.call_count, 1)
        snapshot = prompt.call_args.kwargs["snapshot"]
        self.assertEqual(snapshot.managed_count, 1)
        self.assertEqual(snapshot.staged_count, 1)
        self.assertEqual(snapshot.broken_count, 1)

    def test_save_as_cancelled_from_project_file_prompt_skips_file_selection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_project = root / "source" / "source_project.cxproj"
            managed_path = (
                source_project.with_name("source_project.data")
                / "nodes"
                / "Image Panel - Managed [11111111]"
                / "in"
                / "media"
                / "diagram.png"
            )
            managed_path.parent.mkdir(parents=True, exist_ok=True)
            managed_path.write_text("managed payload", encoding="utf-8")
            missing_external_path = str((root / "external" / "missing.png").resolve())
            persistent_document = self._build_persistent_document(
                external_path=missing_external_path
            )

            host = _ProjectHostStub(
                project_path=str(source_project),
                persistent_document=persistent_document,
            )
            controller = ProjectSessionController(host)  # type: ignore[arg-type]

            with (
                patch.object(
                    controller._project_files_service,
                    "prompt_project_files_action",
                    return_value=False,
                ) as prompt,
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                ) as file_dialog,
                patch(
                    "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                    _AcceptingSelfContainedSaveAsDialog,
                ),
            ):
                controller.save_project_as()

        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(file_dialog.call_count, 0)
        self.assertEqual(host.serializer.saved_documents, [])







    def test_save_as_plain_project_without_managed_data_still_switches_to_new_path(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target_project = root / "copies" / "plain_project.cxproj"
            persistent_document = {
                "schema_version": 1,
                "project_id": "proj_plain",
                "name": "Plain Project",
                "active_workspace_id": "ws_1",
                "workspace_order": ["ws_1"],
                "workspaces": [
                    {
                        "workspace_id": "ws_1",
                        "name": "Main",
                        "dirty": True,
                        "active_view_id": "view_1",
                        "views": [
                            {
                                "view_id": "view_1",
                                "name": "Main",
                                "zoom": 1.0,
                                "pan_x": 0.0,
                                "pan_y": 0.0,
                                "scope_path": [],
                            }
                        ],
                        "nodes": [],
                        "edges": [],
                    }
                ],
                "metadata": {},
            }
            host = _ProjectHostStub(
                project_path="", persistent_document=persistent_document
            )
            host.script_editor.panel_width = 720.0
            controller = ProjectSessionController(host)  # type: ignore[arg-type]

            with (
                patch.object(
                    controller._project_files_service,
                    "prompt_project_files_action",
                    return_value=True,
                ),
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(target_project), "COREX Project (*.cxproj)"),
                ),
                patch(
                    "ea_node_editor.ui.dialogs.project_save_as_dialog.ProjectSaveAsDialog",
                    _AcceptingSelfContainedSaveAsDialog,
                ),
            ):
                controller.save_project_as()

            saved_doc = json.loads(target_project.read_text(encoding="utf-8"))
            self.assertEqual(host.project_path, str(target_project))
            self.assertEqual(
                saved_doc["metadata"]["ui"]["script_editor"]["width"], 720.0
            )
            self.assertEqual(
                saved_doc["metadata"]["artifact_store"],
                {
                    "artifacts": {},
                    "staged": {},
                },
            )


if __name__ == "__main__":
    unittest.main()
