# Purpose: Prepare and validate no-solve native CDB exports in a disposable owner.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_cdb_export.py
"""Native-owner-only CDB preprocessing. Importing this module loads no Ansys code.

The caller owns snapshot creation, native process isolation, deadlines, cancellation,
and final publication. ``run_mapdl(directory, input_name, output_name, release)``
must run synchronously with a bounded lifetime in the owner's process job, raise on
failure/cancellation, and return only after its children exit. Every MAPDL filename
passed here is fixed ASCII and relative to its disposable working directory.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any
from uuid import uuid4

from ea_node_editor.common.path_safety import is_reparse_point

MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_RECEIPT_BYTES = 16 * 1024
MAX_COMPONENT_MEMBERS = 10_000_000
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_USER_COMMANDS = frozenset("""
/COM /PREP7 /SOLU FINISH FINI ALLSEL NSEL ESEL CM CMSEL CMDELE
ET KEYOPT KEYOP ETDELE TYPE MAT REAL SECNUM ESYS CSYS RSYS LOCAL CLOCAL
MP MPTEMP MPDATA MPDELE TB TBTEMP TBDATA TBPT TBDELE R RMORE RMODIF RDELE
SECTYPE SECDATA SECOFFSET SECCONTROL SECDELE D DDELE F FDELE SF SFDELE
SFE SFEDELE BF BFDELE BFE BFEDELE ACEL OMEGA DOMEGA TREF TOFFST
KBC NSUBST AUTOTS OUTRES NLGEOM EQSLV NROPT NEQIT CNVTOL
*SET *DIM *IF *ELSE *ELSEIF *ENDIF *DO *ENDDO *CYCLE *EXIT *GET *VGET
""".split())
_NATIVE_COMMANDS = _SAFE_USER_COMMANDS | frozenset("""
/BATCH /CONFIG /GO /GOLIST /GOPR /GST /NOLIST /NOPR /TITLE /UNITS /WB /EOF
*TAXIS N EN EMORE NBLOCK EBLOCK ETBLOCK CMBLOCK RLBLOCK RMOD
ANTYPE CNCHECK CNTR DMPOPTION DMPOPT EQSL ETCON FINI KEYO NSLE NSUB
NLDIAG RESCONTROL SHPP TIME MPAMOD ERESX SSTIF PSTRES NCNV
SECBLOCK SECOFFS SECCONT RLENGTH TUNIF BFUNIF SFCUM BFCUM DCUM FCUM
CE CP CERIG CEWRITE ACEL CORIOLIS DMPSTR TRNOPT TIMINT
""".split())
_DEPENDENCIES = (
    "ImportedLoad", "ImportedBodyTemperature", "ImportedDisplacement",
    "ImportedPressure", "ImportedForce", "ImportedStress", "ImportedInitial",
    "Submodel", "Condensed", "Superelement", "BoltPretension", "ContactStepControl",
    "NonlinearAdaptive", "NonlinearAdaptivity", "ElementBirth", "ElementDeath",
    "SystemCoupling", "SMARTCrack", "InitialState", "PythonCode",
)


def _read(path: Path) -> str:
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_FILE_BYTES:
        raise ValueError("Native CDB artifact is missing, empty, or too large: " + path.name)
    return path.read_text(encoding="utf-8", errors="strict")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def _commands(text: str):
    """Split APDL comments/command separators without interpreting quoted strings."""
    for line in text.splitlines():
        quote = None
        word = []
        for char in line:
            if char in "\"'":
                if quote == char:
                    quote = None
                elif quote is None:
                    quote = char
            if quote is None and char in "!$":
                if word:
                    yield "".join(word).strip()
                word = []
                if char == "!":
                    break
            else:
                word.append(char)
        if word:
            yield "".join(word).strip()
        if quote:
            raise ValueError("Unterminated APDL quoted string")


def validate_no_solve(text: str, *, user_snippet: bool = False) -> None:
    """Fail closed for user macros/indirection and result-dependent APDL.

This is a supported-command contract, not an APDL security sandbox. Native jobs
must still run under the caller's ownership and timeout/cancellation controls.
"""
    if not isinstance(text, str) or len(text) > MAX_FILE_BYTES:
        raise ValueError("Invalid APDL input")
    for command in _commands(text):
        if not command:
            continue
        parts = [part.strip().upper() for part in command.split(",")]
        verb = parts[0]
        if re.match(r"/COM(?:\s|,|$)", command, re.I):
            continue
        forbidden = (verb.startswith(("SOLV", "LSSO", "PSOL", "MFSO", "*LS")) or
                     verb in {"/INPUT", "/INP", "*USE", "*CREATE", "/SYS", "/SYP",
                              "RESUME", "RESU", "UPGEOM", "UPCOORD", "LDREAD",
                              "INISTATE", "SET", "/POST1", "/POST26", "*TREAD"} or
                     "%" in verb or
                     verb == "ANTYPE" and any(p.startswith("REST") for p in parts[1:]))
        if forbidden:
            raise ValueError("Solve-dependent or indirect APDL is unsupported: " + verb[:80])
        if verb == "CNCHECK" and (parts[1] if len(parts) > 1 else "") not in {
                "", "DETAIL", "SUMMARY", "RESET", "AUTO", "TRIM", "SPLIT", "DMP", "MERGE", "OVER"}:
            raise ValueError("CDB export does not allow partial contact solves or geometry adjustment")
        if verb == "CEWRITE" and parts != ["CEWRITE", "FILE", "CE", "", "INTE"]:
            raise ValueError("Only the native scratch-local connector write is qualified for CDB export")
        assignment = re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*(?:\([^\n]*\))?\s*=.*", command)
        if not user_snippet and verb not in _NATIVE_COMMANDS and not assignment:
            numeric = re.fullmatch(r"[\s0-9+.,EeDd-]+", command)
            record_format = re.fullmatch(r"\([0-9aAiIfFeEdDgGxX.,+\s-]+\)", command)
            if not numeric and not record_format:
                raise ValueError("Generated APDL command is not qualified for no-solve export: " + verb[:80])
        if verb in {"*GET", "*VGET"}:
            if len(parts) < 5 or parts[2] not in {"NODE", "ELEM", "COMP", "ETYP", "MAT", "RCON", "ACTIVE"}:
                raise ValueError("Unsupported APDL query dependency")
            if parts[4] not in {"COUNT", "NUM", "LOC", "MNLOC", "MXLOC", "NODE", "ATTR", "NAME", "TYPE", "TIME", "NCOMP", "INT"}:
                raise ValueError("Result-dependent APDL query is unsupported: " + command[:120])
        if re.search(r"\b(?:UX|UY|UZ|ROTX|ROTY|ROTZ|TEMP|PRES)\s*\(", command, re.I):
            raise ValueError("Result-dependent APDL expression is unsupported")
        if user_snippet:
            if verb not in _SAFE_USER_COMMANDS and not assignment:
                raise ValueError("User APDL command is not qualified for no-solve export: " + verb[:80])


def _tree_path(obj: Any) -> str:
    names, seen = [], set()
    while obj is not None and hasattr(obj, "ObjectId"):
        key = int(obj.ObjectId)
        if key in seen:
            raise ValueError("Cyclic native tree")
        seen.add(key)
        names.append(str(obj.Name))
        obj = obj.Parent
    return "/".join(reversed(names))


def resolve_analysis(model: Any, selector: Any = None) -> tuple[Any, dict[str, Any]]:
    """Resolve exact name/path or {ordinal, name}; ordinal is 1-based in all analyses.

    No source ObjectId is consumed. T02 must validate typed handles in the source
    owner, then translate them to an exact name/path or a qualified ordinal.
    """
    rows = [(a, {"name": str(a.Name), "object_path": _tree_path(a),
                 "ordinal": i + 1}) for i, a in enumerate(model.Analyses)
            if str(a.AnalysisType) == "Static" and str(a.PhysicsType) == "Mechanical"]
    if selector is None or selector == "":
        matches = rows
    elif isinstance(selector, str):
        matches = [(a, row) for a, row in rows if selector in (row["name"], row["object_path"])]
    elif isinstance(selector, Mapping) and set(selector) == {"ordinal", "name"}:
        if type(selector["ordinal"]) is not int or selector["ordinal"] < 1 or type(selector["name"]) is not str:
            raise ValueError("Invalid qualified analysis ordinal")
        matches = [(a, row) for a, row in rows if row["ordinal"] == selector["ordinal"] and row["name"] == selector["name"]]
    else:
        raise ValueError("Analysis must be an exact native name/path or a qualified ordinal")
    if len(matches) != 1:
        raise ValueError("Choose exactly one eligible Static Structural analysis; selection is missing or ambiguous")
    return matches[0]


@dataclass(frozen=True)
class _Block:
    kind: str
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def _blocks(text: str) -> list[_Block]:
    """Read documented native blocked records, including compressed components."""
    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        fields = lines[i].split("!")[0].strip().split(",")
        kind = fields[0].strip().upper()
        if kind not in {"NBLOCK", "EBLOCK", "ETBLOCK", "CMBLOCK"}:
            i += 1
            continue
        if i + 1 >= len(lines):
            raise ValueError("Truncated native block")
        start = i
        if kind == "CMBLOCK":
            match = re.fullmatch(r"\((\d+)i(\d+)\)", lines[i + 1].strip(), re.I)
            count = int(fields[3])
            if not match or count < 1 or count > 10_000_000:
                raise ValueError("Invalid native component format/count")
            i += 2 + (count + int(match[1]) - 1) // int(match[1])
            if i > len(lines):
                raise ValueError("Truncated native component")
        else:
            i += 2
            while i < len(lines) and lines[i].strip() != "-1" and not re.match(r"N,UNBL,LOC,\s*-1,", lines[i].strip(), re.I):
                i += 1
            if i == len(lines):
                raise ValueError("Unterminated native " + kind)
            i += 1
        result.append(_Block(kind, tuple(lines[start:i])))
    return result


def _integers(line: str, width: int) -> list[int]:
    return [int(line[i:i + width]) for i in range(0, len(line), width) if line[i:i + width].strip()]


def _mesh_data(text: str) -> dict[str, Any]:
    nodes, elements, types, components = {}, {}, {}, {}
    component_members = 0
    for block in _blocks(text):
        header = block.lines[0].split("!")[0].split(",")
        form = block.lines[1].lower()
        if block.kind == "NBLOCK":
            fmt = re.fullmatch(r"\(3i(\d+),6e(\d+)\.\d+e\d+\)", form)
            if not fmt:
                raise ValueError("Unqualified native node-block format")
            iw, fw = int(fmt[1]), int(fmt[2])
            for line in block.lines[2:-1]:
                key = int(line[:iw])
                values = tuple(float(line[3 * iw + j * fw:3 * iw + (j + 1) * fw].strip() or "0") for j in range(6))
                if key < 1 or key in nodes or not all(math.isfinite(v) for v in values):
                    raise ValueError("Invalid or duplicate native node")
                nodes[key] = values
        elif block.kind == "EBLOCK":
            fmt = re.fullmatch(r"\(19i(\d+)\)", form)
            if not fmt or header[2].strip().upper() != "SOLID":
                raise ValueError("Unqualified native element-block format")
            records = iter(block.lines[2:-1])
            for line in records:
                values = _integers(line, int(fmt[1]))
                if len(values) < 11 or not 1 <= values[8] <= 400:
                    raise ValueError("Invalid native element record")
                needed = 11 + values[8]
                while len(values) < needed:
                    try:
                        values.extend(_integers(next(records), int(fmt[1])))
                    except StopIteration as exc:
                        raise ValueError("Truncated native connectivity") from exc
                key = values[10]
                if key < 1 or len(values) != needed or key in elements:
                    raise ValueError("Invalid or duplicate native element")
                elements[key] = tuple(values)
        elif block.kind == "ETBLOCK":
            fmt = re.fullmatch(r"\(2i(\d+),19a\d+\)", form)
            if not fmt:
                raise ValueError("Unqualified native element-type block")
            width = int(fmt[1])
            for line in block.lines[2:-1]:
                key = int(line[:width])
                if key in types:
                    raise ValueError("Duplicate native element type")
                types[key] = tuple(line[j:j + width].strip() for j in range(0, len(line), width))
        else:
            width = int(re.fullmatch(r"\(\d+i(\d+)\)", form)[1])
            encoded = [v for line in block.lines[2:] for v in _integers(line, width)]
            if len(encoded) != int(header[3]):
                raise ValueError("Native component count mismatch")
            members = []
            for value in encoded:
                if value < 0:
                    if (not members or -value <= members[-1]
                            or component_members + len(members) + (-value - members[-1]) > MAX_COMPONENT_MEMBERS):
                        raise ValueError("Invalid compressed native component")
                    members.extend(range(members[-1] + 1, -value + 1))
                else:
                    if (value < 1 or component_members + len(members) >= MAX_COMPONENT_MEMBERS
                            or members and value <= members[-1]):
                        raise ValueError("Invalid or oversized native component membership")
                    members.append(value)
            name, kind = header[1].strip(), header[2].strip()
            if name in components or kind not in {"NODE", "ELEM"}:
                raise ValueError("Invalid native component identity")
            components[name] = (kind, tuple(members))
            component_members += len(members)
    if not nodes or not elements or not types:
        raise ValueError("CDB has no independently readable mesh/type definitions")
    if any(row[1] not in types or any(n not in nodes for n in row[11:] if n) for row in elements.values()):
        raise ValueError("Native connectivity/type reference is unresolved")
    return {"nodes": nodes, "elements": elements, "types": types, "components": components}


def _named_components(deck: str, ignored_regions: Mapping[str, str] | None = None) -> set[str]:
    result, active = set(), False
    end_marker = None
    filtered = []
    for line in deck.splitlines():
        stripped = line.strip()
        if end_marker is not None:
            if stripped == end_marker:
                end_marker = None
            continue
        if stripped in (ignored_regions or {}):
            end_marker = ignored_regions[stripped]
        else:
            filtered.append(line)
    if end_marker is not None:
        raise ValueError("Native user-command region is unterminated")
    for command in _commands("\n".join(filtered)):
        parts = [p.strip() for p in command.split(",")]
        verb = parts[0].upper()
        if re.match(r"/COM(?:\s|,|$)", command, re.I) and "********" in command:
            active = "SEND NAMED SELECTION AS" in command.upper()
        if active and verb in {"CM", "CMBLOCK"}:
            name = parts[1].upper()
            if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,31}", name):
                raise ValueError("Unqualified solver-exported component name")
            result.add(name)
    return result


def _selection(kind: str, ids: list[int]) -> str:
    # Compress contiguous ID runs without assuming that mesh numbering is dense.
    lines = [kind + "SEL,NONE"]
    start = end = ids[0]
    for value in ids[1:] + [None]:
        if value is not None and value == end + 1:
            end = value
        else:
            lines.append(f"{kind}SEL,A,{'NODE' if kind == 'N' else 'ELEM'},,{start},{end}")
            start = end = value
    return "\n".join(lines) + "\n"


def _support_definitions(text: str) -> str:
    """Keep native coordinate, real-constant and section definitions, not loads."""
    result = []
    continuation = False
    for line in text.splitlines():
        stripped = line.strip()
        verb = stripped.split(",", 1)[0].upper()
        if verb in {"RLBLOCK", "SECBLOCK"}:
            continuation = True
            result.append(line)
        elif continuation and (stripped.startswith("(") or re.fullmatch(r"[\s0-9+.,EeDd-]+", line)):
            result.append(line)
        else:
            continuation = False
            if verb in {"LOCAL", "CS", "CLOCAL", "R", "RMORE", "SECTYPE", "SECDATA",
                        "SECOFFSET", "SECCONTROL", "SECJOINT"}:
                result.append(line)
    return "\n".join(result) + ("\n" if result else "")


def _mesh_only(full: str, geometry: str, names: set[str]) -> str:
    original = _mesh_data(full)
    # GEOM has no ETBLOCK; validate its geometry using native full definitions.
    definitions = "".join(b.text for b in _blocks(full) if b.kind == "ETBLOCK")
    physical = _mesh_data(definitions + geometry)
    used = {row[1] for row in physical["elements"].values()}
    output = ["/PREP7\n"]
    for block in _blocks(full):
        if block.kind == "ETBLOCK":
            width = int(re.match(r"\(2i(\d+)", block.lines[1], re.I)[1])
            records = [line for line in block.lines[2:-1] if int(line[:width]) in used]
            if records:
                output.append(f"ETBLOCK,{len(records)},{max(used)}\n" + block.lines[1] + "\n" + "\n".join(records) + "\n-1\n")
    output.append(_support_definitions(full))
    output.extend(b.text for b in _blocks(geometry) if b.kind in {"NBLOCK", "EBLOCK"})
    for name in names:
        if name not in original["components"]:
            raise ValueError("Named selection was not present in native database: " + name)
        kind, members = original["components"][name]
        if not set(members).issubset(physical["nodes" if kind == "NODE" else "elements"]):
            raise ValueError("Named selection contains nonphysical mesh IDs")
    output.extend(b.text for b in _blocks(full) if b.kind == "CMBLOCK" and b.lines[0].split(",")[1].strip() in names)
    output.append("FINISH\n")
    return "".join(output)


def _canonical_database(text: str) -> tuple[str, ...]:
    # CDREAD does not restore Mechanical's diagnostic output settings. These
    # are not FE model/load data; every other native database record stays exact.
    return tuple(line.strip() for line in text.splitlines() if line.strip()
                 and line.split(",", 1)[0].strip().upper() not in {"/COM", "/UNITS", "NLDIAG"})


def _native_export_deck(generated: str, begin_marker: str, end_marker: str,
                        trailer: str) -> tuple[str, str]:
    lines = generated.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == begin_marker]
    ends = [i for i, line in enumerate(lines) if line.strip() == end_marker]
    if (len(ends) != 1 or len(starts) != 1 or starts[0] >= ends[0]
            or [line.strip() for line in lines[starts[0] + 1:ends[0]]]
            != [line.strip() for line in trailer.splitlines()]):
        raise RuntimeError("Native CDB export marker/trailer is invalid")
    prefix = "\n".join(lines[:starts[0]])
    validate_no_solve(prefix)
    return "\n".join(lines[:ends[0]]) + "\n/EXIT,NOSAVE\n", prefix


def validate_cdb_receipt(value: Any, *, stage_path: Path | None = None) -> dict[str, Any]:
    keys = {"schema_version", "format", "content", "analysis", "load_step", "step_time",
            "units", "nodes", "elements", "components", "omitted_named_selections",
            "bytes", "sha256", "mesh_sha256", "physics_sha256", "native_readback",
            "numerical_solve", "remeshed", "release_code"}
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError("Invalid CDB export receipt schema")
    receipt = dict(value)
    if (type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1 or receipt["format"] != "cdb"
            or receipt["content"] not in {"mesh", "full"}
            or receipt["native_readback"] is not True
            or receipt["numerical_solve"] is not False or receipt["remeshed"] is not False
            or type(receipt["release_code"]) is not int or receipt["release_code"] != 261):
        raise ValueError("Unqualified CDB export receipt")
    if any(type(receipt[k]) is not int or receipt[k] < 1 for k in ("nodes", "elements", "bytes")):
        raise ValueError("Invalid CDB size or mesh counts")
    if receipt["bytes"] > MAX_FILE_BYTES or not isinstance(receipt["analysis"], dict):
        raise ValueError("Invalid CDB size or analysis identity")
    analysis = receipt["analysis"]
    if (set(analysis) != {"ordinal", "name", "object_path"} or type(analysis["ordinal"]) is not int
            or analysis["ordinal"] < 1 or any(type(analysis[k]) is not str or not analysis[k] for k in ("name", "object_path"))):
        raise ValueError("Invalid CDB analysis identity")
    if (type(receipt["units"]) is not str or not receipt["units"]
            or any(type(receipt[k]) is not str or not _HASH.fullmatch(receipt[k])
                   for k in ("sha256", "mesh_sha256", "physics_sha256"))):
        raise ValueError("Invalid CDB units or native digest")
    if receipt["content"] == "mesh":
        if receipt["load_step"] is not None or receipt["step_time"] is not None:
            raise ValueError("Mesh CDB must not consume a load step")
    elif (type(receipt["load_step"]) is not int or receipt["load_step"] < 1
          or type(receipt["step_time"]) not in {int, float}
          or not math.isfinite(receipt["step_time"])):
        raise ValueError("Invalid CDB load state")
    if (type(receipt["components"]) is not list
            or any(type(name) is not str for name in receipt["components"])
            or type(receipt["omitted_named_selections"]) is not list
            or any(type(name) is not str for name in receipt["omitted_named_selections"])):
        raise ValueError("Invalid CDB named-selection receipt")
    if len(json.dumps(receipt, ensure_ascii=False).encode("utf-8")) > MAX_RECEIPT_BYTES:
        raise ValueError("CDB receipt exceeds the owner transport limit")
    if stage_path is not None:
        if (not stage_path.is_file() or is_reparse_point(stage_path)
                or stage_path.stat().st_size != receipt["bytes"] or _sha(stage_path) != receipt["sha256"]):
            raise ValueError("Staged CDB does not match its native readback receipt")
        mesh = _mesh_data(_read(stage_path))
        if (_digest(mesh) != receipt["mesh_sha256"] or len(mesh["nodes"]) != receipt["nodes"]
                or len(mesh["elements"]) != receipt["elements"]
                or sorted(mesh["components"]) != receipt["components"]):
            raise ValueError("Staged CDB mesh does not match its native readback receipt")
        text = _read(stage_path)
        units = [command.split(",", 1)[1].strip()
                 for command in _commands(text) if command.upper().startswith("/UNITS,")]
        if units != [receipt["units"]]:
            raise ValueError("Staged CDB units do not match their native receipt")
        physics = (_canonical_database(text) if receipt["content"] == "full"
                   else tuple(_support_definitions(text).splitlines()))
        if _digest(physics) != receipt["physics_sha256"]:
            raise ValueError("Staged CDB model definitions do not match their native receipt")
    return receipt


def _run_mapdl(directory: Path, input_name: str, output_name: str, release: int, *, timeout: float) -> None:
    root = os.environ.get(f"AWP_ROOT{release}", "")
    executable = Path(root) / "ansys" / "bin" / "winx64" / f"ANSYS{release}.exe"
    if not root or not executable.is_file():
        raise RuntimeError("CDB export requires the selected release's MAPDL installation")
    command = [str(executable), "-b", "-smp", "-np", "1", "-j", "corex_cdb",
               "-i", input_name, "-o", output_name]
    # The containing MechanicalOwnerProcess has already assigned its Windows
    # kill-on-close job. Native children inherit that ownership; never break away.
    with (directory / "launcher.log").open("ab") as output:
        result = subprocess.run(command, cwd=directory, stdin=subprocess.DEVNULL,
                                stdout=output, stderr=subprocess.STDOUT, timeout=timeout,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    log_path = directory / output_name
    if result.returncode != 0 or not log_path.is_file():
        raise RuntimeError(f"MAPDL CDB preprocessing failed; inspect {log_path}")
    if "*** ERROR ***" in _read(log_path):
        raise RuntimeError(f"MAPDL rejected the CDB preprocessing/readback; inspect {log_path}")


def _native_path(path: Path) -> Path:
    """Use an identity-checked Windows short name for legacy native file APIs."""
    if str(path).isascii():
        return path
    if os.name != "nt":
        raise ValueError("CDB native working paths require Windows")
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL("kernel32", use_last_error=True).GetShortPathNameW
    api.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    api.restype = wintypes.DWORD
    file_name = path.name if path.is_file() else None
    alias_target = path.parent if file_name is not None else path
    if is_reparse_point(path) or is_reparse_point(alias_target):
        raise ValueError("CDB native paths must not be reparse points")
    size = api(str(alias_target), None, 0)
    if not size:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_unicode_buffer(size)
    if not api(str(alias_target), buffer, size):
        raise ctypes.WinError(ctypes.get_last_error())
    native = Path(buffer.value)
    if file_name is not None:
        if is_reparse_point(native) or not native.samefile(alias_target):
            raise ValueError("Native CDB directory alias changed filesystem identity")
        native = native / file_name
    if not str(native).isascii() or is_reparse_point(native) or not native.samefile(path):
        raise ValueError("The native CDB working path needs an ASCII Windows short name; short names are unavailable")
    return native


def _prepare_input(context: Mapping[str, Any], directory: Path, *, content: str,
                   selector: Any, load_step: Any) -> dict[str, Any]:
    model, data_model, tree = context["Model"], context["DataModel"], context["Tree"]
    analysis, identity = resolve_analysis(model, selector)
    mesh = data_model.MeshDataByName("Global")
    if (int(mesh.NodeCount) < 1 or int(mesh.ElementCount) < 1
            or str(model.Mesh.State) != "UpToDate"):
        raise ValueError("CDB export requires an existing up-to-date mesh; generate it explicitly first")
    node_ids = sorted(int(value) for value in mesh.NodeIds)
    element_ids = sorted(int(value) for value in mesh.ElementIds)
    settings = analysis.AnalysisSettings
    step = 1 if content == "mesh" else load_step
    if type(step) is not int or not 1 <= step <= int(settings.NumberOfSteps):
        raise ValueError("CDB load step must identify one existing Mechanical load step")
    selected_id = int(analysis.ObjectId)
    snippets = []
    named = []
    for obj in tree.AllObjects:
        if bool(getattr(obj, "Suppressed", False)):
            continue
        owner = obj
        while owner is not None and not str(owner.GetType().FullName).endswith(".Analysis"):
            owner = getattr(owner, "Parent", None)
        if owner is not None and int(owner.ObjectId) != selected_id:
            continue
        native_type = str(obj.GetType().FullName)
        if any(name in native_type for name in _DEPENDENCIES):
            raise ValueError("CDB no-solve export does not support this dependency: " + str(obj.Name))
        if native_type.endswith(".CommandSnippet"):
            validate_no_solve(str(obj.Input), user_snippet=True)
            snippets.append(obj)
        if native_type.endswith(".NamedSelection"):
            named.append((str(obj.Name), bool(obj.SendToSolver), int(obj.TotalSelection)))
    from System import Enum
    user_regions = {}
    for snippet in snippets:
        # Scratch snapshot only. Keep every authored command, but no automatically
        # inserted SOLVE, including commands attached to earlier load steps.
        if hasattr(snippet, "IssueSolveCommand"):
            snippet.IssueSolveCommand = False
        begin = "/COM,COREX_USER_BEGIN_" + uuid4().hex
        end = "/COM,COREX_USER_END_" + uuid4().hex
        user_regions[begin] = end
        snippet.Input = begin + "\n" + str(snippet.Input) + "\n" + end
    no_solve = analysis.AddCommandSnippet()
    no_solve.Name = "COREX CDB no-solve preparation"
    no_solve.StepSelectionMode = Enum.Parse(no_solve.StepSelectionMode.GetType(), "All")
    no_solve.IssueSolveCommand = False
    no_solve.Input = "/COM,COREX CDB preprocessing only"
    export = analysis.AddCommandSnippet()
    export.Name = "COREX CDB export"
    export.StepSelectionMode = Enum.Parse(export.StepSelectionMode.GetType(), "ByNumber")
    export.StepNumber = step
    export.IssueSolveCommand = False
    begin_marker = "/COM,COREX_CDB_BEGIN_" + uuid4().hex
    marker = "/COM,COREX_CDB_END_" + uuid4().hex
    trailer = ("FINISH\n/PREP7\nALLSEL,ALL\nCDWRITE,DB,full,cdb\n"
               + _selection("E", element_ids) + _selection("N", node_ids)
               + "NSLE,A\nCDWRITE,GEOM,geometry,cdb\n")
    export.Input = begin_marker + "\n" + trailer + marker + "\n/EXIT,NOSAVE\n"
    path = directory / "input.dat"
    analysis.WriteInputFile(str(path))
    generated = _read(path)
    executable, native_prefix = _native_export_deck(generated, begin_marker, marker, trailer)
    prefix = list(_commands(native_prefix))
    units = [c.split(",", 1)[1].strip() for c in prefix if c.upper().startswith("/UNITS,")]
    times = [c.split(",", 1)[1].strip() for c in prefix if c.upper().startswith("TIME,")]
    if len(units) != 1 or not re.fullmatch(r"[A-Za-z]+", units[0]) or not times:
        raise ValueError("Native solver units or selected load-step time are unavailable")
    path.write_text(executable, encoding="utf-8")
    return {"analysis": identity, "step": step, "step_time": float(times[-1]),
            "units": units[0].upper(), "element_ids": element_ids, "node_ids": node_ids,
            "names": _named_components(generated, user_regions),
            "omitted": [name for name, enabled, count in named if not enabled or count == 0]}


def export_cdb_snapshot(*, snapshot_path: Path, stage_path: Path, work_root: Path,
                        content: str = "mesh", analysis: Any = None, load_step: Any = 1,
                        release_code: int = 261, timeout_sec: float = 600.0,
                        run_mapdl: Callable[..., None] | None = None) -> dict[str, Any]:
    """Export one native-staged snapshot inside a fresh Mechanical owner process.

    The caller must create the native snapshot and own this process and its child
    job. Never call this helper inside the GUI or a shared execution worker.
    ``analysis`` is an exact name/path or a source-qualified {ordinal, name}.
    """
    if content not in {"mesh", "full"} or type(release_code) is not int or release_code != 261:
        raise ValueError("CDB export is qualified for mesh/full content in Mechanical 2026 R1 only")
    if type(timeout_sec) not in {int, float} or not math.isfinite(timeout_sec) or timeout_sec <= 0:
        raise ValueError("Invalid native CDB timeout")
    snapshot_path, stage_path, work_root = map(Path, (snapshot_path, stage_path, work_root))
    if (not snapshot_path.is_file() or snapshot_path.suffix.casefold() not in {".mechdb", ".mechdat"}
            or stage_path.exists() or not stage_path.parent.is_dir()
            or work_root.exists() or not work_root.parent.is_dir()
            or any(is_reparse_point(p) for p in (snapshot_path, stage_path.parent, work_root.parent))):
        raise ValueError("Invalid CDB snapshot or private staging paths")
    deadline = time.monotonic() + timeout_sec
    original_hash = _sha(snapshot_path)
    work_root.mkdir()
    native_root = _native_path(work_root.resolve())
    from ansys.mechanical.core import App, global_variables
    app = App(version=release_code)
    try:
        app.open(str(_native_path(snapshot_path.resolve())))
        prepared = _prepare_input(global_variables(app), native_root, content=content,
                                  selector=analysis, load_step=load_step)
    finally:
        app.close()
    if _sha(snapshot_path) != original_hash:
        raise RuntimeError("CDB preparation changed the snapshot database on disk")
    runner = run_mapdl or _run_mapdl

    def run(input_name: str, output_name: str) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("CDB native deadline expired")
        runner(native_root, input_name, output_name, release_code, timeout=remaining)

    run("input.dat", "export.out")
    full = _read(work_root / "full.cdb")
    full_mesh = _mesh_data(full)
    if not set(prepared["element_ids"]).issubset(full_mesh["elements"]):
        raise ValueError("Native preprocessing removed physical mesh elements")
    candidate = work_root / "export.cdb"
    if content == "mesh":
        text = _mesh_only(full, _read(work_root / "geometry.cdb"), prepared["names"])
        mesh = _mesh_data(text)
        if set(mesh["elements"]) != set(prepared["element_ids"]):
            raise ValueError("Mesh CDB contains generated elements or omits physical elements")
        if any(mesh["elements"][key] != full_mesh["elements"][key] for key in mesh["elements"]):
            raise ValueError("Mesh CDB changed native physical element definitions")
    else:
        text, mesh = full, full_mesh
    candidate.write_text("/UNITS," + prepared["units"] + "\n" + text, encoding="utf-8")
    (work_root / "verify.dat").write_text(
        "/PREP7\nCDREAD,DB,export,cdb\nALLSEL,ALL\nCDWRITE,DB,verified,cdb\n/EXIT,NOSAVE\n",
        encoding="ascii")
    run("verify.dat", "verify.out")
    verified = _read(work_root / "verified.cdb")
    if _mesh_data(verified) != mesh:
        raise RuntimeError("Native CDB readback changed mesh, element types, or components")
    if content == "full" and _canonical_database(full) != _canonical_database(verified):
        raise RuntimeError("Native CDB readback changed model or load definitions")
    if content == "mesh" and _support_definitions(text) != _support_definitions(verified):
        raise RuntimeError("Native CDB readback changed required element support definitions")
    physics = _canonical_database(full) if content == "full" else tuple(_support_definitions(text).splitlines())
    receipt = {
        "schema_version": 1, "format": "cdb", "content": content,
        "analysis": prepared["analysis"], "load_step": prepared["step"] if content == "full" else None,
        "step_time": prepared["step_time"] if content == "full" else None,
        "units": prepared["units"], "nodes": len(mesh["nodes"]), "elements": len(mesh["elements"]),
        "components": sorted(mesh["components"]), "omitted_named_selections": prepared["omitted"],
        "bytes": candidate.stat().st_size, "sha256": _sha(candidate),
        "mesh_sha256": _digest(mesh), "physics_sha256": _digest(physics),
        "native_readback": True, "numerical_solve": False, "remeshed": False, "release_code": release_code,
    }
    validate_cdb_receipt(receipt, stage_path=candidate)
    # Atomic no-clobber handoff to the parent's existing publication staging.
    os.link(candidate, stage_path)
    return validate_cdb_receipt(receipt, stage_path=stage_path)


__all__ = ["export_cdb_snapshot", "resolve_analysis", "validate_cdb_receipt", "validate_no_solve"]
