from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import ea_node_editor.ui.shell.presenters.graph_canvas_host_presenter as presenter_module
from ea_node_editor.ui.shell.presenters.graph_canvas_host_presenter import GraphCanvasHostPresenter


class _RecordingTabularPreviewProvider:
    instances: list["_RecordingTabularPreviewProvider"] = []

    def __init__(self, *, project_context_provider: Any) -> None:
        self.project_context_provider = project_context_provider
        self.calls: list[tuple[Any, Any, str]] = []
        self.contexts: list[tuple[str | None, dict[str, Any] | None]] = []
        self.instances.append(self)

    def describe_preview(
        self,
        properties_or_source: Any,
        request: Any = None,
        *,
        mode: str = "inline",
    ) -> dict[str, Any]:
        self.calls.append((properties_or_source, request, mode))
        self.contexts.append(self.project_context_provider())
        return {"call_count": len(self.calls)}


def test_graph_canvas_host_presenter_reuses_tabular_preview_provider(monkeypatch) -> None:
    _RecordingTabularPreviewProvider.instances = []
    monkeypatch.setattr(
        presenter_module,
        "TabularPreviewProvider",
        _RecordingTabularPreviewProvider,
    )
    host = SimpleNamespace(
        project_path="C:/project/example.cxproj",
        model=SimpleNamespace(project=SimpleNamespace(metadata={"artifact_root": "assets"})),
        search_scope_controller=SimpleNamespace(),
        scene=SimpleNamespace(),
        shell_host_presenter=SimpleNamespace(),
        workspace_library_controller=SimpleNamespace(),
    )
    presenter = GraphCanvasHostPresenter(host)

    first = presenter.describe_tabular_preview({"source": "table.csv"}, {"row_limit": 50})
    second = presenter.describe_tabular_preview({"source": "table.csv"}, {"row_limit": 50})

    assert first == {"call_count": 1}
    assert second == {"call_count": 2}
    assert len(_RecordingTabularPreviewProvider.instances) == 1
    provider = _RecordingTabularPreviewProvider.instances[0]
    assert provider.calls == [
        ({"source": "table.csv"}, {"row_limit": 50}, "inline"),
        ({"source": "table.csv"}, {"row_limit": 50}, "inline"),
    ]
    assert provider.contexts == [
        ("C:/project/example.cxproj", {"artifact_root": "assets"}),
        ("C:/project/example.cxproj", {"artifact_root": "assets"}),
    ]


def test_graph_canvas_host_presenter_opens_local_file_sources(monkeypatch, tmp_path) -> None:
    host = SimpleNamespace(
        project_path="",
        model=SimpleNamespace(project=SimpleNamespace(metadata={})),
        search_scope_controller=SimpleNamespace(),
        scene=SimpleNamespace(),
        shell_host_presenter=SimpleNamespace(),
        workspace_library_controller=SimpleNamespace(),
    )
    presenter = GraphCanvasHostPresenter(host)
    mail_path = tmp_path / "message.eml"
    mail_path.write_text("Subject: Hello\n\nBody", encoding="utf-8")
    default_opened: list[object] = []
    chooser_opened: list[object] = []

    monkeypatch.setattr(
        presenter_module,
        "open_path_with_default_handler",
        lambda path: default_opened.append(path) or True,
    )
    monkeypatch.setattr(
        presenter_module,
        "open_path_with_app_chooser",
        lambda path: chooser_opened.append(path) or True,
    )

    default_result = presenter.open_local_file_source(str(mail_path), False)
    chooser_result = presenter.open_local_file_source(str(mail_path), True)
    missing_result = presenter.open_local_file_source(str(tmp_path / "missing.eml"), False)
    monkeypatch.setattr(presenter_module, "open_path_with_default_handler", lambda _path: False)
    failed_result = presenter.open_local_file_source(str(mail_path), False)

    assert default_result == {"success": True, "path": str(mail_path), "error": {}}
    assert chooser_result == {"success": True, "path": str(mail_path), "error": {}}
    assert missing_result["success"] is False
    assert missing_result["error"]["code"] == "missing_file"
    assert failed_result["success"] is False
    assert failed_result["error"]["code"] == "open_failed"
    assert default_opened == [mail_path]
    assert chooser_opened == [mail_path]
