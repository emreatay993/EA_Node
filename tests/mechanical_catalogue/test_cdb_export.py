# Purpose: Prove CDB parser, no-solve admission, selection, and staged-receipt boundaries.
# Map: subsystems/addons.md
# Tests: this file
from __future__ import annotations

import hashlib
import ctypes
from pathlib import Path
from types import SimpleNamespace

import pytest

from ea_node_editor.addons.mechanical import cdb_export as cdb


def _native_text(*, component: str = "", physics: str = "") -> str:
    types = "ETBLOCK,1,1\n(2i9,19a9)\n" + "".join(f"{v:9d}" for v in [1, 285, *([0] * 19)]) + "\n-1\n"
    nodes = "NBLOCK,6,SOLID,4,4\n(3i9,6e21.13e3)\n"
    for index, xyz in enumerate(((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)), 1):
        nodes += f"{index:9d}{0:9d}{0:9d}" + "".join(f"{v:21.13E}" for v in (*xyz, 0, 0, 0)) + "\n"
    nodes += "N,UNBL,LOC,       -1,\n"
    row = [1, 1, 0, 0, 0, 0, 0, 0, 4, 0, 1, 1, 2, 3, 4]
    elements = "EBLOCK,19,SOLID,1,1\n(19i9)\n" + "".join(f"{v:9d}" for v in row) + "\n-1\n"
    return "/UNITS,MPA\n/PREP7\n" + types + nodes + elements + component + physics + "FINISH\n"


def _component(name="BODY", values=(1, -4)):
    return f"CMBLOCK,{name},NODE,{len(values)}\n(8i10)\n" + "".join(f"{v:10d}" for v in values) + "\n"


def _receipt(path: Path, *, content="full"):
    text = path.read_text()
    mesh = cdb._mesh_data(text)
    physics = cdb._canonical_database(text) if content == "full" else tuple(cdb._support_definitions(text).splitlines())
    return {
        "schema_version": 1, "format": "cdb", "content": content,
        "analysis": {"ordinal": 1, "name": "Static Structural", "object_path": "Model/Static Structural"},
        "load_step": 1 if content == "full" else None, "step_time": 1.0 if content == "full" else None,
        "units": "MPA", "nodes": 4, "elements": 1, "components": sorted(mesh["components"]),
        "omitted_named_selections": [], "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mesh_sha256": cdb._digest(mesh),
        "physics_sha256": cdb._digest(physics), "native_readback": True,
        "numerical_solve": False, "remeshed": False, "release_code": 261,
    }


@pytest.mark.parametrize("command", ["SOLVE", "SOLV", "LSSOLVE,1,3", "*LSBAC,X,Y,Z", "my_macro",
                                     "/INPUT,hidden", "*USE,hidden", "F,1,FX,5$SOLVE", "UPGEOM,1"])
def test_generated_input_rejects_solves_and_indirect_execution(command):
    with pytest.raises(ValueError):
        cdb.validate_no_solve(command)


@pytest.mark.parametrize("command", ["x=UX(1)", "*SET,x,UX(1)", "*IF,UX(1),GT,0,THEN",
                                     "*GET,x,NODE,1,U,X", "*VGET,x,NODE,1,S,X", "*CREATE,macro"])
def test_user_snippets_reject_result_dependencies(command):
    with pytest.raises(ValueError):
        cdb.validate_no_solve(command, user_snippet=True)


def test_admits_definition_commands_and_native_numeric_blocks():
    cdb.validate_no_solve("! SOLVE is a comment\n/PREP7\nF,1,FX,25\n*SET,x,3", user_snippet=True)
    cdb.validate_no_solve(_native_text(component=_component()))


def test_native_mesh_parses_connectivity_and_compressed_components():
    mesh = cdb._mesh_data(_native_text(component=_component()))
    assert set(mesh["nodes"]) == {1, 2, 3, 4}
    assert mesh["elements"][1][11:] == (1, 2, 3, 4)
    assert mesh["components"] == {"BODY": ("NODE", (1, 2, 3, 4))}


@pytest.mark.parametrize("encoded", [(0,), (1, 1), (2, 1), (1, -1), (1, -8)])
def test_component_encoding_rejects_invalid_or_oversized_members(monkeypatch, encoded):
    monkeypatch.setattr(cdb, "MAX_COMPONENT_MEMBERS", 5)
    with pytest.raises(ValueError):
        cdb._mesh_data(_native_text(component=_component(values=encoded)))


def test_component_expansion_has_an_aggregate_budget(monkeypatch):
    monkeypatch.setattr(cdb, "MAX_COMPONENT_MEMBERS", 6)
    with pytest.raises(ValueError):
        cdb._mesh_data(_native_text(component=_component("A") + _component("B")))


def test_mesh_projection_drops_physics_and_keeps_element_support_definitions():
    definitions = "LOCAL,UNBL,LOC,12,0,0,0,0\nR,1,25\nSECTYPE,1,SHELL\nSECDATA,0.2,1\n"
    full = _native_text(component=_component(), physics=definitions + "MP,EX,1,200000\nD,1,ALL,0\nF,2,FX,500\n")
    geometry = "".join(block.text for block in cdb._blocks(_native_text()) if block.kind in {"NBLOCK", "EBLOCK"})
    projected = cdb._mesh_only(full, geometry, {"BODY"})
    assert "MP,EX" not in projected and "D,1,ALL" not in projected and "F,2,FX" not in projected
    assert cdb._support_definitions(projected) == definitions
    assert cdb._mesh_data(projected) == cdb._mesh_data(full)


def test_solver_component_detection_does_not_include_support_components():
    deck = "/COM,******** Send Named Selection as Node Component ********\nCMBLOCK,BODY,NODE,2\n(8i10)\n1 -4\n"
    deck += "/COM,******** Boundary conditions ********\nCMBLOCK,_FIXEDSU,NODE,1\n(8i10)\n1\n"
    assert cdb._named_components(deck) == {"BODY"}


def test_analysis_selection_is_exact_and_uses_stable_qualified_ordinal():
    parent = SimpleNamespace(ObjectId=1, Name="Model", Parent=None)
    def analysis(name, identity, physics="Mechanical"):
        return SimpleNamespace(Name=name, ObjectId=identity, Parent=parent, AnalysisType="Static", PhysicsType=physics)
    first, second = analysis("A", 10), analysis("B", 20)
    model = SimpleNamespace(Analyses=[first, analysis("Thermal", 15, "Thermal"), second])
    with pytest.raises(ValueError, match="ambiguous"):
        cdb.resolve_analysis(model)
    assert cdb.resolve_analysis(model, "Model/A")[0] is first
    assert cdb.resolve_analysis(model, {"ordinal": 3, "name": "B"})[0] is second
    with pytest.raises(ValueError):
        cdb.resolve_analysis(model, {"ordinal": 3, "name": "A"})


def test_staged_receipt_requires_matching_bytes_mesh_and_physics(tmp_path):
    path = tmp_path / "result.cdb"
    path.write_text(_native_text(component=_component(), physics="MP,EX,1,200000\n"))
    receipt = _receipt(path)
    assert cdb.validate_cdb_receipt(receipt, stage_path=path) == receipt
    bad = {**receipt, "physics_sha256": "0" * 64}
    with pytest.raises(ValueError, match="model definitions"):
        cdb.validate_cdb_receipt(bad, stage_path=path)
    path.write_text(path.read_text().replace("200000", "100000"))
    with pytest.raises(ValueError, match="native readback receipt"):
        cdb.validate_cdb_receipt(receipt, stage_path=path)


@pytest.mark.parametrize("field,value", [("schema_version", True), ("nodes", True), ("load_step", True),
                                       ("native_readback", False), ("numerical_solve", True),
                                       ("remeshed", True), ("step_time", float("nan")), ("release_code", 252)])
def test_receipt_rejects_unproved_or_invalid_claims(tmp_path, field, value):
    path = tmp_path / "result.cdb"
    path.write_text(_native_text())
    with pytest.raises(ValueError):
        cdb.validate_cdb_receipt({**_receipt(path), field: value})


def test_mesh_receipt_has_no_load_state(tmp_path):
    path = tmp_path / "result.cdb"
    path.write_text(_native_text())
    receipt = _receipt(path, content="mesh")
    cdb.validate_cdb_receipt(receipt, stage_path=path)
    with pytest.raises(ValueError, match="consume"):
        cdb.validate_cdb_receipt({**receipt, "load_step": 1})


def test_canonical_database_only_ignores_native_diagnostics_and_comments():
    first = "/COM,time1\nNLDIAG,EFLG,OFF\nMP,EX,1,200000\nD,1,UX,0\n"
    second = "/COM,time2\nMP,EX,1,200000\nD,1,UX,0\n"
    assert cdb._canonical_database(first) == cdb._canonical_database(second)
    assert cdb._canonical_database(second) != cdb._canonical_database(second.replace("UX", "UY"))


def test_export_preflight_rejects_invalid_paths_before_native_import(tmp_path):
    with pytest.raises(ValueError, match="staging paths"):
        cdb.export_cdb_snapshot(snapshot_path=tmp_path / "missing.mechdb",
                                stage_path=tmp_path / "result.cdb", work_root=tmp_path / "native")


@pytest.mark.parametrize("command", ["*GET,v,NODE,1,U,X", "*SET,v,UX(1)", "*IF,UX(1),GT,0,THEN"])
def test_generated_prefix_rejects_result_queries_too(command):
    with pytest.raises(ValueError):
        cdb.validate_no_solve(command)


def test_snippet_comment_cannot_truncate_validation_or_spoof_export_trailer():
    begin, end, trailer = "/COM,BEGIN_UNIQUE", "/COM,END_UNIQUE", "CDWRITE,DB,full,cdb\n"
    generated = "/COM,CDWRITE,DB,full,cdb\nSOLVE\n" + begin + "\n" + trailer + end + "\n"
    with pytest.raises(ValueError, match="SOLVE"):
        cdb._native_export_deck(generated, begin, end, trailer)
    with pytest.raises(RuntimeError, match="trailer"):
        cdb._native_export_deck(begin + "\nSOLVE\n" + trailer + end, begin, end, trailer)


def test_export_stops_before_unreachable_native_solution_tail():
    begin, end, trailer = "/COM,BEGIN_UNIQUE", "/COM,END_UNIQUE", "CDWRITE,DB,full,cdb\n"
    generated = "/PREP7\n" + begin + "\n" + trailer + end + "\nSOLVE\n"
    executable, prefix = cdb._native_export_deck(generated, begin, end, trailer)
    assert prefix == "/PREP7"
    assert "\nSOLVE\n" not in executable and executable.endswith("/EXIT,NOSAVE\n")


def test_user_snippet_cannot_spoof_a_solver_named_selection_heading():
    deck = "/COM,USER_BEGIN\n/COM,******** SEND NAMED SELECTION AS ********\nCM,INJECTED,NODE\n/COM,USER_END\n"
    deck += "/COM,******** SEND NAMED SELECTION AS ********\nCM,BODY,NODE\n"
    assert cdb._named_components(deck, {"/COM,USER_BEGIN": "/COM,USER_END"}) == {"BODY"}


@pytest.mark.parametrize("option", ["POST", "ADJUST", "MORPH", "TADJUST", "%option%"])
def test_partial_contact_solves_and_geometry_adjustments_are_rejected(option):
    with pytest.raises(ValueError, match="contact solves"):
        cdb.validate_no_solve("CNCHECK," + option)
    cdb.validate_no_solve("CNCHECK,DMP")


def test_receipt_units_are_bound_to_file(tmp_path):
    path = tmp_path / "result.cdb"
    path.write_text(_native_text())
    with pytest.raises(ValueError, match="units"):
        cdb.validate_cdb_receipt({**_receipt(path), "units": "SI"}, stage_path=path)


@pytest.mark.parametrize("nodes,elements,state", [(0, 0, "UpToDate"), (4, 1, "OutOfDate")])
def test_missing_or_stale_mesh_is_rejected_before_input_writer(tmp_path, nodes, elements, state):
    analysis = SimpleNamespace(Name="A", ObjectId=3, Parent=None, AnalysisType="Static", PhysicsType="Mechanical")
    model = SimpleNamespace(Analyses=[analysis], Mesh=SimpleNamespace(State=state))
    mesh = SimpleNamespace(NodeCount=nodes, ElementCount=elements)
    context = {"Model": model, "DataModel": SimpleNamespace(MeshDataByName=lambda name: mesh), "Tree": None}
    with pytest.raises(ValueError, match="up-to-date mesh"):
        cdb._prepare_input(context, tmp_path, content="full", selector="A", load_step=1)
    assert not (tmp_path / "input.dat").exists()


def test_only_qualified_scratch_local_connector_write_is_allowed():
    cdb.validate_no_solve("CEWRITE,file,ce,,INTE")
    cdb.validate_no_solve("/COM ******** comment without comma\n/EOF")
    with pytest.raises(ValueError, match="scratch-local"):
        cdb.validate_no_solve("CEWRITE,../outside,ce,,INTE")


def _short_path_api(monkeypatch, tmp_path, *, file_name="s.mechdb"):
    directory = tmp_path / "parent-\u03a9"
    directory.mkdir()
    snapshot = directory / file_name
    snapshot.write_bytes(b"native staged snapshot")
    alias = tmp_path / "PARENT~1"
    calls, identities = [], []

    class GetShortPathName:
        def __call__(self, path, buffer, size):
            calls.append(Path(path))
            if buffer is None:
                return len(str(alias)) + 1
            buffer.value = str(alias)
            return len(str(alias))

    api = GetShortPathName()
    monkeypatch.setattr(cdb, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: SimpleNamespace(GetShortPathNameW=api), raising=False)

    def samefile(candidate, original):
        identities.append((candidate, original))
        return (candidate, original) in {
            (alias, directory), (alias / file_name, snapshot),
        }

    monkeypatch.setattr(Path, "samefile", samefile)
    return SimpleNamespace(directory=directory, snapshot=snapshot, alias=alias, calls=calls, identities=identities)


@pytest.mark.parametrize("file_name", ["s.mechdb", "s.mechdat", "s.cdb"])
def test_native_short_file_path_preserves_original_filename_and_extension(tmp_path, monkeypatch, file_name):
    case = _short_path_api(monkeypatch, tmp_path, file_name=file_name)
    native = cdb._native_path(case.snapshot)
    assert native == case.alias / file_name
    assert native.suffix == case.snapshot.suffix
    assert str(native).isascii()
    assert case.calls == [case.directory, case.directory]
    assert case.identities == [(case.alias, case.directory), (native, case.snapshot)]
    assert case.snapshot.read_bytes() == b"native staged snapshot"


def test_native_short_directory_path_keeps_whole_directory_alias(tmp_path, monkeypatch):
    case = _short_path_api(monkeypatch, tmp_path)
    assert cdb._native_path(case.directory) == case.alias
    assert case.calls == [case.directory, case.directory]
    assert case.identities == [(case.alias, case.directory)]


@pytest.mark.parametrize("mismatch", ["parent", "file"])
def test_native_short_file_path_rejects_changed_filesystem_identity(tmp_path, monkeypatch, mismatch):
    case = _short_path_api(monkeypatch, tmp_path)
    monkeypatch.setattr(Path, "samefile", lambda candidate, original: (
        mismatch != "parent" if candidate == case.alias else mismatch != "file"
    ))
    with pytest.raises(ValueError, match="identity|short name"):
        cdb._native_path(case.snapshot)


@pytest.mark.parametrize("reparse", ["source", "parent", "alias", "file_alias"])
def test_native_short_file_path_rejects_reparse_points(tmp_path, monkeypatch, reparse):
    case = _short_path_api(monkeypatch, tmp_path)
    paths = {"source": case.snapshot, "parent": case.directory,
             "alias": case.alias, "file_alias": case.alias / case.snapshot.name}
    monkeypatch.setattr(cdb, "is_reparse_point", lambda path: path == paths[reparse])
    with pytest.raises(ValueError, match="reparse|identity|short name"):
        cdb._native_path(case.snapshot)


def test_native_short_file_path_has_no_filename_rewriting_fallback(tmp_path, monkeypatch):
    case = _short_path_api(monkeypatch, tmp_path, file_name="snapshot-\u03a9.mechdb")
    with pytest.raises(ValueError, match="ASCII Windows short name"):
        cdb._native_path(case.snapshot)
    assert case.calls == [case.directory, case.directory]
