from __future__ import annotations

from pathlib import Path

from ea_node_editor.nodes.types import ExecutionContext


def pick_optional_path(ctx: ExecutionContext, *, input_key: str, property_key: str) -> Path | None:
    for candidate in (ctx.inputs.get(input_key), ctx.properties.get(property_key)):
        if candidate is None:
            continue
        text = str(candidate).strip()
        if text:
            resolved_path = ctx.resolve_path_value(candidate)
            return resolved_path if resolved_path is not None else Path(text)
    return None


def pick_path(ctx: ExecutionContext, *, input_key: str, property_key: str, node_name: str) -> Path:
    path = pick_optional_path(ctx, input_key=input_key, property_key=property_key)
    if path is not None:
        return path
    raise ValueError(f"{node_name} requires a non-empty file path.")


def require_existing_file(path: Path, *, node_name: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{node_name} path does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"{node_name} path must point to a file: {path}")
