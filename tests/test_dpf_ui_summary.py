from __future__ import annotations

import json
import unittest
from pathlib import Path

from ea_node_editor.addons.ansys_dpf.ui_summary import project_dpf_workflow_summary
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_FIELDS_CONTAINER_DATA_TYPE,
    DPF_MODEL_DATA_TYPE,
)
from ea_node_editor.runtime_contracts import (
    PATH_DATA_TYPE_ID,
    RuntimeArtifactRef,
    RuntimeHandleRef,
)
from ea_node_editor.runtime_contracts.solution_records import (
    NodeSolutionFact,
    SolutionDisposition,
    SolutionFreshness,
    SolutionResidency,
)
from ea_node_editor.ui.shell.state import ShellRunState
from ea_node_editor.ui_qml.graph_canvas_state import GraphCanvasStateBridge


def _handle(kind: str, **metadata) -> RuntimeHandleRef:  # noqa: ANN003
    data_type_id = {
        "dpf.fields_container": DPF_FIELDS_CONTAINER_DATA_TYPE,
        "dpf.model": DPF_MODEL_DATA_TYPE,
    }[kind]
    return RuntimeHandleRef(
        data_type_id=data_type_id,
        schema_version=1,
        handle_id=f"handle_{kind}",
        kind=kind,
        owner_scope="run:test",
        worker_generation=0,
        metadata=metadata,
    )


class _ExecutionSource:
    def __init__(self) -> None:
        self.run_state = ShellRunState()


class _SceneState:
    workspace_id = "workspace"


class _SceneBridge:
    state_bridge = _SceneState()


class DpfUiSummaryTests(unittest.TestCase):
    def assert_qml_safe(self, payload: object) -> None:
        json.dumps(payload)
        self.assertNotIn("handle_id", repr(payload))
        self.assertNotIn("coordinates", repr(payload))

    def test_result_source_and_fields_use_only_compact_metadata(self) -> None:
        source = project_dpf_workflow_summary(
            "dpf.workflow.result_source",
            {
                "normalized_path": r"C:\results\demo.rst",
                "model": _handle("dpf.model", extension=".rst"),
            },
        )
        fields = project_dpf_workflow_summary(
            "dpf.workflow.result_fields",
            {
                "fields": _handle(
                    "dpf.fields_container",
                    result_name="displacement",
                    location="Nodal",
                    unit="mm",
                    field_count=2,
                    set_ids=[1, 2],
                    value_ranges=[{"minimum": -1.0, "maximum": 4.0}],
                )
            },
        )

        self.assertEqual(source["headline"], "demo.rst")
        self.assertEqual(fields["headline"], "Displacement · 2 fields")
        self.assertEqual(fields["detail"], "Nodal · mm")
        self.assert_qml_safe(source)
        self.assert_qml_safe(fields)

    def test_envelope_reports_peak_without_copying_coordinates_or_tables(self) -> None:
        summary = project_dpf_workflow_summary(
            "dpf.workflow.min_max_envelope",
            {
                "per_set_table": [{"set_id": index} for index in range(50)],
                "summary": {
                    "result_name": "stress",
                    "location": "Nodal",
                    "unit": "MPa",
                    "max": {
                        "value": 412.8,
                        "entity_id": 18342,
                        "set_id": 17,
                        "coordinates": [1.0, 2.0, 3.0],
                    },
                },
            },
        )

        self.assertEqual(summary["headline"], "Max 412.8 MPa")
        self.assertEqual(summary["detail"], "Entity 18342 · Set 17")
        self.assert_qml_safe(summary)

    def test_time_history_reports_counts_without_copying_rows(self) -> None:
        summary = project_dpf_workflow_summary(
            "dpf.workflow.time_history_probe",
            {
                "series": _handle(
                    "dpf.fields_container",
                    result_name="displacement",
                    unit="mm",
                    field_count=3,
                    entity_ids=[10, 20, 30],
                ),
                "time_values": [0.0, 0.5, 1.0, 1.5],
                "table": [{"entity_id": entity_id} for entity_id in range(12)],
            },
        )

        self.assertEqual(summary["headline"], "3 curves · 12 rows")
        self.assertEqual(
            summary["facts"],
            [
                {"label": "Entities", "value": "3"},
                {"label": "Sets", "value": "4"},
                {"label": "Curves", "value": "3"},
                {"label": "Rows", "value": "12"},
            ],
        )
        self.assert_qml_safe(summary)

    def test_stress_and_field_math_use_operation_metadata(self) -> None:
        cases = (
            ("dpf.workflow.stress_invariants", "von_mises", "Von Mises"),
            ("dpf.workflow.field_math", "subtract", "Subtract"),
        )
        for node_type_id, operation, expected in cases:
            with self.subTest(node_type_id=node_type_id):
                summary = project_dpf_workflow_summary(
                    node_type_id,
                    {
                        "fields": _handle(
                            "dpf.fields_container",
                            operation=operation,
                            location="Nodal",
                            unit="MPa",
                            field_count=1,
                        )
                    },
                )
                self.assertEqual(summary["headline"], f"{expected} · Nodal · MPa")
                self.assert_qml_safe(summary)

    def test_table_export_reports_row_count_and_opaque_artifact_ref(self) -> None:
        artifact = RuntimeArtifactRef.staged(
            "dpf_table_csv",
            data_type_id=PATH_DATA_TYPE_ID,
            schema_version=1,
            format="csv",
            size_bytes=0,
            sha256="0" * 64,
            provenance="corex.test.fixture",
            metadata={"entry_file": "table.csv", "row_count": 58_204},
        )
        summary = project_dpf_workflow_summary(
            "dpf.workflow.table_export",
            {"table": [{} for _ in range(4)], "csv": artifact},
        )

        self.assertEqual(summary["headline"], "4 rows exported")
        self.assertEqual(summary["detail"], "dpf_table_csv")
        self.assertEqual(summary["facts"][-1]["value"], "temp://dpf_table_csv")
        self.assert_qml_safe(summary)

    def test_execution_fact_uses_latest_summary_and_preserves_stale_state(self) -> None:
        source = _ExecutionSource()
        source.run_state.cached_node_output_records_by_workspace_id = {
            "workspace": {
                "node": {
                    "older": {
                        "record_id": "older",
                        "observed_at_epoch_ms": 100.0,
                        "stale": False,
                        "dpf_workflow_summary": {
                            "headline": "Older",
                            "detail": "",
                            "facts": [],
                        },
                    },
                    "newer": {
                        "record_id": "newer",
                        "observed_at_epoch_ms": 200.0,
                        "stale": True,
                        "dpf_workflow_summary": {
                            "headline": "Newer",
                            "detail": "Graph changed",
                            "facts": [{"label": "Rows", "value": "10"}],
                        },
                    },
                }
            }
        }
        source.run_state.node_solution_facts_by_workspace_id = {
            "workspace": {
                "node": NodeSolutionFact(
                    project_id="project",
                    workspace_id="workspace",
                    node_id="node",
                    freshness=SolutionFreshness.EXPIRED,
                    revision=1,
                    retained_record_id="newer",
                    retained_solution_key="a" * 64,
                    residency=SolutionResidency.SESSION,
                    expiration_reason_code="graph_changed",
                    expiration_root_node_ids=("node",),
                    last_disposition=SolutionDisposition.RECOMPUTED,
                )
            }
        }
        bridge = GraphCanvasStateBridge(
            execution_source=source,
            scene_bridge=_SceneBridge(),  # type: ignore[arg-type]
        )

        self.assertEqual(
            bridge.dpf_workflow_summary_lookup,
            {
                "node": {
                    "state": "stale",
                    "headline": "Newer",
                    "detail": "Graph changed",
                    "facts": [{"label": "Rows", "value": "10"}],
                }
            },
        )

    def test_metadata_only_record_does_not_project_a_ready_dpf_summary(self) -> None:
        source = _ExecutionSource()
        source.run_state.cached_node_output_records_by_workspace_id = {
            "workspace": {
                "node": {
                    "record": {
                        "record_id": "record",
                        "observed_at_epoch_ms": 1.0,
                        "outputs_available": False,
                        "dpf_workflow_summary": {
                            "headline": "Stress · 2 fields",
                            "detail": "Nodal · MPa",
                            "facts": [],
                        },
                    }
                }
            }
        }
        source.run_state.node_solution_facts_by_workspace_id = {
            "workspace": {
                "node": NodeSolutionFact(
                    project_id="project",
                    workspace_id="workspace",
                    node_id="node",
                    freshness=SolutionFreshness.CURRENT,
                    revision=1,
                    retained_record_id="record",
                    retained_solution_key="a" * 64,
                    residency=SolutionResidency.SESSION,
                    last_disposition=SolutionDisposition.RECOMPUTED,
                )
            }
        }
        bridge = GraphCanvasStateBridge(
            execution_source=source,
            scene_bridge=_SceneBridge(),  # type: ignore[arg-type]
        )

        self.assertEqual(
            bridge.dpf_workflow_summary_lookup,
            {
                "node": {
                    "state": "unavailable",
                    "headline": "Unavailable",
                    "detail": "",
                    "facts": [],
                }
            },
        )

    def test_qml_fact_and_unsupported_node_fallback(self) -> None:
        self.assertIsNone(project_dpf_workflow_summary("core.logger", {}))
        qml_path = (
            Path(__file__).resolve().parents[1]
            / "ea_node_editor"
            / "ui_qml"
            / "components"
            / "graph_canvas"
            / "GraphCanvasExecutionFacts.qml"
        )
        qml = qml_path.read_text(encoding="utf-8")
        self.assertIn("readonly property var dpfWorkflowSummaryLookup", qml)
        self.assertIn("facts.stateBridge.dpf_workflow_summary_lookup", qml)


if __name__ == "__main__":
    unittest.main()
