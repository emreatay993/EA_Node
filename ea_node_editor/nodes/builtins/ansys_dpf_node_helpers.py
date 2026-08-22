from __future__ import annotations

from typing import Any

from ea_node_editor.nodes.builtins.ansys_dpf_common import (
    normalize_result_file_path,
    resolve_model_handle_and_object,
)


def source_value_from_ctx(
    ctx,
    *,
    result_file_key: str,
    path_key: str,
    node_name: str,
) -> Any:  # noqa: ANN001
    result_file_value = ctx.inputs.get(result_file_key)
    if result_file_value is not None:
        return result_file_value

    path_value = ctx.inputs.get(path_key)
    if path_value is not None and str(path_value).strip():
        return normalize_result_file_path(
            ctx,
            input_key=path_key,
            property_key=path_key,
            node_name=node_name,
        )

    return normalize_result_file_path(
        ctx,
        input_key=path_key,
        property_key=path_key,
        node_name=node_name,
    )


def require_model_input(ctx, *, node_name: str):  # noqa: ANN001
    model_value = ctx.inputs.get("model")
    if model_value is None:
        raise ValueError(f"{node_name} requires a model input.")
    return resolve_model_handle_and_object(ctx, model_value, node_name=node_name)


def default_export_artifact_key(ctx, field_ref) -> str:  # noqa: ANN001
    result_name = str(field_ref.metadata.get("result_name", "")).strip() or "field"
    set_id = int(field_ref.metadata.get("set_id", 1))
    return f"{ctx.workspace_id}.{ctx.node_id}.{result_name}.set{set_id}"


__all__ = [
    "default_export_artifact_key",
    "require_model_input",
    "source_value_from_ctx",
]
