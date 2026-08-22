from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.jupyter_notebook import JUPYTER_NOTEBOOK_TYPE_ID
from ea_node_editor.persistence.artifact_refs import STAGED_ARTIFACT_REF_SCHEME
from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.ui.shell.host_presenter import ShellHostPresenter
from ea_node_editor.ui_qml.jupyter_server_bridge import JupyterServerBridge


class _FakeWorkspaceManager:
    def __init__(self, workspace_id: str) -> None:
        self._workspace_id = workspace_id

    def active_workspace_id(self) -> str:
        return self._workspace_id


class _FakeScene:
    def selected_node_id(self) -> str:
        return ""


class _FakeProjectSessionController:
    def __init__(self, store: ProjectArtifactStore, temporary_root_parent: Path) -> None:
        self._store = store
        self._temporary_root_parent = temporary_root_parent

    def ensure_project_staging_root(self) -> Path:
        # Mirrors the real controller: this also records the staging-root hint in
        # the store metadata so staged refs resolve back to the same location.
        return self._store.ensure_staging_root(temporary_root_parent=self._temporary_root_parent)

    def project_artifact_store(self) -> ProjectArtifactStore:
        return self._store


class _FakeHost(QObject):
    project_meta_changed = pyqtSignal()

    def __init__(self, *, model, registry, workspace_manager, scene, controller, project_path) -> None:  # noqa: ANN001
        super().__init__()
        self.model = model
        self.registry = registry
        self.workspace_manager = workspace_manager
        self.scene = scene
        self.project_session_controller = controller
        self.project_path = project_path


def test_host_presenter_stages_blank_notebook_resolving_to_valid_ipynb(qapp, tmp_path) -> None:  # noqa: ANN001
    import nbformat

    registry = build_default_registry()
    model = GraphModel()
    workspace = model.active_workspace
    node = model.add_node(
        workspace.workspace_id,
        JUPYTER_NOTEBOOK_TYPE_ID,
        "Analysis Notebook",
        10.0,
        20.0,
        properties=registry.default_properties(JUPYTER_NOTEBOOK_TYPE_ID),
    )

    project_path = tmp_path / "project.cxproj"
    store = ProjectArtifactStore(project_path=project_path)
    host = _FakeHost(
        model=model,
        registry=registry,
        workspace_manager=_FakeWorkspaceManager(workspace.workspace_id),
        scene=_FakeScene(),
        controller=_FakeProjectSessionController(store, tmp_path / "session"),
        project_path=str(project_path),
    )
    presenter = ShellHostPresenter(host)

    ref = presenter.create_blank_managed_notebook(node.node_id, kernel_name="python3")

    assert ref.startswith(f"{STAGED_ARTIFACT_REF_SCHEME}://")
    # The staged ref is recorded in project metadata (so it persists on save).
    resolved = ProjectArtifactResolver(
        project_path=str(project_path),
        project_metadata=dict(model.project.metadata),
    ).resolve_to_path(ref)
    assert resolved is not None and Path(resolved).is_file()
    assert Path(resolved).suffix == ".ipynb"
    notebook = nbformat.read(str(resolved), as_version=4)
    assert notebook.nbformat == 4
    assert notebook.metadata["kernelspec"]["name"] == "python3"


class _FakePresenterHost:
    class _Presenter:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def create_blank_managed_notebook(self, node_id: str = "", *, kernel_name: str = "") -> str:
            self.calls.append((node_id, kernel_name))
            return "temp://created_notebook"

    def __init__(self) -> None:
        self.shell_host_presenter = self._Presenter()


def test_bridge_create_blank_emits_notebook_ref_assigned(qapp) -> None:  # noqa: ANN001
    host = _FakePresenterHost()
    bridge = JupyterServerBridge(shell_window=host)
    assigned: list[tuple[str, str]] = []
    failed: list[tuple[str, str]] = []
    bridge.notebookRefAssigned.connect(lambda node, ref: assigned.append((node, ref)))
    bridge.serverFailed.connect(lambda node, reason: failed.append((node, reason)))

    bridge.createBlankNotebook("node-create", "python3")

    assert not failed
    assert assigned == [("node-create", "temp://created_notebook")]
    assert host.shell_host_presenter.calls == [("node-create", "python3")]


def test_bridge_create_blank_without_presenter_reports_failure(qapp) -> None:  # noqa: ANN001
    bridge = JupyterServerBridge(shell_window=None)
    failed: list[tuple[str, str]] = []
    bridge.serverFailed.connect(lambda node, reason: failed.append((node, reason)))

    bridge.createBlankNotebook("node-x", "")

    assert failed and "project" in failed[-1][1].lower()
