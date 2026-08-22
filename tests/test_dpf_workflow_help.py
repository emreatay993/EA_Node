from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ea_node_editor.addons.ansys_dpf import operator_docs as addon_operator_docs
from ea_node_editor.help.dpf_operator_docs import (
    is_dpf_help_type_id,
    is_dpf_operator_type_id,
    is_dpf_workflow_type_id,
    markdown_for_node,
    markdown_for_type_id,
    markdown_path_for_type_id,
)

_CURATED_WORKFLOW_TYPE_IDS = (
    "dpf.workflow.result_source",
    "dpf.workflow.result_fields",
    "dpf.workflow.result_viewer",
    "dpf.workflow.min_max_envelope",
    "dpf.workflow.time_history_probe",
    "dpf.workflow.stress_invariants",
    "dpf.workflow.mode_shape_viewer",
    "dpf.workflow.field_math",
    "dpf.workflow.table_export",
)
_REQUIRED_SECTIONS = (
    "## Use this when",
    "## Required wiring",
    "## Defaults",
    "## Outputs",
    "## If it fails",
    "## Mini recipe",
)


class _RegistryStub:
    def __init__(self, specs: dict[str, object] | None = None) -> None:
        self._specs = specs or {}

    def spec_or_none(self, type_id: str) -> object | None:
        return self._specs.get(type_id)


def test_all_curated_dpf_workflows_have_complete_help_pages() -> None:
    lookup = _RegistryStub()
    packaged_docs_root = Path(addon_operator_docs.__file__).resolve().with_name("workflow_docs")

    for type_id in _CURATED_WORKFLOW_TYPE_IDS:
        path = markdown_path_for_type_id(type_id, lookup)  # type: ignore[arg-type]
        assert path is not None and path.is_file(), type_id
        assert path.parent == packaged_docs_root, type_id
        markdown = markdown_for_type_id(type_id, lookup)  # type: ignore[arg-type]
        assert markdown is not None, type_id
        assert markdown.startswith("# DPF "), type_id
        for section in _REQUIRED_SECTIONS:
            assert section in markdown, f"{type_id} is missing {section}"


def test_curated_workflow_ids_join_operator_ids_in_dpf_help_routing() -> None:
    for type_id in _CURATED_WORKFLOW_TYPE_IDS:
        assert is_dpf_workflow_type_id(type_id)
        assert is_dpf_help_type_id(type_id)
        assert not is_dpf_operator_type_id(type_id)

    assert is_dpf_help_type_id("dpf.op.result.displacement")
    assert not is_dpf_help_type_id("core.logger")
    assert not is_dpf_workflow_type_id("dpf.workflow.unknown")


def test_selected_curated_workflow_node_resolves_through_shared_lookup() -> None:
    type_id = "dpf.workflow.result_fields"
    spec = SimpleNamespace(type_id=type_id, display_name="DPF Result Fields")
    registry = _RegistryStub({type_id: spec})
    workspace = SimpleNamespace(nodes={"node-1": SimpleNamespace(type_id=type_id)})
    host = SimpleNamespace(
        active_workspace_id="workspace-1",
        model=SimpleNamespace(
            project=SimpleNamespace(workspaces={"workspace-1": workspace}),
        ),
        registry=registry,
    )

    resolved = markdown_for_node(host, "node-1")

    assert resolved is not None
    markdown, resolved_type_id, display_name = resolved
    assert markdown.startswith("# DPF Result Fields")
    assert resolved_type_id == type_id
    assert display_name == "DPF Result Fields"
