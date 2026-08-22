from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtWidgets import QApplication

from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.surface_contracts import surface_spec_payload_for_node_type


_ROOT = Path(__file__).resolve().parents[1]
_QML_PATH = (
    _ROOT
    / "ea_node_editor"
    / "ui_qml"
    / "components"
    / "graph"
    / "dpf"
    / "GraphDpfWorkflowSurface.qml"
)
_NODE_TYPE_IDS = (
    "dpf.workflow.result_source",
    "dpf.workflow.result_fields",
    "dpf.workflow.min_max_envelope",
    "dpf.workflow.time_history_probe",
    "dpf.workflow.stress_invariants",
    "dpf.workflow.field_math",
    "dpf.workflow.table_export",
)


def _variant(value):  # noqa: ANN001
    converter = getattr(value, "toVariant", None)
    return converter() if callable(converter) else value


def _node_data(
    type_id: str,
    *,
    properties: dict | None = None,
    connected_ports: tuple[str, ...] = (),
) -> dict:
    return {
        "node_id": "dpf-node",
        "type_id": type_id,
        "properties": dict(properties or {}),
        "ports": [
            {"key": key, "connected": True}
            for key in connected_ports
        ],
    }


def _create_surface_with_host(node_data: dict):  # noqa: ANN001
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QApplication.instance() or QApplication([])
    engine = QQmlEngine()
    engine.addImportPath(str(_QML_PATH.parents[2]))

    host_component = QQmlComponent(engine)
    host_component.setData(
        b"""
import QtQuick 2.15
Item {
    property var nodeData: ({})
    property var executionFacts: ({ "dpfWorkflowSummaryLookup": ({}) })
    property bool isFailedNode: false
    property bool isRunningNode: false
    property color inlineRowColor: "#20242b"
    property color inlineRowBorderColor: "#3a414d"
    property color inlineInputTextColor: "#eef2f7"
    property color inlineLabelColor: "#b7c0ce"
    property color inlineInputBackgroundColor: "#22242a"
    property color inlineInputBorderColor: "#4a4f5a"
    property color selectedOutlineColor: "#60cdff"
    property color warningOutlineColor: "#d4a72c"
    property color completedOutlineColor: "#3fb950"
    property color failureOutlineColor: "#f85149"
    property color runningOutlineColor: "#58a6ff"
    property int nodeTextRenderType: Text.CurveRendering
    property var graphSharedTypography: ({
        "inlinePropertyPixelSize": 10,
        "inlinePropertyFontWeight": Font.Normal
    })
    signal surfaceControlInteractionStarted(string nodeId)
    signal inlinePropertyCommitted(string nodeId, string key, var value)
}
""",
        QUrl(),
    )
    assert host_component.status() == QQmlComponent.Status.Ready, "\n".join(
        error.toString() for error in host_component.errors()
    )
    host = host_component.create()
    assert host is not None
    host.setProperty("nodeData", node_data)

    surface_component = QQmlComponent(engine, QUrl.fromLocalFile(str(_QML_PATH)))
    assert surface_component.status() == QQmlComponent.Status.Ready, "\n".join(
        error.toString() for error in surface_component.errors()
    )
    surface = surface_component.create()
    assert surface is not None
    surface.setProperty("width", 300.0)
    surface.setProperty("host", host)
    app.processEvents()
    return app, engine, surface, host


def _set_node_data(app, host, node_data: dict) -> None:  # noqa: ANN001
    host.setProperty("nodeData", node_data)
    app.processEvents()


def test_non_viewer_curated_nodes_use_dpf_workflow_surface() -> None:
    registry = build_default_registry()
    for type_id in _NODE_TYPE_IDS:
        spec = registry.get_spec(type_id)
        assert spec.surface_family == "dpf_workflow"
        payload = surface_spec_payload_for_node_type(type_id=type_id, spec=spec)
        assert payload["component_key"] == "dpf_workflow"
        assert payload["qml_component"] == "dpf/GraphDpfWorkflowSurface.qml"
        assert payload["layout"]["content_region"] == "body"


def test_viewer_shortcuts_keep_viewer_surface() -> None:
    registry = build_default_registry()
    assert registry.get_spec("dpf.workflow.result_viewer").surface_family == "viewer"
    assert registry.get_spec("dpf.workflow.mode_shape_viewer").surface_family == "viewer"


def test_dpf_workflow_surface_loads_offscreen_without_host() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QApplication.instance() or QApplication([])
    engine = QQmlEngine()
    engine.addImportPath(str(_QML_PATH.parents[2]))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(_QML_PATH)))
    assert component.status() == QQmlComponent.Status.Ready, "\n".join(
        error.toString() for error in component.errors()
    )
    surface = component.create()
    try:
        assert surface is not None
        assert surface.objectName() == "graphDpfWorkflowSurface"
        assert surface.property("minimumBodyWidth") == 300.0
        assert surface.property("minimumBodyHeight") == 188.0
    finally:
        if surface is not None:
            surface.deleteLater()
        engine.deleteLater()
        app.processEvents()


def test_dpf_workflow_surface_uses_shared_execution_and_edit_paths() -> None:
    source = _QML_PATH.read_text(encoding="utf-8")
    assert "dpfWorkflowSummaryLookup" in source
    assert "host.inlinePropertyCommitted" in source
    assert "host.surfaceControlInteractionStarted" in source
    assert "GraphSurfaceComboBox" in source
    assert "dpf.workflow.result_viewer" not in _NODE_TYPE_IDS


def test_dpf_workflow_surface_reports_each_next_required_action() -> None:
    base_result = {
        "result_name": "displacement",
        "selection_mode": "all",
        "time_scope_mode": "first_set",
        "location": "auto",
    }
    app, engine, surface, host = _create_surface_with_host(
        _node_data("dpf.workflow.result_source", properties={"path": ""})
    )
    try:
        cases = (
            (
                _node_data("dpf.workflow.result_source", properties={"path": ""}),
                "Choose a result file in Inspector",
            ),
            (
                _node_data("dpf.workflow.result_fields", properties=base_result),
                "Connect Model",
            ),
            (
                _node_data(
                    "dpf.workflow.result_fields",
                    properties={**base_result, "result_name": ""},
                    connected_ports=("model",),
                ),
                "Choose a result type in Inspector",
            ),
            (
                _node_data(
                    "dpf.workflow.time_history_probe",
                    properties={**base_result, "selection_mode": "choose_scope"},
                    connected_ports=("model",),
                ),
                "Choose a named selection, Node IDs, or Element IDs in Inspector",
            ),
            (
                _node_data(
                    "dpf.workflow.result_fields",
                    properties={**base_result, "selection_mode": "named_selection", "named_selection": ""},
                    connected_ports=("model",),
                ),
                "Choose a named selection in Inspector",
            ),
            (
                _node_data(
                    "dpf.workflow.result_fields",
                    properties={**base_result, "selection_mode": "node_ids", "node_ids": ""},
                    connected_ports=("model",),
                ),
                "Enter Node IDs in Inspector",
            ),
            (
                _node_data(
                    "dpf.workflow.result_fields",
                    properties={**base_result, "selection_mode": "element_ids", "element_ids": ""},
                    connected_ports=("model",),
                ),
                "Enter Element IDs in Inspector",
            ),
            (
                _node_data(
                    "dpf.workflow.result_fields",
                    properties={**base_result, "time_scope_mode": "set_ids", "set_ids": ""},
                    connected_ports=("model",),
                ),
                "Enter Set IDs in Inspector",
            ),
            (
                _node_data(
                    "dpf.workflow.result_fields",
                    properties={**base_result, "time_scope_mode": "time_values", "time_values": ""},
                    connected_ports=("model",),
                ),
                "Enter time values in Inspector",
            ),
            (
                _node_data(
                    "dpf.workflow.field_math",
                    properties={"operation": "add"},
                ),
                "Connect input A",
            ),
            (
                _node_data(
                    "dpf.workflow.field_math",
                    properties={"operation": "subtract"},
                    connected_ports=("a",),
                ),
                "B required for Subtract — connect input B",
            ),
            (
                _node_data(
                    "dpf.workflow.table_export",
                    connected_ports=("model",),
                ),
                "Connect Fields",
            ),
            (
                _node_data(
                    "dpf.workflow.table_export",
                    connected_ports=("fields",),
                ),
                "Connect Model",
            ),
        )
        for node_data, expected in cases:
            _set_node_data(app, host, node_data)
            assert surface.property("nextRequiredAction") == expected
            assert surface.property("incomplete") is True
            assert surface.property("statusMessage") == f"Setup incomplete — {expected}"
    finally:
        surface.deleteLater()
        host.deleteLater()
        engine.deleteLater()
        app.processEvents()


def test_field_math_surface_keeps_b_visible_and_explains_its_requirement() -> None:
    app, engine, surface, host = _create_surface_with_host(
        _node_data(
            "dpf.workflow.field_math",
            properties={"operation": "add"},
            connected_ports=("a", "b"),
        )
    )
    try:
        assert surface.property("incomplete") is False
        assert surface.property("fieldMathPortGuidance") == "B required for Add — connected"

        _set_node_data(
            app,
            host,
            _node_data(
                "dpf.workflow.field_math",
                properties={"operation": "scale"},
                connected_ports=("a",),
            ),
        )
        assert surface.property("incomplete") is False
        assert surface.property("fieldMathPortGuidance") == "B unused for Scale"

        _set_node_data(
            app,
            host,
            _node_data(
                "dpf.workflow.field_math",
                properties={"operation": "scale"},
                connected_ports=("a", "b"),
            ),
        )
        assert surface.property("incomplete") is False
        assert surface.property("fieldMathPortGuidance") == (
            "B unused for Scale — disconnect input B"
        )

        spec = build_default_registry().get_spec("dpf.workflow.field_math")
        b_port = next(port for port in spec.ports if port.key == "b")
        assert b_port.required is False
    finally:
        surface.deleteLater()
        host.deleteLater()
        engine.deleteLater()
        app.processEvents()


def test_dpf_workflow_surface_uses_domain_labels_and_elides_result_facts() -> None:
    app, engine, surface, host = _create_surface_with_host(
        _node_data(
            "dpf.workflow.stress_invariants",
            properties={
                "invariant": "principal_1",
                "selection_mode": "all",
                "time_scope_mode": "set_ids",
                "set_ids": "1, 2",
                "location": "auto",
            },
            connected_ports=("model",),
        )
    )
    try:
        rows = _variant(surface.property("controlRows"))
        labels_by_key = {row["key"]: list(row["labels"]) for row in rows}
        assert labels_by_key["selection_mode"] == [
            "Whole model",
            "Named selection",
            "Node IDs",
            "Element IDs",
        ]
        assert labels_by_key["time_scope_mode"] == [
            "First set",
            "Last set",
            "All sets",
            "Set IDs",
            "Time values",
        ]
        assert labels_by_key["invariant"][1:4] == [
            "Principal S1",
            "Principal S2",
            "Principal S3",
        ]
        summary = surface.findChild(QObject, "dpfWorkflowConfigurationSummary")
        assert summary is not None
        assert summary.property("text") == (
            "Principal S1 · Whole model · Set IDs · Native location"
        )

        source = _QML_PATH.read_text(encoding="utf-8")
        assert "id: factsColumn" in source
        assert "elide: Text.ElideMiddle" in source
        assert "maximumLineCount: 1" in source
    finally:
        surface.deleteLater()
        host.deleteLater()
        engine.deleteLater()
        app.processEvents()
