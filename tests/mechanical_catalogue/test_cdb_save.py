# Purpose: Prove CDB Save source selection, isolated staging, receipts, controls, and rollback without native Ansys.
# Map: subsystems/addons.md
# Tests: this file
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from ea_node_editor.addons.mechanical import backend as backend_module
from ea_node_editor.addons.mechanical import cdb_export, runtime
from ea_node_editor.addons.mechanical.backend import MechanicalOwnerBackend
from ea_node_editor.addons.mechanical.owner_process import OwnerOperationError, OwnerProtocolError
from ea_node_editor.addons.mechanical.session import MechanicalSessionService, StaleMechanicalModelError
from ea_node_editor.addons.mechanical.contracts import (
    catalogue_table, encode_selector, model_handle, object_value,
)
from ea_node_editor.addons.mechanical.property_edit import (
    MechanicalPropertyEditAdapter, _catalogue_index,
)
from ea_node_editor.addons.mechanical.saving import (
    create_save_staging, preflight_save_destination, publish_save,
    resolve_save_format, save_receipt_message, validate_staged_bundle,
)
from ea_node_editor.addons.property_edit_adapters import PropertyEditAdapterContext
from ea_node_editor.execution.worker_services import WorkerServices
from tests.mechanical_catalogue import test_standalone_save as standalone
from tests.mechanical_catalogue import test_workbench_model_export as workbench
from tests.mechanical_catalogue.test_cdb_export import _component, _native_text, _receipt
from tests.mechanical_catalogue.test_contracts import _row


def _object(model, *, object_id=17, name="Static Structural", path="Project/Model/Static Structural", **changes):
    metadata = model.metadata
    payload = {
        **{key: metadata[key] for key in (
            "run_id", "session_id", "document_id", "source_key", "system_key", "model_revision"
        )},
        "object_id": object_id, "parent_id": None, "analysis_id": object_id,
        "object_path": path, "display_name": name,
        "api_type": "Ansys.ACT.Automation.Mechanical.Analysis", "category": "Analysis",
        **changes,
    }
    payload["selector_code"] = encode_selector(
        "object", document_id=payload["document_id"], system_key=payload["system_key"],
        object_path=payload["object_path"], native_id=payload["object_id"],
    )
    return object_value(payload)


def _setup(tmp_path, monkeypatch, *, suffix="mechdb", **properties):
    source = tmp_path / ("source." + suffix)
    source.write_bytes(b"original-source")
    is_workbench = suffix in {"wbpj", "wbpz"}
    base = workbench if is_workbench else standalone
    original = base._model()

    class Sessions(base._Sessions):
        def operate(self, session, **kwargs):
            if kwargs["operation"] == "cdb_source_preflight":
                self.calls.append(kwargs)
                assert kwargs["mutation"] is False
                assert kwargs["expected_revision"] == 2
                return {"analysis": {"ordinal": 3, "name": "Static Structural"}}
            response = super().operate(session, **kwargs)
            args = kwargs["args"]
            frame = response["catalogue"].to_pandas()
            rows = frame.astype(object).where(frame.notna(), None).to_dict("records")
            rows[0].update(args["catalogue_identity"])
            operation = _row(
                **args["catalogue_identity"], record_kind="operation",
                omitted_rows=None, catalogue_complete=None,
            )
            operation.update(save_receipt_message(
                destination=Path(args["destination_path"]), source=source,
                format_code="mechdb", files=[Path(p) for p in args["files"]],
                overwrite=args["overwrite"], archive_policy=None,
            ))
            response["catalogue"] = catalogue_table([*rows, operation])
            return response

        def register_model(self, session, **kwargs):
            return model_handle(
                handle_id=str(uuid4()), owner_scope="run-1", worker_generation=1,
                metadata={
                    **original.metadata, **kwargs, "model_revision": session.revision,
                    "connection_generation": getattr(session, "connection_generation", 0),
                },
            )

    sessions = Sessions(tmp_path, source)
    destination = tmp_path / "result.cdb"
    ctx, invalidations = base._context(tmp_path, sessions, destination, **properties)
    owners = []
    helper_calls = []

    def helper(**kwargs):
        helper_calls.append(kwargs)
        assert kwargs["work_root"].parent.is_dir()
        assert not kwargs["work_root"].exists()
        assert kwargs["snapshot_path"].is_file()
        assert not kwargs["stage_path"].exists()
        kwargs["work_root"].mkdir()
        physics = f"MP,EX,1,200000\nF,2,FX,{kwargs['load_step']}\n" if kwargs["content"] == "full" else ""
        kwargs["stage_path"].write_text(_native_text(component=_component(), physics=physics))
        receipt = _receipt(kwargs["stage_path"], content=kwargs["content"])
        receipt["analysis"] = {**kwargs["analysis"], "object_path": kwargs["analysis"]["name"]}
        if kwargs["content"] == "full":
            receipt.update(load_step=kwargs["load_step"], step_time=float(kwargs["load_step"]))
        return receipt

    class Owner:
        def __init__(self, *, work_root):
            self.work_root = Path(work_root)
            self.work_root.mkdir()
            self.calls = []
            self.closed = False
            owners.append(self)

        def request(self, **kwargs):
            self.calls.append(kwargs)
            assert kwargs["expected_revision"] == 0
            assert kwargs["timeout_sec"] == 600.0
            args = kwargs["args"]
            if kwargs["operation"] == "convert_workbench_model":
                stage = Path(args["stage_path"])
                stage.write_bytes(b"native-snapshot")
                Path(args["stage_companion"]).mkdir()
                return {"status": "converted", "native_save": {
                    "schema_version": 1, "marker": "corex-workbench-model-export-v1",
                    "format": "mechdb", "reopen_verified": True, "source_workbench_preserved": True,
                    "bridge_bytes": args["bridge_bytes"], "stage_bytes": stage.stat().st_size,
                    "tree_object_count": 6, "analysis_count": 3, "body_count": 1,
                    "definition_count": 1, "setting_count": 1, "scope_count": 1,
                    "snippet_count": 0, "camera_count": 0,
                }}
            assert kwargs["operation"] == "export_cdb_snapshot"
            assert all(owner.closed for owner in owners[:-1])
            return MechanicalOwnerBackend().execute(kwargs["operation"], args)

        def close(self):
            self.closed = True

    monkeypatch.setattr(runtime, "MechanicalOwnerProcess", Owner)
    monkeypatch.setattr(cdb_export, "export_cdb_snapshot", helper)
    return SimpleNamespace(
        source=source, destination=destination, ctx=ctx, sessions=sessions, model=original,
        owners=owners, helper_calls=helper_calls, invalidations=invalidations,
    )


@pytest.mark.parametrize("suffix", ["mechdb", "mechdat", "mechpz", "wbpj", "wbpz"])
@pytest.mark.parametrize("content,step", [("mesh", object()), ("full", 1), ("full", 3)])
def test_save_exports_one_cdb_and_preserves_fresh_source_identity(tmp_path, monkeypatch, suffix, content, step):
    case = _setup(tmp_path, monkeypatch, suffix=suffix, cdb_content=content, cdb_load_step=step,
                  include_results=object(), include_user_files=object(), include_external_imported_files=object())
    result = runtime.execute_save_model(case.ctx, case.model)
    assert result["files"] == [str(case.destination)]
    assert result["model"].metadata["model_revision"] == 3
    assert result["model"].metadata["connection_generation"] == (
        5 if suffix in {"wbpj", "wbpz"} else 0
    )
    for key in ("run_id", "session_id", "document_id", "source_key", "system_key", "release_code"):
        assert result["model"].metadata[key] == case.model.metadata[key]
    assert [call["mutation"] for call in case.sessions.calls] == [False, True]
    snapshot = case.sessions.calls[1]
    assert snapshot["args"]["format"] == "mechdb"
    assert not {"include_results", "include_user_files", "include_external_imported_files"} & snapshot["args"].keys()
    assert all(owner.closed for owner in case.owners)
    assert len(case.owners) == (2 if suffix in {"wbpj", "wbpz"} else 1)
    assert case.invalidations == [("open-1", "mechanical_model_mutated")]
    assert case.source.read_bytes() == b"original-source"
    report = result["report"].to_pandas()
    summary = report.iloc[0]
    assert summary["catalogue_id"] == result["model"].metadata["catalogue_id"]
    assert summary["producer_port"] == "report"
    message = json.loads(report[report.record_kind == "operation"].iloc[0]["message"])
    assert message["format"] == "cdb" and message["destination"] == str(case.destination)
    assert message["files"] == result["files"]
    assert message["cdb"]["analysis"] == {"ordinal": 3, "name": "Static Structural", "object_path": "Static Structural"}
    assert message["cdb"]["load_step"] == (step if content == "full" else None)
    cdb_export.validate_cdb_receipt(message["cdb"], stage_path=case.destination)
    assert not list(tmp_path.glob(".corex-cdb-*"))
    with pytest.raises(ValueError, match="stale"):
        runtime.execute_save_model(case.ctx, case.model)


@pytest.mark.parametrize("selector_kind", ["typed", "picker", "text", "blank"])
def test_runtime_preflights_source_selector_before_snapshot_mutation(tmp_path, monkeypatch, selector_kind):
    case = _setup(tmp_path, monkeypatch)
    typed = _object(case.model)
    selector = {"typed": typed, "picker": typed.payload["selector_code"], "text": "Project/Model/Static Structural", "blank": ""}[selector_kind]
    case.ctx.properties["cdb_analysis"] = selector
    runtime.execute_save_model(case.ctx, case.model)
    submitted = case.sessions.calls[0]["args"]["selector"]
    if selector_kind in {"typed", "picker"}:
        assert submitted == {"kind": "typed", "object_id": 17, "object_path": "Project/Model/Static Structural"}
    assert case.helper_calls[0]["analysis"] == {"ordinal": 3, "name": "Static Structural"}


@pytest.mark.parametrize("field,value", [("model_revision", 999), ("run_id", "other"), ("session_id", "other"), ("analysis_id", 999)])
def test_typed_analysis_rejected_against_original_model_before_any_owner_call(tmp_path, monkeypatch, field, value):
    case = _setup(tmp_path, monkeypatch)
    case.ctx.properties["cdb_analysis"] = _object(case.model, **{field: value})
    with pytest.raises(ValueError):
        runtime.execute_save_model(case.ctx, case.model)
    assert not case.sessions.calls and not case.owners


@pytest.mark.parametrize("properties", [
    {"cdb_content": "invalid"}, {"cdb_analysis": []},
    {"cdb_content": "full", "cdb_load_step": True},
    {"cdb_content": "full", "cdb_load_step": 0},
    {"cdb_content": "full", "cdb_load_step": 1.5},
])
def test_invalid_active_controls_fail_before_native_staging(tmp_path, monkeypatch, properties):
    case = _setup(tmp_path, monkeypatch, **properties)
    with pytest.raises((ValueError, TypeError)):
        runtime.execute_save_model(case.ctx, case.model)
    assert not case.sessions.calls and not case.owners


def test_non_cdb_save_ignores_all_cdb_controls(tmp_path):
    source = tmp_path / "source.mechdb"
    source.write_bytes(b"source")
    sessions = standalone._Sessions(tmp_path, source)
    ctx, _ = standalone._context(tmp_path, sessions, tmp_path / "result.mechdb",
                                 cdb_content=object(), cdb_analysis=object(), cdb_load_step=object())
    runtime.execute_save_model(ctx, standalone._model())
    assert len(sessions.calls) == 1 and sessions.calls[0]["operation"] == "standalone_save"


def test_overwrite_refusal_precedes_source_preflight(tmp_path, monkeypatch):
    case = _setup(tmp_path, monkeypatch)
    case.destination.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        runtime.execute_save_model(case.ctx, case.model)
    assert not case.sessions.calls and case.destination.read_bytes() == b"original"


@pytest.mark.parametrize("failure", ["helper", "timeout", "cancel", "receipt", "snapshot", "report", "encoding", "registration"])
def test_failures_close_owner_and_preserve_existing_destination(tmp_path, monkeypatch, failure):
    case = _setup(tmp_path, monkeypatch, overwrite=True)
    case.destination.write_bytes(b"original")
    helper = cdb_export.export_cdb_snapshot
    cancelled = [False]
    monkeypatch.setattr(type(case.ctx), "should_stop", lambda _ctx: cancelled[0])

    def failing_helper(**kwargs):
        if failure in {"helper", "timeout"}:
            raise (TimeoutError("test timeout") if failure == "timeout" else RuntimeError("test native failure"))
        receipt = helper(**kwargs)
        if failure == "cancel":
            cancelled[0] = True
        if failure == "receipt":
            receipt["physics_sha256"] = "0" * 64
        return receipt

    monkeypatch.setattr(cdb_export, "export_cdb_snapshot", failing_helper)
    original_operate = case.sessions.operate

    def operate(session, **kwargs):
        response = original_operate(session, **kwargs)
        if kwargs["mutation"]:
            if failure == "snapshot":
                response["native_save"]["reopen_verified"] = False
            if failure == "report":
                response["catalogue"] = catalogue_table([_row()])
        return response

    monkeypatch.setattr(case.sessions, "operate", operate)
    if failure in {"encoding", "registration"}:
        def fail(*_args, **_kwargs):
            raise RuntimeError("test output failure")
        monkeypatch.setattr(runtime if failure == "encoding" else case.sessions,
                            "serialize_runtime_value" if failure == "encoding" else "register_model", fail)
    with pytest.raises((RuntimeError, ValueError)):
        runtime.execute_save_model(case.ctx, case.model)
    assert case.destination.read_bytes() == b"original"
    assert case.source.read_bytes() == b"original-source"
    assert all(owner.closed for owner in case.owners)
    assert case.sessions.session.revision == 3
    if failure == "snapshot":
        assert not case.owners


def test_source_native_preflight_uses_overall_analysis_order_and_original_tree_paths(tmp_path, monkeypatch):
    original = standalone._model()
    values = [
        _object(original, object_id=11, name="Modal", path="Project/Model/Modal"),
        _object(original, object_id=17, name="Static Structural", path="Project/Model/A"),
        _object(original, object_id=22, name="Static Structural", path="Project/Model/B"),
    ]
    analyses = [SimpleNamespace(ObjectId=11, Name="Modal", AnalysisType="Modal", PhysicsType="Mechanical"),
                SimpleNamespace(ObjectId=17, Name="Static Structural", AnalysisType="Static", PhysicsType="Mechanical"),
                SimpleNamespace(ObjectId=22, Name="Static Structural", AnalysisType="Static", PhysicsType="Mechanical")]
    backend = MechanicalOwnerBackend()
    backend.source_path = tmp_path / "source.mechdb"
    backend.work_path = tmp_path / "work.mechdb"
    backend.work_root = tmp_path
    backend.release_code = 261
    backend.tree = SimpleNamespace(AllObjects=[])
    backend.model = SimpleNamespace(Analyses=analyses)
    backend.app = standalone._NativeApp({"Model": backend.model})
    monkeypatch.setattr(backend_module, "search_tree", lambda **_kwargs: {"objects": values})
    args = {
        "source_path": str(backend.source_path), "work_path": str(backend.work_path),
        "identity": {key: original.metadata[key] for key in (
            "run_id", "session_id", "document_id", "source_key", "system_key", "model_revision"
        )},
        "selector": {"kind": "typed", "object_id": 22, "object_path": "Project/Model/B"},
    }
    assert backend.execute("cdb_source_preflight", args) == {"analysis": {"ordinal": 3, "name": "Static Structural"}}
    for selector in (None, {"kind": "text", "text": "Static Structural"},
                     {"kind": "typed", "object_id": 22, "object_path": "Project/Model/A"},
                     {"kind": "text", "text": "Project/Model/Modal"}):
        with pytest.raises(ValueError, match="eligible"):
            backend.execute("cdb_source_preflight", {**args, "selector": selector})
    backend.model.Analyses.pop()
    assert backend.execute("cdb_source_preflight", {**args, "selector": None}) == {
        "analysis": {"ordinal": 2, "name": "Static Structural"}
    }


def test_cdb_publication_requires_native_receipt_and_preserves_archive_validation(tmp_path):
    source = tmp_path / "source.mechdb"
    source.write_bytes(b"source")
    destination = tmp_path / "result.cdb"
    assert resolve_save_format(destination, "auto") == "cdb"
    with pytest.raises(ValueError, match="agree"):
        resolve_save_format(destination, "mechdb")
    staging = create_save_staging(destination, "cdb")
    staging.primary.write_text(_native_text())
    preflight = preflight_save_destination(destination, source=source, format_code="cdb", overwrite=False)
    with pytest.raises(ValueError, match="receipt"):
        publish_save(staging, preflight=preflight, format_code="cdb")
    with pytest.raises(RuntimeError, match="archive"):
        validate_staged_bundle(staging, format_code="mechpz")
    receipt = _receipt(staging.primary)
    transaction = publish_save(staging, preflight=preflight, format_code="cdb", cdb_receipt=receipt)
    transaction.commit()
    assert destination.is_file()


def test_cdb_conditions_follow_connected_format_file_and_content(tmp_path):
    properties = {"format": "mechdb", "file": "old.mechdb", "cdb_content": "mesh",
                  "cdb_analysis": "", "cdb_load_step": 1, "include_results": True}
    values = {"format": "auto", "file": "result.cdb", "cdb_content": "full"}
    context = PropertyEditAdapterContext(
        node=SimpleNamespace(node_id="save", type_id="mechanical.save_model", properties=properties),
        workspace_edges=[SimpleNamespace(target_node_id="save", target_port_key=key,
                                         source_node_id="source", source_port_key=key, enabled=True) for key in values],
        current_output_provider=lambda _node, key: values.get(key),
    )
    adapter = MechanicalPropertyEditAdapter()
    items = [{"key": key, "editor_enabled": True, "condition_enabled": True} for key in properties]
    projected = {item["key"]: item for item in adapter.build_property_items(context, items)}
    assert projected["cdb_load_step"]["condition_enabled"]
    assert not projected["include_results"]["condition_enabled"]
    values["cdb_content"] = "mesh"
    projected = {item["key"]: item for item in adapter.build_property_items(context, items)}
    assert not projected["cdb_load_step"]["condition_enabled"]
    assert projected["cdb_analysis"]["condition_enabled"]
    values["file"] = "result.mechdb"
    projected = {item["key"]: item for item in adapter.build_property_items(context, items)}
    assert all(not projected[key]["condition_enabled"] for key in ("cdb_content", "cdb_analysis", "cdb_load_step"))


def test_picker_indexes_only_accepted_analysis_rows():
    identity = _row(catalogue_id=str(uuid4()), system_key="standalone")
    analysis = _row(catalogue_id=identity["catalogue_id"], record_kind="object", object_id=17,
                    analysis_id=17, object_path="Model/A", display_name="A",
                    api_type="Ansys.ACT.Automation.Mechanical.Analysis", system_key="standalone",
                    omitted_rows=None, catalogue_complete=None)
    analysis["selector_code"] = encode_selector(
        "object", document_id=analysis["document_id"], system_key=analysis["system_key"],
        object_path=analysis["object_path"], native_id=17,
    )
    body = {**analysis, "object_id": 18, "analysis_id": None, "api_type": "Body", "display_name": "Body"}
    body["selector_code"] = encode_selector(
        "object", document_id=body["document_id"], system_key=body["system_key"],
        object_path=body["object_path"], native_id=18,
    )
    rows = [identity, analysis, body]
    index = _catalogue_index(catalogue_table(rows), rows)
    assert [code for code, _label in index.rows_by_kind["analysis"]] == [analysis["selector_code"]]


@pytest.mark.parametrize("field,value", [("ordinal", 2), ("name", "Another analysis"), ("load_step", 2)])
def test_closed_receipt_must_also_match_requested_analysis_and_step(tmp_path, monkeypatch, field, value):
    case = _setup(tmp_path, monkeypatch, cdb_content="full", cdb_load_step=1)
    helper = cdb_export.export_cdb_snapshot

    def mismatched(**kwargs):
        receipt = helper(**kwargs)
        if field == "load_step":
            receipt[field] = value
        else:
            receipt["analysis"][field] = value
        return receipt

    monkeypatch.setattr(cdb_export, "export_cdb_snapshot", mismatched)
    with pytest.raises(RuntimeError, match="requested export"):
        runtime.execute_save_model(case.ctx, case.model)
    assert not case.destination.exists() and all(owner.closed for owner in case.owners)


@pytest.mark.parametrize("suffix", ["mechdb", "wbpj"])
def test_unicode_destination_keeps_original_paths_through_publication(tmp_path, monkeypatch, suffix):
    root = tmp_path / "unicode-\u03a9"
    root.mkdir()
    case = _setup(root, monkeypatch, suffix=suffix)
    result = runtime.execute_save_model(case.ctx, case.model)
    assert result["files"] == [str(case.destination)]
    assert case.helper_calls[0]["stage_path"].is_relative_to(root)
    assert case.source.read_bytes() == b"original-source"


def test_native_rmod_spelling_is_not_admitted_in_user_commands():
    cdb_export.validate_no_solve("RMOD,tid,3,10.")
    with pytest.raises(ValueError):
        cdb_export.validate_no_solve("RMOD,tid,3,10.", user_snippet=True)


@pytest.mark.parametrize("args", [{}, {"run_mapdl": "forbidden"}, {"release_code": 262}])
def test_export_owner_operation_rejects_unapproved_schema_before_native_import(args):
    with pytest.raises(ValueError, match="fresh qualified owner"):
        MechanicalOwnerBackend().execute("export_cdb_snapshot", args)


def _real_failure_case(tmp_path, monkeypatch, *, phase, error_type, suffix="mechdb", destination_format="cdb"):
    source = tmp_path / f"source.{suffix}"
    source.write_bytes(b"original source")
    callbacks = []

    class Owner:
        alive = True
        close_calls = 0
        stage = None

        def request(self, **request):
            if request["operation"] == "cdb_source_preflight":
                if phase == "preflight":
                    raise error_type("analysis selection is missing or ambiguous")
                return {"analysis": {"ordinal": 1, "name": "Static Structural"}}
            assert request["operation"] in {"standalone_save", "workbench_model_export"}
            args = request["args"]
            self.stage = Path(args["stage_path"])
            self.stage.write_bytes(b"partial native snapshot")
            Path(args["stage_companion"]).mkdir()
            raise error_type("source snapshot failed")

        def close(self):
            self.close_calls += 1
            self.alive = False

    owner = Owner()
    services = WorkerServices()
    services.bind_data_types(standalone.SAVE_DATA_TYPES)
    service = MechanicalSessionService(services, owner_factory=lambda: owner)
    session = service.open_session(
        run_id="run-1", workspace_id="workspace-1", open_node_id="open-1",
        source_path=source, working_folder=tmp_path / "working", register_cancel=callbacks.append,
    )
    session.work_path.write_bytes(b"unsaved working model edits")
    results = session.work_root / "retained-results.rst"
    results.write_bytes(b"existing results")
    source_stage = session.work_root / "earlier-snapshot.mechdb"
    source_stage.write_bytes(b"earlier staged snapshot")
    model = service.register_model(
        session, document_id="document", source_key="source", system_key="SYS" if suffix == "wbpj" else "standalone",
        release_code=261, catalogue_id=str(uuid4()),
    )
    destination = tmp_path / f"result.{destination_format}"
    destination.write_bytes(b"existing destination")
    ctx, invalidations = standalone._context(tmp_path, service, destination, overwrite=True)

    def unexpected_owner(**_kwargs):
        pytest.fail("source rejection must not create a conversion or export owner")

    monkeypatch.setattr(runtime, "MechanicalOwnerProcess", unexpected_owner)
    return SimpleNamespace(
        owner=owner, service=service, session=session, model=model, ctx=ctx,
        source=source, source_stage=source_stage, results=results,
        destination=destination, callbacks=callbacks, invalidations=invalidations,
    )


@pytest.mark.parametrize("suffix", ["mechdb", "wbpj"])
@pytest.mark.parametrize("phase", ["preflight", "snapshot"])
@pytest.mark.parametrize("error_type", [OwnerOperationError, OwnerProtocolError, TimeoutError])
def test_real_session_cdb_rejection_and_uncertain_retirement_preserve_recovery(
    tmp_path, monkeypatch, suffix, phase, error_type,
):
    case = _real_failure_case(tmp_path, monkeypatch, phase=phase, error_type=error_type, suffix=suffix)
    expected_rejection = phase == "preflight" and error_type is OwnerOperationError
    with pytest.raises(ValueError if expected_rejection else RuntimeError) as raised:
        runtime.execute_save_model(case.ctx, case.model)
    assert case.session.work_path.read_bytes() == b"unsaved working model edits"
    assert case.results.read_bytes() == b"existing results"
    assert case.source_stage.read_bytes() == b"earlier staged snapshot"
    assert case.source.read_bytes() == b"original source"
    assert case.destination.read_bytes() == b"existing destination"
    assert case.session.revision == (1 if phase == "snapshot" else 0)
    assert case.invalidations == ([("open-1", "mechanical_model_mutated")] if phase == "snapshot" else [])
    if phase == "snapshot":
        assert case.owner.stage.read_bytes() == b"partial native snapshot"
        assert "recovery_path=" in str(raised.value)
    if expected_rejection:
        assert case.owner.alive and case.owner.close_calls == 0
        assert not case.session.terminal and not case.session.closed
        assert case.service.admit_model(case.model, run_id="run-1", workspace_id="workspace-1") is case.session
        case.service.reset()
    else:
        assert not case.owner.alive and case.owner.close_calls == 1
        assert case.session.terminal and case.session.closed and case.session.retain_work_root
        assert f"source_recovery_path={case.session.work_root}" in str(raised.value)
        with pytest.raises(StaleMechanicalModelError):
            case.service.admit_model(case.model, run_id="run-1", workspace_id="workspace-1")
        case.callbacks[0]()
        case.service.cleanup_run("run-1")
        case.service.reset()
        assert case.session.work_path.read_bytes() == b"unsaved working model edits"
        assert case.source_stage.read_bytes() == b"earlier staged snapshot"
        if phase == "snapshot":
            assert case.owner.stage.read_bytes() == b"partial native snapshot"


def test_non_cdb_uncertain_retirement_keeps_existing_cleanup_policy(tmp_path, monkeypatch):
    case = _real_failure_case(
        tmp_path, monkeypatch, phase="snapshot", error_type=OwnerOperationError, destination_format="mechdb",
    )
    with pytest.raises(RuntimeError, match="operation_uncertain"):
        runtime.execute_save_model(case.ctx, case.model)
    assert not case.owner.alive and case.session.closed
    assert not case.session.retain_work_root and not case.session.work_root.exists()
    assert case.source.read_bytes() == b"original source"
    assert case.owner.stage.read_bytes() == b"partial native snapshot"


def test_cdb_recovery_retention_survives_a_failed_owner_close_and_later_callback(tmp_path, monkeypatch):
    case = _real_failure_case(tmp_path, monkeypatch, phase="preflight", error_type=OwnerProtocolError)
    close = case.owner.close
    attempts = []

    def close_once_failed():
        attempts.append(True)
        if len(attempts) == 1:
            raise RuntimeError("test close failure")
        close()

    monkeypatch.setattr(case.owner, "close", close_once_failed)
    with pytest.raises(RuntimeError, match="session retirement failed"):
        runtime.execute_save_model(case.ctx, case.model)
    assert case.session.retain_work_root and not case.session.closed
    assert case.session.work_path.read_bytes() == b"unsaved working model edits"
    case.callbacks[0]()
    assert case.session.closed and not case.owner.alive
    assert case.session.work_path.read_bytes() == b"unsaved working model edits"
    assert case.source_stage.read_bytes() == b"earlier staged snapshot"
