from __future__ import annotations

from pathlib import Path

from ea_node_editor.nodes.types import ExecutionContext


def pick_path(ctx: ExecutionContext, *, input_key: str, property_key: str, node_name: str) -> Path:
    for candidate in (ctx.inputs.get(input_key), ctx.properties.get(property_key)):
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text:
            return Path(text)
    raise ValueError(f"{node_name} requires a non-empty file path.")


def require_existing_file(path: Path, *, node_name: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{node_name} path does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{node_name} path must point to a file: {path}")
