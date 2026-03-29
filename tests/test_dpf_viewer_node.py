from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

dpf = pytest.importorskip("ansys.dpf.core")
pytest.importorskip("pyvista")

from ansys_dpf_core.fixture_paths import STATIC_ANALYSIS_RST
from ea_node_editor.execution.dpf_runtime_service import DPF_VIEWER_DATASET_HANDLE_KIND
from ea_node_editor.execution.protocol import CloseViewerSessionCommand, OpenViewerSessionCommand
from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.ansys_dpf import (
    DpfModelNodePlugin,
    DpfResultFieldNodePlugin,
    DpfViewerNodePlugin,
)
from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    DPF_MODEL_NODE_TYPE_ID,
    DPF_RESULT_FIELD_NODE_TYPE_ID,
    DPF_VIEWER_NODE_TYPE_ID,
)
from ea_node_editor.nodes.types import ExecutionContext
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver


class DpfViewerNodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()

    def _execution_context(
        self,
        node_type_id: str,
        *,
        inputs: dict[str, object] | None = None,
        properties: dict[str, object] | None = None,
        services: WorkerServices | None = None,
        node_id: str | None = None,
    ) -> ExecutionContext:
        resolver = ProjectArtifactResolver(project_path=None)
        return ExecutionContext(
            run_id="run_dpf_viewer",
            node_id=node_id or f"node_{node_type_id.replace('.', '_')}",
            workspace_id="ws_dpf_viewer",
            inputs=dict(inputs or {}),
            properties=self.registry.normalize_properties(node_type_id, dict(properties or {})),
            emit_log=lambda _level, _message: None,
            path_resolver=resolver.resolve_to_path,
            worker_services=services or WorkerServices(),
        )

    def _model_and_field_refs(self, services: WorkerServices) -> tuple[object, object]:
        model_ref = DpfModelNodePlugin().execute(
            self._execution_context(
                DPF_MODEL_NODE_TYPE_ID,
                inputs={"path": str(STATIC_ANALYSIS_RST)},
                services=services,
            )
        ).outputs["model"]
        field_ref = DpfResultFieldNodePlugin().execute(
            self._execution_context(
                DPF_RESULT_FIELD_NODE_TYPE_ID,
                inputs={"model": model_ref},
                properties={"result_name": "displacement", "set_ids": "2"},
                services=services,
            )
        ).outputs["field"]
        return model_ref, field_ref

    def test_viewer_node_seeds_cached_session_payload_with_live_dataset_defaults(self) -> None:
        services = WorkerServices()
        model_ref, field_ref = self._model_and_field_refs(services)

        session_payload = DpfViewerNodePlugin().execute(
            self._execution_context(
                DPF_VIEWER_NODE_TYPE_ID,
                inputs={"field": field_ref, "model": model_ref},
                services=services,
                node_id="node_viewer_packet_p13",
            )
        ).outputs["session"]

        self.assertEqual(session_payload["workspace_id"], "ws_dpf_viewer")
        self.assertEqual(session_payload["node_id"], "node_viewer_packet_p13")
        self.assertTrue(session_payload["session_id"].startswith("viewer_session_"))
        self.assertEqual(session_payload["backend_id"], DPF_EXECUTION_VIEWER_BACKEND_ID)
        self.assertEqual(session_payload["summary"]["result_name"], "displacement")
        self.assertEqual(session_payload["summary"]["set_id"], 2)
        self.assertEqual(session_payload["summary"]["set_label"], "Set 2")
        self.assertEqual(session_payload["summary"]["cache_state"], "live_ready")
        self.assertEqual(session_payload["live_open_status"], "ready")
        self.assertEqual(session_payload["options"]["output_profile"], "both")
        self.assertEqual(session_payload["options"]["live_policy"], "focus_only")
        self.assertFalse(session_payload["options"]["keep_live"])
        self.assertEqual(session_payload["options"]["live_mode"], "proxy")
        self.assertEqual(session_payload["options"]["session_state"], "open")
        self.assertGreaterEqual(int(session_payload["transport_revision"]), 1)
        self.assertEqual(session_payload["transport"]["kind"], "dpf_transport_bundle")
        self.assertIn("manifest_path", session_payload["transport"])
        self.assertIn("entry_path", session_payload["transport"])
        self.assertEqual(session_payload["data_refs"]["dataset"].kind, DPF_VIEWER_DATASET_HANDLE_KIND)

    def test_viewer_node_reopen_restores_result_summary_and_keep_live_policy(self) -> None:
        services = WorkerServices()
        model_ref, field_ref = self._model_and_field_refs(services)

        session_payload = DpfViewerNodePlugin().execute(
            self._execution_context(
                DPF_VIEWER_NODE_TYPE_ID,
                inputs={"field": field_ref, "model": model_ref},
                properties={"viewer_live_policy": "keep_live", "output_mode": "memory"},
                services=services,
                node_id="node_viewer_keep_live_packet_p13",
            )
        ).outputs["session"]

        closed = services.viewer_session_service.close_session(
            CloseViewerSessionCommand(
                workspace_id="ws_dpf_viewer",
                node_id="node_viewer_keep_live_packet_p13",
                session_id=session_payload["session_id"],
                options={"reason": "test_demote", "release_handles": True},
            )
        )
        reopened = services.viewer_session_service.open_session(
            OpenViewerSessionCommand(
                workspace_id="ws_dpf_viewer",
                node_id="node_viewer_keep_live_packet_p13",
                session_id=session_payload["session_id"],
            )
        )

        self.assertEqual(closed.summary["close_reason"], "test_demote")
        self.assertEqual(reopened.summary["result_name"], "displacement")
        self.assertEqual(reopened.summary["set_label"], "Set 2")
        self.assertEqual(reopened.options["live_policy"], "keep_live")
        self.assertTrue(reopened.options["keep_live"])
        self.assertEqual(reopened.options["live_mode"], "proxy")
        self.assertEqual(reopened.summary["cache_state"], "proxy_ready")
        self.assertEqual(reopened.backend_id, DPF_EXECUTION_VIEWER_BACKEND_ID)
        self.assertEqual(reopened.live_open_status, "blocked")
        self.assertEqual(reopened.live_open_blocker["code"], "rerun_required")


if __name__ == "__main__":
    unittest.main()
