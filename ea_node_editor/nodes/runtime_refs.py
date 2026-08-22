from __future__ import annotations

from ea_node_editor.runtime_contracts import (
    ImageValue,
    RuntimeArtifactRef,
    RuntimeArtifactScope,
    RuntimeHandleRef,
    coerce_runtime_artifact_ref,
    coerce_runtime_handle_ref,
    deserialize_runtime_value,
    serialize_runtime_value,
)

RuntimeArtifactRef.__module__ = __name__
ImageValue.__module__ = __name__
RuntimeHandleRef.__module__ = __name__
coerce_runtime_artifact_ref.__module__ = __name__
coerce_runtime_handle_ref.__module__ = __name__
deserialize_runtime_value.__module__ = __name__
serialize_runtime_value.__module__ = __name__


__all__ = [
    "ImageValue",
    "RuntimeArtifactRef",
    "RuntimeArtifactScope",
    "RuntimeHandleRef",
    "coerce_runtime_artifact_ref",
    "coerce_runtime_handle_ref",
    "deserialize_runtime_value",
    "serialize_runtime_value",
]
