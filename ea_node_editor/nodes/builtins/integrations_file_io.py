from __future__ import annotations

import json
from pathlib import Path

from ea_node_editor.nodes.builtins.integrations_common import pick_optional_path, pick_path, require_existing_file
from ea_node_editor.nodes.output_artifacts import write_managed_output
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec


def _write_file_payload(path: Path, *, inputs: dict[str, object], as_json: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if as_json:
        payload = inputs["data"] if "data" in inputs else inputs.get("text", "")
        try:
            serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
        except TypeError as exc:
            raise ValueError(f"File Write could not serialize payload as JSON: {exc}") from exc
        path.write_text(serialized, encoding="utf-8")
        return

    payload = inputs.get("text", inputs.get("data", ""))
    path.write_text("" if payload is None else str(payload), encoding="utf-8")


class FileReadNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="io.file_read",
            display_name="File Read",
    category_path=("Input / Output",),
            icon="integrations/description.svg",
            description="Reads a text file.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=False),
                PortSpec("path", "in", "data", "path", required=False),
                PortSpec("text", "out", "data", "str", exposed=True),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
            ),
            properties=(PropertySpec("path", "path", "", "File Path"),),
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        path = pick_path(ctx, input_key="path", property_key="path", node_name="File Read")
        require_existing_file(path, node_name="File Read")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"File Read failed for '{path}': {exc}") from exc
        return NodeResult(outputs={"text": text, "exec_out": True})


class FileWriteNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="io.file_write",
            display_name="File Write",
    category_path=("Input / Output",),
            icon="integrations/save.svg",
            description="Writes text or JSON to a file.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=False),
                PortSpec("path", "in", "data", "path", required=False),
                PortSpec("text", "in", "data", "str", required=False),
                PortSpec("data", "in", "data", "any", required=False),
                PortSpec("written_path", "out", "data", "path", exposed=True),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
            ),
            properties=(
                PropertySpec("path", "path", "output.txt", "Output Path"),
                PropertySpec("as_json", "bool", False, "Serialize As JSON"),
            ),
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        as_json = bool(ctx.properties.get("as_json", False))
        path = pick_optional_path(ctx, input_key="path", property_key="path")
        if path is None:
            write_result = write_managed_output(
                ctx,
                output_key="written_path",
                default_suffix=".json" if as_json else ".txt",
                write_payload=lambda output_path: _write_file_payload(
                    output_path,
                    inputs=ctx.inputs,
                    as_json=as_json,
                ),
            )
            return NodeResult(outputs={"written_path": write_result.artifact_ref, "exec_out": True})

        if path.exists() and path.is_dir():
            raise ValueError(f"File Write path must be a file, not a directory: {path}")

        _write_file_payload(path, inputs=ctx.inputs, as_json=as_json)
        return NodeResult(outputs={"written_path": str(path), "exec_out": True})


class PathPointerNodePlugin:
    """Path Pointer — holds a file or folder path for reuse across nodes.

    Implements Variant B ("File / Folder Pointer") from the design mockup at
    ``~/.claude/plans/do-i-have-some-enchanted-spindle.html``. Decisions:
    ``mode`` is ``"file"`` or ``"folder"``; no DPF handle output (downstream
    DPF workflows continue to use ``dpf.result_file``); all properties live in
    a single ``"Source"`` inspector group.

    Acts as a passive data source: one editable path feeds many consumers, so a
    path referenced by several nodes has a single edit point.
    """

    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="io.path_pointer",
            display_name="Path Pointer",
            category_path=("Input / Output",),
            icon="integrations/description.svg",
            description="Holds a file or folder path for reuse across nodes.",
            runtime_behavior="passive",
            ports=(
                PortSpec("path", "out", "data", "path", exposed=True),
                PortSpec("exists", "out", "data", "bool", exposed=True),
            ),
            properties=(
                PropertySpec(
                    "mode",
                    "enum",
                    "file",
                    "Mode",
                    enum_values=("file", "folder"),
                    inline_editor="enum",
                    inspector_editor="enum",
                    group="Source",
                ),
                PropertySpec(
                    "path",
                    "path",
                    "",
                    "Path",
                    inline_editor="path",
                    inspector_editor="path",
                    group="Source",
                ),
                PropertySpec(
                    "must_exist",
                    "bool",
                    True,
                    "Must Exist",
                    inspector_editor="toggle",
                    group="Source",
                ),
            ),
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        mode = str(ctx.properties.get("mode", "file")).strip().lower()
        if mode not in ("file", "folder"):
            raise ValueError(
                f"Path Pointer mode must be 'file' or 'folder', got: {mode!r}"
            )
        must_exist = bool(ctx.properties.get("must_exist", True))

        path = pick_optional_path(ctx, input_key="path", property_key="path")
        if path is None:
            if must_exist:
                raise ValueError(
                    "Path Pointer requires a non-empty path when 'Must Exist' is enabled."
                )
            return NodeResult(outputs={"path": "", "exists": False})

        exists = path.exists()
        type_ok = (path.is_file() if mode == "file" else path.is_dir()) if exists else False

        if must_exist:
            if not exists:
                raise FileNotFoundError(f"Path Pointer path does not exist: {path}")
            if mode == "file" and not path.is_file():
                raise ValueError(
                    f"Path Pointer expected a file but got a directory: {path}"
                )
            if mode == "folder" and not path.is_dir():
                raise ValueError(
                    f"Path Pointer expected a folder but got a file: {path}"
                )

        return NodeResult(
            outputs={"path": str(path), "exists": bool(exists and type_ok)}
        )
