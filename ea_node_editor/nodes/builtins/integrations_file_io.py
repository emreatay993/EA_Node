from __future__ import annotations

import json

from ea_node_editor.nodes.builtins.integrations_common import pick_path, require_existing_file
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PortSpec, PropertySpec


class FileReadNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="io.file_read",
            display_name="File Read",
            category="Input / Output",
            icon="description",
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
            category="Input / Output",
            icon="save",
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
        path = pick_path(ctx, input_key="path", property_key="path", node_name="File Write")
        if path.exists() and path.is_dir():
            raise ValueError(f"File Write path must be a file, not a directory: {path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        as_json = bool(ctx.properties.get("as_json", False))
        if as_json:
            payload = ctx.inputs["data"] if "data" in ctx.inputs else ctx.inputs.get("text", "")
            try:
                serialized = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
            except TypeError as exc:
                raise ValueError(f"File Write could not serialize payload as JSON: {exc}") from exc
            path.write_text(serialized, encoding="utf-8")
        else:
            payload = ctx.inputs.get("text", ctx.inputs.get("data", ""))
            path.write_text("" if payload is None else str(payload), encoding="utf-8")
        return NodeResult(outputs={"written_path": str(path), "exec_out": True})
