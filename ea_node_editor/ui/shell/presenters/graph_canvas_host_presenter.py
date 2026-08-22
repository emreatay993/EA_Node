from __future__ import annotations

import copy
import json
from typing import Any

from PyQt6.QtCore import QObject, QUrl

from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.platform_open import open_path_with_app_chooser, open_path_with_default_handler
from ea_node_editor.ui.media_preview_provider import describe_local_image
from ea_node_editor.ui.mail_preview_provider import describe_mail_preview
from ea_node_editor.ui.pdf_preview_provider import describe_pdf_preview
from ea_node_editor.ui.tabular_preview_async import TabularPreviewWorkerPool
from ea_node_editor.ui.tabular_preview_provider import TabularPreviewProvider

from .contracts import _GraphCanvasHostPresenterHostProtocol, _presenter_parent


class GraphCanvasHostPresenter(QObject):
    def __init__(
        self,
        host: _GraphCanvasHostPresenterHostProtocol,
        *,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(_presenter_parent(host, parent))
        self._host = host
        self._tabular_preview_provider = TabularPreviewProvider(
            project_context_provider=self._project_context,
        )
        self._tabular_preview_worker_pool = TabularPreviewWorkerPool(self)
        self._tabular_preview_worker_pool.job_finished.connect(self._on_tabular_preview_job_finished)
        self._tabular_preview_errors: dict[str, str] = {}

    def shutdown(self) -> None:
        self._tabular_preview_worker_pool.shutdown()
        self._tabular_preview_errors.clear()

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:
        result = self._host.workspace_library_controller.request_delete_selected_graph_items(edge_ids)
        return bool(result.payload)

    def request_navigate_scope_parent(self) -> bool:
        return bool(self._host.search_scope_controller.navigate_scope(self._host.scene.navigate_scope_parent))

    def request_navigate_scope_root(self) -> bool:
        return bool(self._host.search_scope_controller.navigate_scope(self._host.scene.navigate_scope_root))

    def set_graph_cursor_shape(self, cursor_shape: int) -> None:
        self._host.shell_host_presenter.set_graph_cursor_shape(cursor_shape)

    def clear_graph_cursor_shape(self) -> None:
        self._host.shell_host_presenter.clear_graph_cursor_shape()

    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]:
        return describe_pdf_preview(source, page_number)

    def describe_image_preview(self, source: str) -> dict[str, Any]:
        return describe_local_image(source)

    def describe_mail_preview(self, source: str) -> dict[str, Any]:
        return describe_mail_preview(source)

    def open_local_file_source(self, source: str, chooser: bool = False) -> dict[str, Any]:
        project_path, project_metadata = self._project_context()
        resolver = ProjectArtifactResolver(
            project_path=project_path,
            project_metadata=project_metadata,
        )
        path = resolver.resolve_to_path(str(source or "").strip())
        if path is None or not path.exists() or not path.is_file():
            return {
                "success": False,
                "path": "",
                "error": {
                    "code": "missing_file",
                    "message": "The selected source file could not be opened.",
                },
            }
        opener = open_path_with_app_chooser if bool(chooser) else open_path_with_default_handler
        if not opener(path):
            return {
                "success": False,
                "path": str(path),
                "error": {
                    "code": "open_failed",
                    "message": f'Could not open "{path}".',
                },
            }
        return {"success": True, "path": str(path), "error": {}}

    def describe_tabular_preview(
        self,
        properties_or_source: dict[str, Any] | str,
        request: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._tabular_preview_provider.describe_preview(
            properties_or_source,
            request,
            mode="inline",
        )
        if isinstance(payload, dict) and payload.get("state") == "loading":
            job_key = self._tabular_preview_job_key(properties_or_source, request)
            error = self._tabular_preview_errors.get(job_key, "")
            if error:
                return self._tabular_error_payload(error)
            # Cold cache: resolve on the worker (where conversion is allowed);
            # the provider's session caches absorb the result so the surface's
            # next describe is a warm hit.
            self._schedule_tabular_preview_build(properties_or_source, request, job_key=job_key)
        return payload

    def _schedule_tabular_preview_build(
        self,
        properties_or_source: dict[str, Any] | str,
        request: dict[str, Any] | None,
        *,
        job_key: str | None = None,
    ) -> None:
        properties_snapshot = copy.deepcopy(properties_or_source)
        request_snapshot = copy.deepcopy(request)
        normalized_job_key = job_key or self._tabular_preview_job_key(properties_snapshot, request_snapshot)

        def build() -> None:
            self._tabular_preview_provider.describe_preview(
                properties_snapshot,
                request_snapshot,
                mode="inline",
            )

        if self._tabular_preview_worker_pool.schedule(normalized_job_key, build):
            self._tabular_preview_errors.pop(normalized_job_key, None)

    @staticmethod
    def _tabular_preview_job_key(
        properties_or_source: dict[str, Any] | str,
        request: dict[str, Any] | None,
    ) -> str:
        return "inline:" + json.dumps(
            {"properties": properties_or_source, "request": request},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    def _on_tabular_preview_job_finished(self, job_key: str, error: str) -> None:
        if error:
            self._tabular_preview_errors[str(job_key)] = str(error)
        else:
            self._tabular_preview_errors.pop(str(job_key), None)

    @staticmethod
    def _tabular_error_payload(message: str) -> dict[str, Any]:
        return {
            "state": "error",
            "content_kind": "tabular",
            "preview_kind": "",
            "message": str(message or "Tabular preview is unavailable."),
            "error": {
                "code": "tabular_inline_unavailable",
                "message": str(message or "Tabular preview is unavailable."),
                "recoverable": True,
            },
        }

    def resolve_local_file_source_url(self, source: str) -> str:
        project_path, project_metadata = self._project_context()
        resolver = ProjectArtifactResolver(
            project_path=project_path,
            project_metadata=project_metadata,
        )
        path = resolver.resolve_to_path(str(source or "").strip())
        if path is None:
            return ""
        return QUrl.fromLocalFile(str(path)).toString()

    def _project_context(self) -> tuple[str | None, dict[str, Any] | None]:
        project_path = str(getattr(self._host, "project_path", "") or "").strip() or None
        model = getattr(self._host, "model", None)
        project = getattr(model, "project", None)
        metadata = getattr(project, "metadata", None)
        return project_path, dict(metadata) if isinstance(metadata, dict) else None

    def request_edit_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_edit_flow_edge_style(edge_id))

    def request_edit_flow_edge_label(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_edit_flow_edge_label(edge_id))

    def request_reset_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_reset_flow_edge_style(edge_id))

    def request_copy_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_copy_flow_edge_style(edge_id))

    def request_paste_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_paste_flow_edge_style(edge_id))

    def request_remove_edge(self, edge_id: str) -> bool:
        result = self._host.workspace_library_controller.request_remove_edge(edge_id)
        return bool(result.payload)

    def request_edit_passive_node_style(self, node_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_edit_passive_node_style(node_id))

    def request_reset_passive_node_style(self, node_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_reset_passive_node_style(node_id))

    def request_copy_passive_node_style(self, node_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_copy_passive_node_style(node_id))

    def request_paste_passive_node_style(self, node_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_paste_passive_node_style(node_id))

    def request_propagate_passive_node_style(self, node_id: str) -> bool:
        return bool(self._host.shell_host_presenter.request_propagate_passive_node_style(node_id))

    def request_rename_node(self, node_id: str) -> bool:
        result = self._host.workspace_library_controller.request_rename_node(node_id)
        return bool(result.payload)

    def request_ungroup_node(self, node_id: str) -> bool:
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return False
        self._host.scene.select_node(normalized_node_id)
        return bool(self._host.workspace_library_controller.ungroup_selected_nodes())

    def request_remove_node(self, node_id: str) -> bool:
        result = self._host.workspace_library_controller.request_remove_node(node_id)
        return bool(result.payload)


__all__ = ["GraphCanvasHostPresenter"]
