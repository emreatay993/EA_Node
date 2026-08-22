from __future__ import annotations

from collections.abc import Iterable

_MUTUALLY_EXCLUSIVE_TARGET_INPUT_GROUPS: dict[tuple[str, str], tuple[str, ...]] = {
    ("dpf.model", "result_file"): ("result_file", "path"),
    ("dpf.model", "path"): ("result_file", "path"),
}

_PROPERTY_OVERRIDE_INPUT_PORT_PRECEDENCE: dict[tuple[str, str], tuple[str, ...]] = {
    ("dpf.model", "path"): ("result_file", "path"),
}


def _normalize_token(value: str) -> str:
    return str(value or "").strip()


def property_override_input_port_keys(node_type_id: str, property_key: str) -> tuple[str, ...]:
    normalized_node_type_id = _normalize_token(node_type_id)
    normalized_property_key = _normalize_token(property_key)
    if not normalized_property_key:
        return ()
    return _PROPERTY_OVERRIDE_INPUT_PORT_PRECEDENCE.get(
        (normalized_node_type_id, normalized_property_key),
        (normalized_property_key,),
    )


def mutually_exclusive_target_input_group(node_type_id: str, port_key: str) -> tuple[str, ...] | None:
    normalized_node_type_id = _normalize_token(node_type_id)
    normalized_port_key = _normalize_token(port_key)
    if not normalized_node_type_id or not normalized_port_key:
        return None
    return _MUTUALLY_EXCLUSIVE_TARGET_INPUT_GROUPS.get((normalized_node_type_id, normalized_port_key))


def conflicting_target_input_keys(node_type_id: str, port_key: str) -> tuple[str, ...]:
    group = mutually_exclusive_target_input_group(node_type_id, port_key)
    if group is None:
        return ()
    normalized_port_key = _normalize_token(port_key)
    return tuple(candidate for candidate in group if candidate != normalized_port_key)


def higher_precedence_conflicting_target_input_keys(node_type_id: str, port_key: str) -> tuple[str, ...]:
    group = mutually_exclusive_target_input_group(node_type_id, port_key)
    if group is None:
        return ()
    normalized_port_key = _normalize_token(port_key)
    try:
        current_index = group.index(normalized_port_key)
    except ValueError:
        return ()
    return group[:current_index]


def inactive_input_source_key(
    node_type_id: str,
    port_key: str,
    connected_input_port_keys: Iterable[str],
) -> str | None:
    higher_precedence_keys = higher_precedence_conflicting_target_input_keys(node_type_id, port_key)
    if not higher_precedence_keys:
        return None
    connected_lookup = {_normalize_token(candidate) for candidate in connected_input_port_keys}
    for candidate in higher_precedence_keys:
        if candidate in connected_lookup:
            return candidate
    return None


def driven_by_input_reason(source_port_key: str) -> str:
    normalized_source_port_key = _normalize_token(source_port_key)
    if not normalized_source_port_key:
        return ""
    return f"Driven by {normalized_source_port_key}"


def mutually_exclusive_connect_message(target_port_key: str, source_port_key: str) -> str:
    normalized_target_port_key = _normalize_token(target_port_key)
    normalized_source_port_key = _normalize_token(source_port_key)
    if not normalized_target_port_key and not normalized_source_port_key:
        return "These inputs are mutually exclusive."
    if not normalized_target_port_key:
        return f"Can't connect while {normalized_source_port_key} is active."
    if not normalized_source_port_key:
        return f"Can't connect {normalized_target_port_key} because this input is inactive."
    return f"Can't connect {normalized_target_port_key} while {normalized_source_port_key} is active."


__all__ = [
    "conflicting_target_input_keys",
    "driven_by_input_reason",
    "higher_precedence_conflicting_target_input_keys",
    "inactive_input_source_key",
    "mutually_exclusive_connect_message",
    "mutually_exclusive_target_input_group",
    "property_override_input_port_keys",
]
