# Purpose: Define typed runtime carriers and strict recursive serialization.
# Map: subsystems/supporting_runtime_assets.md
# Tests: tests/test_typed_runtime_values.py
# Landmarks: TypedInlineValue; RuntimeArtifactRef; RuntimeHandleRef; serialize_runtime_value; deserialize_runtime_value

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import zlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from ea_node_editor.common.payload_tools import (
    INLINE_PAYLOAD_MAX_BYTES,
    JSON_MAX_DEPTH,
    REF_METADATA_MAX_BYTES,
    copy_json_mapping,
    copy_json_safe,
)

from ea_node_editor.runtime_contracts.data_tree import DataTree
from ea_node_editor.runtime_contracts.data_types import (
    ARRAY_DATA_REF_TYPE_ID,
    ARRAY_SLICE_2D_REF_TYPE_ID,
    DataTypeCatalogError,
    INTERVAL_1D_GRAPH_DATA_TYPE_ID,
    TABULAR_DATA_REF_TYPE_ID,
    TABULAR_WINDOW_REF_TYPE_ID,
)
from ea_node_editor.runtime_contracts.interval_1d import (
    INTERVAL_1D_DATA_TYPE,
    Interval1D,
)
from ea_node_editor.runtime_contracts.tabular_data import (
    ARRAY_DATA_REF_MARKER_VALUE,
    ARRAY_SLICE_2D_REF_MARKER_VALUE,
    TABULAR_DATA_REF_MARKER_VALUE,
    TABULAR_WINDOW_REF_MARKER_VALUE,
    ArrayDataRef,
    ArraySlice2DRef,
    TabularDataRef,
    TabularWindowRef,
    coerce_array_data_ref,
    coerce_array_slice_2d_ref,
    coerce_tabular_data_ref,
    coerce_tabular_window_ref,
)
from ea_node_editor.persistence.artifact_refs import (
    ManagedArtifactRef,
    StagedArtifactRef,
    format_managed_artifact_ref,
    format_staged_artifact_ref,
    parse_artifact_ref,
)

if TYPE_CHECKING:
    from ea_node_editor.runtime_contracts.data_types import DataTypeCatalog

RuntimeArtifactScope = Literal["managed", "staged"]

_RUNTIME_VALUE_MARKER_KEY = "__ea_runtime_value__"
_OPAQUE_MAPPING_RUNTIME_MARKERS = frozenset(
    {
        "secret_data",
        "ssh_sftp_host_data",
    }
)
_RUNTIME_ARTIFACT_MARKER_VALUE = "artifact_ref"
_RUNTIME_IMAGE_MARKER_VALUE = "image_value"
_RUNTIME_HANDLE_MARKER_VALUE = "handle_ref"
_RUNTIME_TYPED_INLINE_MARKER_VALUE = "typed_inline"
_RUNTIME_DATA_TREE_MARKER_VALUE = "data_tree"
_RUNTIME_INTERVAL_1D_MARKER_VALUE = INTERVAL_1D_DATA_TYPE
_RUNTIME_ARTIFACT_FORMAT_MAX_LENGTH = 64
_RUNTIME_ARTIFACT_FORMAT_PATTERN = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")
_RUNTIME_ARTIFACT_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_RUNTIME_ARTIFACT_PROVENANCE_MAX_LENGTH = 128
_RUNTIME_ARTIFACT_PROVENANCE_PATTERN = re.compile(
    r"[A-Za-z0-9]+(?:[._:-][A-Za-z0-9]+)*"
)
IMAGE_VALUE_DATA_TYPE_ID = "COREX.DataTypes.Image"
IMAGE_VALUE_SCHEMA_VERSION = 1
IMAGE_VALUE_MAX_ENCODED_BYTES = 64 * 1024 * 1024
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_IMAGE_VALUE_MAX_PIXELS = 64_000_000
_PNG_DECODE_CHUNK_BYTES = 64 * 1024
_PNG_CHANNELS_BY_COLOR_TYPE = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
_PRIVATE_PATH_PATTERN = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/)")
_DRIVE_RELATIVE_PATH_PATTERN = re.compile(r"^[A-Za-z]:(?![\\/])")
_HOME_PATH_PATTERN = re.compile(r"^~(?:[^\\/]*[\\/]|$)")
_ENVIRONMENT_PATH_PATTERN = re.compile(
    r"^(?:%[A-Za-z_][A-Za-z0-9_]*%|\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$[A-Za-z_][A-Za-z0-9_]*)"
)
_DURABLE_PRIVATE_RELATIVE_ROOTS = frozenset(
    {
        "private",
        "session-temp",
        "session-temporary",
        "session_temp",
        "session_temporary",
        "staging",
    }
)
_FORBIDDEN_DURABLE_MARKERS = frozenset(
    {
        _RUNTIME_HANDLE_MARKER_VALUE,
        TABULAR_DATA_REF_MARKER_VALUE,
        ARRAY_DATA_REF_MARKER_VALUE,
        TABULAR_WINDOW_REF_MARKER_VALUE,
        ARRAY_SLICE_2D_REF_MARKER_VALUE,
        "secret_data",
        "ssh_sftp_host_data",
    }
)


@dataclass(slots=True, frozen=True)
class DurableRuntimeValueValidation:
    eligible: bool
    reason_code: str
    canonical_payload: bytes | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.eligible, bool):
            raise TypeError("eligible must be a boolean")
        if not isinstance(self.reason_code, str):
            raise TypeError("reason_code must be a string")
        if self.eligible:
            if self.reason_code != "durable_value_eligible":
                raise ValueError("eligible durable values require the success reason")
            if type(self.canonical_payload) is not bytes:
                raise TypeError("eligible durable values require canonical bytes")
        elif self.canonical_payload is not None:
            raise ValueError("ineligible durable values cannot carry canonical bytes")


def _png_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) < 8 or payload[:8] != _PNG_SIGNATURE:
        raise ValueError("encoded_bytes must contain a valid PNG header")
    offset = 8
    dimensions: tuple[int, int] | None = None
    color_type = -1
    seen_plte = False
    seen_idat = False
    idat_closed = False
    row_stride = 0
    expected_decoded_bytes = 0
    decoded_bytes = 0
    decompressor: zlib.Decompress | None = None

    def consume_raster(decoded: bytes) -> None:
        nonlocal decoded_bytes
        if len(decoded) > expected_decoded_bytes - decoded_bytes:
            raise ValueError("PNG decoded raster exceeds the IHDR byte count")
        first_filter = (-decoded_bytes) % row_stride
        for index in range(first_filter, len(decoded), row_stride):
            if decoded[index] > 4:
                raise ValueError("PNG scanline filter byte is invalid")
        decoded_bytes += len(decoded)

    def consume_idat(compressed: bytes | memoryview) -> None:
        if decompressor is None:
            raise ValueError("PNG IDAT decoder is unavailable")
        pending: bytes | memoryview = compressed
        while pending:
            if decompressor.eof:
                raise ValueError("PNG IDAT contains trailing compressed stream data")
            output_limit = max(
                1,
                min(
                    _PNG_DECODE_CHUNK_BYTES,
                    expected_decoded_bytes - decoded_bytes + 1,
                ),
            )
            previous_length = len(pending)
            try:
                decoded = decompressor.decompress(pending, output_limit)
            except zlib.error as exc:
                raise ValueError("PNG IDAT contains invalid zlib data") from exc
            pending = decompressor.unconsumed_tail
            consume_raster(decoded)
            if decompressor.eof:
                if decompressor.unused_data or pending:
                    raise ValueError("PNG IDAT contains trailing compressed stream data")
                return
            if not pending:
                return
            if len(pending) == previous_length and not decoded:
                raise ValueError("PNG IDAT decoder made no progress")

    def finish_raster() -> None:
        if decompressor is None:
            raise ValueError("PNG IDAT chunk is missing")
        while not decompressor.eof:
            output_limit = max(
                1,
                min(
                    _PNG_DECODE_CHUNK_BYTES,
                    expected_decoded_bytes - decoded_bytes + 1,
                ),
            )
            try:
                decoded = decompressor.decompress(b"", output_limit)
            except zlib.error as exc:
                raise ValueError("PNG IDAT contains invalid zlib data") from exc
            if not decoded:
                break
            consume_raster(decoded)
        if not decompressor.eof:
            raise ValueError("PNG IDAT zlib stream did not reach EOF")
        if decompressor.unused_data or decompressor.unconsumed_tail:
            raise ValueError("PNG IDAT contains trailing compressed stream data")
        if decoded_bytes != expected_decoded_bytes:
            raise ValueError("PNG decoded raster byte count does not match IHDR")

    while offset < len(payload):
        if len(payload) - offset < 12:
            raise ValueError("PNG chunk is truncated")
        length = int.from_bytes(payload[offset : offset + 4], "big")
        chunk_type = payload[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(payload):
            raise ValueError("PNG chunk length exceeds encoded_bytes")
        if len(chunk_type) != 4 or not all(
            ord("A") <= byte <= ord("Z") or ord("a") <= byte <= ord("z")
            for byte in chunk_type
        ) or chunk_type[2] & 0x20:
            raise ValueError("PNG chunk type is invalid")
        data = memoryview(payload)[offset + 8 : offset + 8 + length]
        expected_crc = int.from_bytes(payload[offset + 8 + length : chunk_end], "big")
        chunk_crc = zlib.crc32(data, zlib.crc32(chunk_type)) & 0xFFFFFFFF
        if chunk_crc != expected_crc:
            raise ValueError("PNG chunk CRC is invalid")
        if dimensions is None:
            if chunk_type != b"IHDR" or length != 13:
                raise ValueError("PNG IHDR must be the first chunk")
            width = int.from_bytes(data[0:4], "big")
            height = int.from_bytes(data[4:8], "big")
            bit_depth, color_type, compression, filter_method, interlace = data[8:13]
            valid_depths = {
                0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8},
                4: {8, 16}, 6: {8, 16},
            }
            if interlace != 0:
                raise ValueError("interlaced PNG images are not supported")
            if (
                width < 1 or height < 1 or width * height > _IMAGE_VALUE_MAX_PIXELS
                or bit_depth not in valid_depths.get(color_type, set())
                or compression != 0 or filter_method != 0
            ):
                raise ValueError("PNG IHDR is invalid or exceeds 64 megapixels")
            dimensions = width, height
            row_bytes = (
                width * _PNG_CHANNELS_BY_COLOR_TYPE[color_type] * bit_depth + 7
            ) // 8
            row_stride = row_bytes + 1
            expected_decoded_bytes = height * row_stride
        elif chunk_type == b"IHDR":
            raise ValueError("PNG contains multiple IHDR chunks")
        elif chunk_type == b"PLTE":
            if seen_plte or seen_idat or color_type in {0, 4} or length < 3 or length > 768 or length % 3:
                raise ValueError("PNG PLTE chunk order or length is invalid")
            seen_plte = True
        elif chunk_type == b"IDAT":
            if idat_closed or (color_type == 3 and not seen_plte):
                raise ValueError("PNG IDAT chunk order is invalid")
            seen_idat = True
            if decompressor is None:
                decompressor = zlib.decompressobj()
            consume_idat(data)
        elif chunk_type == b"IEND":
            if length != 0 or not seen_idat or chunk_end != len(payload):
                raise ValueError("PNG IEND chunk is invalid or not final")
            finish_raster()
            return dimensions
        elif not chunk_type[0] & 0x20:
            raise ValueError("PNG contains an unsupported critical chunk")
        if seen_idat and chunk_type != b"IDAT":
            idat_closed = True
        offset = chunk_end
    raise ValueError("PNG IEND chunk is missing")


@dataclass(slots=True, frozen=True)
class ImageValue:
    encoded_bytes: bytes
    format: str
    width: int
    height: int
    sha256: str
    schema_version: int = IMAGE_VALUE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if type(self.encoded_bytes) is not bytes:
            raise TypeError("encoded_bytes must be immutable bytes")
        encoded_size = ((len(self.encoded_bytes) + 2) // 3) * 4
        if encoded_size > IMAGE_VALUE_MAX_ENCODED_BYTES:
            raise ValueError("encoded PNG exceeds the 64 MiB runtime payload limit")
        if type(self.format) is not str:
            raise TypeError("format must be an exact string")
        if type(self.width) is not int or type(self.height) is not int:
            raise TypeError("width and height must be exact integers")
        if type(self.sha256) is not str:
            raise TypeError("sha256 must be an exact string")
        if type(self.schema_version) is not int:
            raise TypeError("schema_version must be an exact integer")
        if self.format != "png":
            raise ValueError("ImageValue format must be 'png'")
        if self.schema_version != IMAGE_VALUE_SCHEMA_VERSION:
            raise ValueError("ImageValue schema_version must be 1")
        png_width, png_height = _png_dimensions(self.encoded_bytes)
        if self.width != png_width or self.height != png_height:
            raise ValueError("ImageValue dimensions do not match the PNG header")
        digest = hashlib.sha256(self.encoded_bytes).hexdigest()
        if self.sha256 != digest:
            raise ValueError("ImageValue sha256 does not match encoded_bytes")

    @property
    def data_type_id(self) -> str:
        return IMAGE_VALUE_DATA_TYPE_ID

    @classmethod
    def from_png(cls, encoded_bytes: bytes) -> ImageValue:
        if type(encoded_bytes) is not bytes:
            raise TypeError("encoded_bytes must be immutable bytes")
        payload = encoded_bytes
        width, height = _png_dimensions(payload)
        return cls(
            encoded_bytes=payload,
            format="png",
            width=width,
            height=height,
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        catalog: DataTypeCatalog | None = None,
    ) -> ImageValue | None:
        if payload.get(_RUNTIME_VALUE_MARKER_KEY) != _RUNTIME_IMAGE_MARKER_VALUE:
            return None
        if catalog is None:
            raise DataTypeCatalogError(
                "an active data-type catalog is required for image values"
            )
        _validate_payload_fields(
            payload,
            label="ImageValue payload",
            required=frozenset(
                {
                    _RUNTIME_VALUE_MARKER_KEY,
                    "data_type_id",
                    "schema_version",
                    "format",
                    "width",
                    "height",
                    "sha256",
                    "encoded_base64",
                }
            ),
        )
        if payload["data_type_id"] != IMAGE_VALUE_DATA_TYPE_ID:
            raise ValueError("ImageValue data_type_id is invalid")
        encoded = payload["encoded_base64"]
        if not isinstance(encoded, str) or len(encoded) > IMAGE_VALUE_MAX_ENCODED_BYTES:
            raise ValueError("ImageValue encoded_base64 exceeds the 64 MiB limit")
        try:
            png = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("ImageValue encoded_base64 is invalid") from exc
        value = cls(
            encoded_bytes=png,
            format=payload["format"],
            width=payload["width"],
            height=payload["height"],
            sha256=payload["sha256"],
            schema_version=payload["schema_version"],
        )
        catalog.validate_carrier(IMAGE_VALUE_DATA_TYPE_ID, value)
        return value

    def to_payload(self, *, catalog: DataTypeCatalog | None = None) -> dict[str, Any]:
        if catalog is None:
            raise DataTypeCatalogError(
                "an active data-type catalog is required for image values"
            )
        catalog.validate_carrier(IMAGE_VALUE_DATA_TYPE_ID, self)
        encoded = base64.b64encode(self.encoded_bytes).decode("ascii")
        if len(encoded) > IMAGE_VALUE_MAX_ENCODED_BYTES:
            raise ValueError("ImageValue encoded_base64 exceeds the 64 MiB limit")
        return {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_IMAGE_MARKER_VALUE,
            "data_type_id": IMAGE_VALUE_DATA_TYPE_ID,
            "schema_version": self.schema_version,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "sha256": self.sha256,
            "encoded_base64": encoded,
        }


def _copy_metadata_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return copy_json_mapping(
        value,
        field_name="metadata",
        max_encoded_bytes=REF_METADATA_MAX_BYTES,
        reject_sensitive_metadata=True,
    )


def _normalize_required_runtime_string(field_name: str, value: object) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _normalize_data_type_id(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("data_type_id must be a string")
    return _normalize_required_runtime_string("data_type_id", value)


def _normalize_schema_version(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("schema_version must be an integer")
    if value < 1:
        raise ValueError("schema_version must be >= 1")
    return value


def _validate_artifact_format(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("format must be a string")
    if (
        not value
        or value != value.strip()
        or len(value) > _RUNTIME_ARTIFACT_FORMAT_MAX_LENGTH
        or _RUNTIME_ARTIFACT_FORMAT_PATTERN.fullmatch(value) is None
    ):
        raise ValueError(
            "format must be a nonblank, already-trimmed lowercase token of at "
            "most 64 characters; '.', '_', and '-' are allowed only between "
            "alphanumeric segments"
        )
    return value


def _validate_artifact_size_bytes(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("size_bytes must be an integer")
    if value < 0:
        raise ValueError("size_bytes must be >= 0")
    return value


def _validate_artifact_sha256(value: object) -> str:
    if (
        not isinstance(value, str)
        or _RUNTIME_ARTIFACT_SHA256_PATTERN.fullmatch(value) is None
    ):
        raise ValueError("sha256 must be a lowercase 64-character hex digest")
    return value


def _validate_artifact_provenance(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("provenance must be a string")
    if (
        not value
        or value != value.strip()
        or len(value) > _RUNTIME_ARTIFACT_PROVENANCE_MAX_LENGTH
        or _RUNTIME_ARTIFACT_PROVENANCE_PATTERN.fullmatch(value) is None
    ):
        raise ValueError(
            "provenance must be a nonblank, already-trimmed identifier of at "
            "most 128 characters"
        )
    return value


def _validate_payload_fields(
    payload: Mapping[str, Any],
    *,
    label: str,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
) -> None:
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"{label} is missing: " + ", ".join(sorted(missing)))
    unexpected = set(payload).difference(required | optional)
    if unexpected:
        raise ValueError(
            f"{label} has unexpected fields: "
            + ", ".join(sorted(str(key) for key in unexpected))
        )


def _normalize_worker_generation(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("worker_generation must be an integer")
    try:
        generation = int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("worker_generation must be an integer") from exc
    if generation < 0:
        raise ValueError("worker_generation must be >= 0")
    return generation


@dataclass(slots=True, frozen=True)
class TypedInlineValue:
    data_type_id: str
    schema_version: int
    payload: Any

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "data_type_id",
            _normalize_data_type_id(self.data_type_id),
        )
        object.__setattr__(
            self,
            "schema_version",
            _normalize_schema_version(self.schema_version),
        )
        object.__setattr__(
            self,
            "payload",
            copy_json_safe(
                self.payload,
                field_name="inline payload",
                max_encoded_bytes=INLINE_PAYLOAD_MAX_BYTES,
            ),
        )

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        catalog: DataTypeCatalog | None = None,
    ) -> TypedInlineValue | None:
        if (
            str(payload.get(_RUNTIME_VALUE_MARKER_KEY, "")).strip()
            != _RUNTIME_TYPED_INLINE_MARKER_VALUE
        ):
            return None
        if catalog is None:
            raise DataTypeCatalogError(
                "an active data-type catalog is required for typed inline values"
            )
        _validate_payload_fields(
            payload,
            label="Typed inline payload",
            required=frozenset(
                {
                    _RUNTIME_VALUE_MARKER_KEY,
                    "data_type_id",
                    "schema_version",
                    "payload",
                }
            ),
        )
        value = cls(
            data_type_id=payload["data_type_id"],
            schema_version=payload["schema_version"],
            payload=payload["payload"],
        )
        catalog.validate_carrier(value.data_type_id, value)
        return value

    def to_payload(
        self,
        *,
        catalog: DataTypeCatalog | None = None,
    ) -> dict[str, Any]:
        if catalog is None:
            raise DataTypeCatalogError(
                "an active data-type catalog is required for typed inline values"
            )
        catalog.validate_carrier(self.data_type_id, self)
        return {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_TYPED_INLINE_MARKER_VALUE,
            "data_type_id": self.data_type_id,
            "schema_version": self.schema_version,
            "payload": copy_json_safe(
                self.payload,
                field_name="inline payload",
                max_encoded_bytes=INLINE_PAYLOAD_MAX_BYTES,
            ),
        }


@dataclass(slots=True, frozen=True)
class RuntimeArtifactRef:
    ref: str
    artifact_id: str
    scope: RuntimeArtifactScope
    data_type_id: str
    schema_version: int
    format: str
    size_bytes: int
    sha256: str
    provenance: str
    metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        parsed = parse_artifact_ref(self.ref)
        if self.scope == "managed":
            if not isinstance(parsed, ManagedArtifactRef):
                raise ValueError("Runtime artifact ref does not use the saved scheme")
            normalized_ref = parsed.as_string()
        elif self.scope == "staged":
            if not isinstance(parsed, StagedArtifactRef):
                raise ValueError("Runtime artifact ref does not use the temp scheme")
            normalized_ref = parsed.as_string()
        else:
            raise ValueError("Unsupported runtime artifact scope")

        if self.artifact_id != parsed.artifact_id:
            raise ValueError(
                "Runtime artifact ref artifact_id does not match the ref payload"
            )

        object.__setattr__(self, "ref", normalized_ref)
        object.__setattr__(
            self,
            "data_type_id",
            _normalize_data_type_id(self.data_type_id),
        )
        object.__setattr__(
            self,
            "schema_version",
            _normalize_schema_version(self.schema_version),
        )
        object.__setattr__(self, "format", _validate_artifact_format(self.format))
        object.__setattr__(
            self,
            "size_bytes",
            _validate_artifact_size_bytes(self.size_bytes),
        )
        object.__setattr__(self, "sha256", _validate_artifact_sha256(self.sha256))
        object.__setattr__(
            self,
            "provenance",
            _validate_artifact_provenance(self.provenance),
        )
        object.__setattr__(self, "metadata", _copy_metadata_mapping(self.metadata))

    @classmethod
    def managed(
        cls,
        artifact_id: str,
        *,
        data_type_id: str,
        schema_version: int,
        format: str,
        size_bytes: int,
        sha256: str,
        provenance: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeArtifactRef:
        try:
            ref = format_managed_artifact_ref(artifact_id)
        except ValueError:
            raise ValueError(
                "artifact_id must be a valid artifact identifier"
            ) from None
        return cls(
            ref=ref,
            artifact_id=str(artifact_id).strip(),
            scope="managed",
            data_type_id=data_type_id,
            schema_version=schema_version,
            format=format,
            size_bytes=size_bytes,
            sha256=sha256,
            provenance=provenance,
            metadata=_copy_metadata_mapping(metadata),
        )

    @classmethod
    def staged(
        cls,
        artifact_id: str,
        *,
        data_type_id: str,
        schema_version: int,
        format: str,
        size_bytes: int,
        sha256: str,
        provenance: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeArtifactRef:
        try:
            ref = format_staged_artifact_ref(artifact_id)
        except ValueError:
            raise ValueError(
                "artifact_id must be a valid artifact identifier"
            ) from None
        return cls(
            ref=ref,
            artifact_id=str(artifact_id).strip(),
            scope="staged",
            data_type_id=data_type_id,
            schema_version=schema_version,
            format=format,
            size_bytes=size_bytes,
            sha256=sha256,
            provenance=provenance,
            metadata=_copy_metadata_mapping(metadata),
        )

    @classmethod
    def from_artifact_ref(
        cls,
        value: object,
        *,
        data_type_id: str,
        schema_version: int,
        format: str,
        size_bytes: int,
        sha256: str,
        provenance: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> RuntimeArtifactRef:
        parsed = parse_artifact_ref(value)
        if isinstance(parsed, ManagedArtifactRef):
            return cls.managed(
                parsed.artifact_id,
                data_type_id=data_type_id,
                schema_version=schema_version,
                format=format,
                size_bytes=size_bytes,
                sha256=sha256,
                provenance=provenance,
                metadata=metadata,
            )
        if isinstance(parsed, StagedArtifactRef):
            return cls.staged(
                parsed.artifact_id,
                data_type_id=data_type_id,
                schema_version=schema_version,
                format=format,
                size_bytes=size_bytes,
                sha256=sha256,
                provenance=provenance,
                metadata=metadata,
            )
        raise ValueError("Unsupported runtime artifact ref value")

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        catalog: DataTypeCatalog | None = None,
    ) -> RuntimeArtifactRef | None:
        if (
            str(payload.get(_RUNTIME_VALUE_MARKER_KEY, "")).strip()
            != _RUNTIME_ARTIFACT_MARKER_VALUE
        ):
            return None
        if catalog is None:
            raise DataTypeCatalogError(
                "an active data-type catalog is required for runtime artifact refs"
            )
        _validate_payload_fields(
            payload,
            label="Runtime artifact ref payload",
            required=frozenset(
                {
                    _RUNTIME_VALUE_MARKER_KEY,
                    "data_type_id",
                    "schema_version",
                    "ref",
                    "artifact_id",
                    "scope",
                    "format",
                    "size_bytes",
                    "sha256",
                    "provenance",
                }
            ),
            optional=frozenset({"metadata"}),
        )
        metadata = payload.get("metadata")
        ref_value = str(payload["ref"]).strip()
        if not ref_value:
            raise ValueError("Runtime artifact ref payload is missing ref")
        payload_scope = str(payload["scope"]).strip()
        if not payload_scope:
            raise ValueError("Runtime artifact ref payload scope must be non-empty")
        payload_artifact_id = str(payload["artifact_id"]).strip()
        if not payload_artifact_id:
            raise ValueError(
                "Runtime artifact ref payload artifact_id must be non-empty"
            )
        runtime_ref = cls.from_artifact_ref(
            ref_value,
            data_type_id=payload["data_type_id"],
            schema_version=payload["schema_version"],
            format=payload["format"],
            size_bytes=payload["size_bytes"],
            sha256=payload["sha256"],
            provenance=payload["provenance"],
            metadata=metadata,
        )
        if payload_scope != runtime_ref.scope:
            raise ValueError(
                "Runtime artifact ref payload scope does not match the ref value"
            )
        if payload_artifact_id != runtime_ref.artifact_id:
            raise ValueError(
                "Runtime artifact ref payload artifact_id does not match the ref value"
            )
        catalog.validate_carrier(runtime_ref.data_type_id, runtime_ref)
        return runtime_ref

    def to_payload(
        self,
        *,
        catalog: DataTypeCatalog | None = None,
    ) -> dict[str, Any]:
        if catalog is None:
            raise DataTypeCatalogError(
                "an active data-type catalog is required for runtime artifact refs"
            )
        catalog.validate_carrier(self.data_type_id, self)
        payload: dict[str, Any] = {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_ARTIFACT_MARKER_VALUE,
            "ref": self.ref,
            "artifact_id": self.artifact_id,
            "scope": self.scope,
            "data_type_id": self.data_type_id,
            "schema_version": self.schema_version,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "provenance": self.provenance,
        }
        if self.metadata:
            payload["metadata"] = _copy_metadata_mapping(self.metadata)
        return payload

    def __str__(self) -> str:
        return self.ref

    def to_descriptor(self) -> dict[str, Any]:
        return {
            "data_type_id": self.data_type_id,
            "schema_version": self.schema_version,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "provenance": self.provenance,
        }


@dataclass(slots=True, frozen=True)
class RuntimeHandleRef:
    data_type_id: str
    schema_version: int
    handle_id: str
    kind: str
    owner_scope: str
    worker_generation: int
    metadata: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "data_type_id",
            _normalize_data_type_id(self.data_type_id),
        )
        object.__setattr__(
            self,
            "schema_version",
            _normalize_schema_version(self.schema_version),
        )
        object.__setattr__(
            self,
            "handle_id",
            _normalize_required_runtime_string("handle_id", self.handle_id),
        )
        object.__setattr__(
            self, "kind", _normalize_required_runtime_string("kind", self.kind)
        )
        object.__setattr__(
            self,
            "owner_scope",
            _normalize_required_runtime_string("owner_scope", self.owner_scope),
        )
        object.__setattr__(
            self,
            "worker_generation",
            _normalize_worker_generation(self.worker_generation),
        )
        object.__setattr__(self, "metadata", _copy_metadata_mapping(self.metadata))

    @classmethod
    def from_payload(
        cls,
        payload: Mapping[str, Any],
        *,
        catalog: DataTypeCatalog | None = None,
    ) -> RuntimeHandleRef | None:
        if (
            str(payload.get(_RUNTIME_VALUE_MARKER_KEY, "")).strip()
            != _RUNTIME_HANDLE_MARKER_VALUE
        ):
            return None
        if catalog is None:
            raise DataTypeCatalogError(
                "an active data-type catalog is required for runtime handle refs"
            )
        _validate_payload_fields(
            payload,
            label="Runtime handle ref payload",
            required=frozenset(
                {
                    _RUNTIME_VALUE_MARKER_KEY,
                    "data_type_id",
                    "schema_version",
                    "handle_id",
                    "kind",
                    "owner_scope",
                    "worker_generation",
                }
            ),
            optional=frozenset({"metadata"}),
        )
        value = cls(
            data_type_id=payload["data_type_id"],
            schema_version=payload["schema_version"],
            handle_id=payload.get("handle_id", ""),
            kind=payload.get("kind", ""),
            owner_scope=payload.get("owner_scope", ""),
            worker_generation=payload.get("worker_generation", 0),
            metadata=payload.get("metadata"),
        )
        catalog.validate_carrier(value.data_type_id, value)
        return value

    def to_payload(
        self,
        *,
        catalog: DataTypeCatalog | None = None,
    ) -> dict[str, Any]:
        if catalog is None:
            raise DataTypeCatalogError(
                "an active data-type catalog is required for runtime handle refs"
            )
        catalog.validate_carrier(self.data_type_id, self)
        payload: dict[str, Any] = {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_HANDLE_MARKER_VALUE,
            "data_type_id": self.data_type_id,
            "schema_version": self.schema_version,
            "handle_id": self.handle_id,
            "kind": self.kind,
            "owner_scope": self.owner_scope,
            "worker_generation": self.worker_generation,
        }
        if self.metadata:
            payload["metadata"] = _copy_metadata_mapping(self.metadata)
        return payload


def coerce_runtime_artifact_ref(
    value: object,
    *,
    catalog: DataTypeCatalog | None = None,
) -> RuntimeArtifactRef | None:
    if isinstance(value, RuntimeArtifactRef):
        return value
    if isinstance(value, Mapping):
        return RuntimeArtifactRef.from_payload(value, catalog=catalog)
    return None


def coerce_runtime_handle_ref(
    value: object,
    *,
    catalog: DataTypeCatalog | None = None,
) -> RuntimeHandleRef | None:
    if isinstance(value, RuntimeHandleRef):
        return value
    if isinstance(value, Mapping):
        return RuntimeHandleRef.from_payload(value, catalog=catalog)
    return None


RuntimeValueRef: TypeAlias = (
    TypedInlineValue
    | ImageValue
    | RuntimeArtifactRef
    | RuntimeHandleRef
    | TabularDataRef
    | ArrayDataRef
    | TabularWindowRef
    | ArraySlice2DRef
)


def _extract_runtime_marker(payload: Mapping[str, Any]) -> str | None:
    if _RUNTIME_VALUE_MARKER_KEY not in payload:
        return None
    marker = payload.get(_RUNTIME_VALUE_MARKER_KEY)
    if not isinstance(marker, str):
        raise ValueError("Runtime value marker must be a non-empty string")
    normalized_marker = marker.strip()
    if not normalized_marker:
        raise ValueError("Runtime value marker must be a non-empty string")
    return normalized_marker


def _coerce_runtime_value_ref(
    payload: Mapping[str, Any],
    *,
    catalog: DataTypeCatalog | None,
) -> RuntimeValueRef | None:
    marker = _extract_runtime_marker(payload)
    if marker is None:
        return None
    if marker == _RUNTIME_TYPED_INLINE_MARKER_VALUE:
        runtime_value = TypedInlineValue.from_payload(payload, catalog=catalog)
        if runtime_value is None:
            raise ValueError("Typed inline payload is incomplete")
        return runtime_value
    if marker == _RUNTIME_IMAGE_MARKER_VALUE:
        image = ImageValue.from_payload(payload, catalog=catalog)
        if image is None:
            raise ValueError("ImageValue payload is incomplete")
        return image
    if marker == _RUNTIME_ARTIFACT_MARKER_VALUE:
        runtime_ref = coerce_runtime_artifact_ref(payload, catalog=catalog)
        if runtime_ref is None:
            raise ValueError("Runtime artifact ref payload is incomplete")
        return runtime_ref
    if marker == _RUNTIME_HANDLE_MARKER_VALUE:
        runtime_ref = coerce_runtime_handle_ref(payload, catalog=catalog)
        if runtime_ref is None:
            raise ValueError("Runtime handle ref payload is incomplete")
        return runtime_ref
    if marker == TABULAR_DATA_REF_MARKER_VALUE:
        runtime_ref = coerce_tabular_data_ref(payload)
        if runtime_ref is None:
            raise ValueError("Tabular data ref payload is incomplete")
        return runtime_ref
    if marker == ARRAY_DATA_REF_MARKER_VALUE:
        runtime_ref = coerce_array_data_ref(payload)
        if runtime_ref is None:
            raise ValueError("Array data ref payload is incomplete")
        return runtime_ref
    if marker == TABULAR_WINDOW_REF_MARKER_VALUE:
        runtime_ref = coerce_tabular_window_ref(payload)
        if runtime_ref is None:
            raise ValueError("Tabular window ref payload is incomplete")
        return runtime_ref
    if marker == ARRAY_SLICE_2D_REF_MARKER_VALUE:
        runtime_ref = coerce_array_slice_2d_ref(payload)
        if runtime_ref is None:
            raise ValueError("Array slice 2D ref payload is incomplete")
        return runtime_ref
    raise ValueError(f"Unsupported runtime value marker: {marker!r}")


def _serialize_data_tree(
    value: DataTree,
    *,
    depth: int,
    catalog: DataTypeCatalog | None,
) -> dict[str, Any]:
    return {
        _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_DATA_TREE_MARKER_VALUE,
        "branches": [
            {
                "path": list(path),
                "items": [
                    _serialize_runtime_value(
                        item,
                        depth=depth + 1,
                        catalog=catalog,
                    )
                    for item in items
                ],
            }
            for path, items in value.branches
        ],
    }


def _deserialize_data_tree(
    payload: Mapping[str, Any],
    *,
    depth: int,
    catalog: DataTypeCatalog | None,
) -> DataTree:
    _validate_payload_fields(
        payload,
        label="DataTree runtime payload",
        required=frozenset({_RUNTIME_VALUE_MARKER_KEY, "branches"}),
    )
    raw_branches = payload.get("branches")
    if isinstance(raw_branches, (str, bytes, bytearray)) or not isinstance(
        raw_branches, list
    ):
        raise ValueError("DataTree runtime payload branches must be a list")
    branches: list[tuple[tuple[int, ...], tuple[Any, ...]]] = []
    for raw_branch in raw_branches:
        if not isinstance(raw_branch, Mapping):
            raise ValueError("DataTree runtime payload branches must be mappings")
        _validate_payload_fields(
            raw_branch,
            label="DataTree runtime branch",
            required=frozenset({"path", "items"}),
        )
        raw_path = raw_branch.get("path")
        raw_items = raw_branch.get("items")
        if isinstance(raw_path, (str, bytes, bytearray)) or not isinstance(
            raw_path, list
        ):
            raise ValueError("DataTree runtime payload paths must be lists")
        if isinstance(raw_items, (str, bytes, bytearray)) or not isinstance(
            raw_items, list
        ):
            raise ValueError("DataTree runtime payload items must be lists")
        branches.append(
            (
                tuple(raw_path),
                tuple(
                    _deserialize_runtime_value(
                        item,
                        depth=depth + 1,
                        catalog=catalog,
                    )
                    for item in raw_items
                ),
            )
        )
    return DataTree(branches)


def _serialize_interval_1d(value: Interval1D) -> dict[str, Any]:
    return {
        _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_INTERVAL_1D_MARKER_VALUE,
        "start": value.start,
        "end": value.end,
    }


def _deserialize_interval_1d(payload: Mapping[str, Any]) -> Interval1D:
    expected_keys = {_RUNTIME_VALUE_MARKER_KEY, "start", "end"}
    missing_keys = expected_keys.difference(payload)
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ValueError(f"Interval 1D runtime payload is missing: {missing}")
    unexpected_keys = set(payload).difference(expected_keys)
    if unexpected_keys:
        unexpected = ", ".join(sorted(str(key) for key in unexpected_keys))
        raise ValueError(
            f"Interval 1D runtime payload has unexpected fields: {unexpected}"
        )
    return Interval1D(start=payload["start"], end=payload["end"])


def _runtime_semantic_type_id(value: object) -> str:
    if isinstance(value, ImageValue):
        return IMAGE_VALUE_DATA_TYPE_ID
    if isinstance(value, TypedInlineValue):
        return value.data_type_id
    if isinstance(value, RuntimeArtifactRef):
        return value.data_type_id
    if isinstance(value, RuntimeHandleRef):
        return value.data_type_id
    if isinstance(value, TabularDataRef):
        return TABULAR_DATA_REF_TYPE_ID
    if isinstance(value, ArrayDataRef):
        return ARRAY_DATA_REF_TYPE_ID
    if isinstance(value, TabularWindowRef):
        return TABULAR_WINDOW_REF_TYPE_ID
    if isinstance(value, ArraySlice2DRef):
        return ARRAY_SLICE_2D_REF_TYPE_ID
    if isinstance(value, Interval1D):
        return INTERVAL_1D_GRAPH_DATA_TYPE_ID
    return ""


def _requires_active_catalog(value: object) -> bool:
    if isinstance(
        value,
        (TypedInlineValue, ImageValue, RuntimeArtifactRef, RuntimeHandleRef),
    ):
        return True
    if isinstance(value, DataTree):
        return any(
            _requires_active_catalog(item)
            for _path, items in value.branches
            for item in items
        )
    if isinstance(value, Mapping):
        marker = _extract_runtime_marker(value)
        if marker in {
            _RUNTIME_TYPED_INLINE_MARKER_VALUE,
            _RUNTIME_IMAGE_MARKER_VALUE,
            _RUNTIME_ARTIFACT_MARKER_VALUE,
            _RUNTIME_HANDLE_MARKER_VALUE,
        }:
            return True
        return any(_requires_active_catalog(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_requires_active_catalog(item) for item in value)
    return False


def _validate_catalog_value(
    value: object,
    *,
    catalog: DataTypeCatalog,
    declared_type_id: str,
) -> None:
    if isinstance(value, DataTree):
        for _path, items in value.branches:
            for item in items:
                if isinstance(item, DataTree):
                    raise DataTypeCatalogError(
                        "nested DataTree runtime values are not supported"
                    )
                _validate_catalog_value(
                    item,
                    catalog=catalog,
                    declared_type_id=declared_type_id,
                )
        return
    semantic_type_id = _runtime_semantic_type_id(value)
    if semantic_type_id:
        catalog.validate_carrier(declared_type_id or semantic_type_id, value)
        return
    if declared_type_id:
        catalog.validate_carrier(declared_type_id, value)
    if isinstance(value, Mapping):
        nested_values = value.values()
    elif isinstance(value, (list, tuple)):
        nested_values = value
    else:
        return
    for item in nested_values:
        _validate_catalog_value(
            item,
            catalog=catalog,
            declared_type_id="",
        )


def _serialize_runtime_value(
    value: Any,
    *,
    depth: int,
    catalog: DataTypeCatalog | None,
) -> Any:
    if depth > JSON_MAX_DEPTH:
        raise ValueError(f"runtime value exceeds maximum JSON depth {JSON_MAX_DEPTH}")
    if isinstance(value, DataTree):
        return _serialize_data_tree(
            value,
            depth=depth,
            catalog=catalog,
        )
    if isinstance(value, Interval1D):
        return _serialize_interval_1d(value)
    if isinstance(
        value,
        (
            TypedInlineValue,
            ImageValue,
            RuntimeArtifactRef,
            RuntimeHandleRef,
            TabularDataRef,
            ArrayDataRef,
            TabularWindowRef,
            ArraySlice2DRef,
        ),
    ):
        if isinstance(
            value,
            (TypedInlineValue, ImageValue, RuntimeArtifactRef, RuntimeHandleRef),
        ):
            return value.to_payload(catalog=catalog)
        return value.to_payload()
    if isinstance(value, Mapping):
        marker = _extract_runtime_marker(value)
        if marker == _RUNTIME_DATA_TREE_MARKER_VALUE:
            return _serialize_data_tree(
                _deserialize_data_tree(
                    value,
                    depth=depth,
                    catalog=catalog,
                ),
                depth=depth,
                catalog=catalog,
            )
        if marker == _RUNTIME_INTERVAL_1D_MARKER_VALUE:
            return _serialize_interval_1d(_deserialize_interval_1d(value))
        payload_ref = (
            None
            if marker in _OPAQUE_MAPPING_RUNTIME_MARKERS
            else _coerce_runtime_value_ref(value, catalog=catalog)
        )
        if payload_ref is not None:
            if isinstance(
                payload_ref,
                (TypedInlineValue, ImageValue, RuntimeArtifactRef, RuntimeHandleRef),
            ):
                return payload_ref.to_payload(catalog=catalog)
            return payload_ref.to_payload()
        copied: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("runtime value mapping keys must be strings")
            copied[key] = _serialize_runtime_value(
                item,
                depth=depth + 1,
                catalog=catalog,
            )
        return copied
    if isinstance(value, (list, tuple)):
        return [
            _serialize_runtime_value(
                item,
                depth=depth + 1,
                catalog=catalog,
            )
            for item in value
        ]
    return copy_json_safe(value, field_name="runtime value")


def serialize_runtime_value(
    value: Any,
    *,
    catalog: DataTypeCatalog | None = None,
    declared_type_id: str = "",
) -> Any:
    if catalog is None and (declared_type_id or _requires_active_catalog(value)):
        raise DataTypeCatalogError(
            "an active data-type catalog is required for semantic runtime carriers"
        )
    if catalog is not None and declared_type_id:
        _validate_catalog_value(
            value,
            catalog=catalog,
            declared_type_id=declared_type_id,
        )
    serialized = _serialize_runtime_value(
        value,
        depth=0,
        catalog=catalog,
    )
    serialized = copy_json_safe(
        serialized,
        field_name="runtime value",
        max_depth=JSON_MAX_DEPTH,
    )
    if catalog is not None:
        restored = _deserialize_runtime_value(
            serialized,
            depth=0,
            catalog=catalog,
        )
        _validate_catalog_value(
            restored,
            catalog=catalog,
            declared_type_id=declared_type_id,
        )
    return serialized


def _deserialize_runtime_value(
    value: Any,
    *,
    depth: int,
    catalog: DataTypeCatalog | None,
) -> Any:
    if depth > JSON_MAX_DEPTH:
        raise ValueError(f"runtime value exceeds maximum JSON depth {JSON_MAX_DEPTH}")
    if isinstance(value, Mapping):
        marker = _extract_runtime_marker(value)
        if marker == _RUNTIME_DATA_TREE_MARKER_VALUE:
            return _deserialize_data_tree(
                value,
                depth=depth,
                catalog=catalog,
            )
        if marker == _RUNTIME_INTERVAL_1D_MARKER_VALUE:
            return _deserialize_interval_1d(value)
        payload_ref = (
            None
            if marker in _OPAQUE_MAPPING_RUNTIME_MARKERS
            else _coerce_runtime_value_ref(value, catalog=catalog)
        )
        if payload_ref is not None:
            return payload_ref
        copied: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("runtime value mapping keys must be strings")
            copied[key] = _deserialize_runtime_value(
                item,
                depth=depth + 1,
                catalog=catalog,
            )
        return copied
    if isinstance(value, (list, tuple)):
        return [
            _deserialize_runtime_value(
                item,
                depth=depth + 1,
                catalog=catalog,
            )
            for item in value
        ]
    return copy_json_safe(value, field_name="runtime value")


def deserialize_runtime_value(
    value: Any,
    *,
    catalog: DataTypeCatalog | None = None,
    declared_type_id: str = "",
) -> Any:
    safe_value = copy_json_safe(
        value,
        field_name="runtime value",
        max_depth=JSON_MAX_DEPTH,
    )
    if catalog is None and (declared_type_id or _requires_active_catalog(safe_value)):
        raise DataTypeCatalogError(
            "an active data-type catalog is required for semantic runtime carriers"
        )
    restored = _deserialize_runtime_value(
        safe_value,
        depth=0,
        catalog=catalog,
    )
    if catalog is not None:
        _validate_catalog_value(
            restored,
            catalog=catalog,
            declared_type_id=declared_type_id,
        )
    return restored


def _durable_type_is_eligible(catalog: DataTypeCatalog, type_id: str) -> bool:
    try:
        spec = catalog.require(type_id)
    except (KeyError, TypeError, ValueError, DataTypeCatalogError):
        return False
    return spec.persistence != "never" and spec.sensitivity == "normal"


def _durable_semantic_carrier_is_eligible(
    catalog: DataTypeCatalog,
    *,
    actual_type_id: str,
    declared_type_id: str,
    carrier: str,
    schema_version: int | None,
) -> bool:
    try:
        actual = catalog.require(actual_type_id)
        declared = catalog.require(declared_type_id)
    except (KeyError, TypeError, ValueError, DataTypeCatalogError):
        return False
    return bool(
        actual.persistence != "never"
        and actual.sensitivity == "normal"
        and declared.persistence != "never"
        and declared.sensitivity == "normal"
        and carrier in actual.carriers
        and carrier in declared.carriers
        and catalog.is_assignable(actual_type_id, declared_type_id)
        and (
            schema_version is None
            or schema_version == actual.payload_schema_version
        )
    )


def _durable_string_is_private_path(value: str) -> bool:
    normalized = value.strip()
    portable = normalized.replace("\\", "/")
    parts = tuple(
        part.casefold()
        for part in portable.split("/")
        if part not in {"", "."}
    )
    return bool(
        normalized.casefold().startswith(("temp://", "saved://"))
        or _PRIVATE_PATH_PATTERN.match(normalized)
        or _DRIVE_RELATIVE_PATH_PATTERN.match(normalized)
        or _HOME_PATH_PATTERN.match(normalized)
        or _ENVIRONMENT_PATH_PATTERN.match(normalized)
        or os.path.isabs(normalized)
        or ".." in parts
        or (
            len(parts) > 1
            and parts[0] in _DURABLE_PRIVATE_RELATIVE_ROOTS
        )
    )


def _validate_durable_value(
    value: Any,
    *,
    catalog: DataTypeCatalog,
    artifact_context: Any,
    depth: int,
    declared_type_id: str = "",
) -> str:
    if depth > JSON_MAX_DEPTH:
        return "durable_value_ineligible"
    value_type = type(value)
    if value is None or value_type in {bool, int}:
        return ""
    if value_type is float:
        return "" if math.isfinite(value) else "durable_value_ineligible"
    if value_type is str:
        return (
            "durable_value_ineligible"
            if _durable_string_is_private_path(value)
            else ""
        )
    if value_type is RuntimeArtifactRef:
        if value.scope != "managed":
            return "durable_artifact_invalid"
        if not declared_type_id or not _durable_semantic_carrier_is_eligible(
            catalog,
            actual_type_id=value.data_type_id,
            declared_type_id=declared_type_id,
            carrier="artifact",
            schema_version=value.schema_version,
        ):
            return "durable_artifact_invalid"
        metadata_reason = _validate_durable_value(
            value.metadata,
            catalog=catalog,
            artifact_context=artifact_context,
            depth=depth + 1,
        )
        if metadata_reason:
            return metadata_reason
        inspector = getattr(artifact_context, "inspect_durable_artifact", None)
        if not callable(inspector):
            return "durable_artifact_invalid"
        try:
            inspector(value)
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError):
            return "durable_artifact_invalid"
        return ""
    if value_type in {
        RuntimeHandleRef,
        TabularDataRef,
        ArrayDataRef,
        TabularWindowRef,
        ArraySlice2DRef,
    }:
        return "durable_value_ineligible"
    if value_type is ImageValue:
        if not declared_type_id or not _durable_semantic_carrier_is_eligible(
            catalog,
            actual_type_id=value.data_type_id,
            declared_type_id=declared_type_id,
            carrier="inline",
            schema_version=value.schema_version,
        ):
            return "durable_value_ineligible"
        try:
            encoded = json.dumps(
                _durable_inline_payload(value),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        except (AttributeError, TypeError, ValueError):
            return "durable_value_ineligible"
        return "" if len(encoded) <= INLINE_PAYLOAD_MAX_BYTES else "durable_value_ineligible"
    if value_type is TypedInlineValue:
        if not declared_type_id or not _durable_semantic_carrier_is_eligible(
            catalog,
            actual_type_id=value.data_type_id,
            declared_type_id=declared_type_id,
            carrier="inline",
            schema_version=value.schema_version,
        ):
            return "durable_value_ineligible"
        return _validate_durable_value(
            value.payload,
            catalog=catalog,
            artifact_context=artifact_context,
            depth=depth + 1,
        )
    if value_type is Interval1D:
        return (
            ""
            if declared_type_id
            and _durable_semantic_carrier_is_eligible(
                catalog,
                actual_type_id=INTERVAL_1D_GRAPH_DATA_TYPE_ID,
                declared_type_id=declared_type_id,
                carrier="inline",
                schema_version=1,
            )
            else "durable_value_ineligible"
        )
    if value_type is DataTree:
        for _path, items in value.branches:
            for item in items:
                reason = _validate_durable_value(
                    item,
                    catalog=catalog,
                    artifact_context=artifact_context,
                    depth=depth + 1,
                )
                if reason:
                    return reason
        return ""
    if value_type in {list, tuple}:
        for item in value:
            reason = _validate_durable_value(
                item,
                catalog=catalog,
                artifact_context=artifact_context,
                depth=depth + 1,
            )
            if reason:
                return reason
        return ""
    if value_type is dict:
        marker = value.get(_RUNTIME_VALUE_MARKER_KEY)
        if marker is not None:
            return "durable_value_ineligible"
        for key, item in value.items():
            if type(key) is not str or _durable_string_is_private_path(key):
                return "durable_value_ineligible"
            reason = _validate_durable_value(
                item,
                catalog=catalog,
                artifact_context=artifact_context,
                depth=depth + 1,
            )
            if reason:
                return reason
        return ""
    return "durable_value_ineligible"


def _durable_item_type_and_kind(
    value: Any,
    declared_type_id: str,
) -> tuple[str, str]:
    value_type = type(value)
    if value_type is RuntimeArtifactRef:
        return value.data_type_id, "artifact_ref"
    if value_type in {
        RuntimeHandleRef,
        TabularDataRef,
        ArrayDataRef,
        TabularWindowRef,
        ArraySlice2DRef,
    }:
        return "", "forbidden"
    if value_type in {TypedInlineValue, ImageValue}:
        return value.data_type_id, "inline"
    if value_type is Interval1D:
        return INTERVAL_1D_GRAPH_DATA_TYPE_ID, "inline"
    return declared_type_id, "inline"


def _durable_inline_payload(value: Any, *, depth: int = 0) -> Any:
    if depth > JSON_MAX_DEPTH:
        raise ValueError("durable inline value exceeds the depth limit")
    value_type = type(value)
    if value is None or value_type in {bool, int}:
        return value
    if value_type is str:
        if _durable_string_is_private_path(value):
            raise ValueError("durable value contains a private path")
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError("durable inline value contains a non-finite number")
        return value
    if value_type is ImageValue:
        if len(value.encoded_bytes) > INLINE_PAYLOAD_MAX_BYTES:
            raise ValueError("durable image exceeds the inline limit")
        return {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_IMAGE_MARKER_VALUE,
            "data_type_id": value.data_type_id,
            "schema_version": value.schema_version,
            "format": value.format,
            "width": value.width,
            "height": value.height,
            "sha256": value.sha256,
            "encoded_base64": base64.b64encode(value.encoded_bytes).decode("ascii"),
        }
    if value_type is RuntimeArtifactRef:
        payload = {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_ARTIFACT_MARKER_VALUE,
            "ref": value.ref,
            "artifact_id": value.artifact_id,
            "scope": value.scope,
            "data_type_id": value.data_type_id,
            "schema_version": value.schema_version,
            "format": value.format,
            "size_bytes": value.size_bytes,
            "sha256": value.sha256,
            "provenance": value.provenance,
        }
        if value.metadata:
            payload["metadata"] = _durable_inline_payload(
                value.metadata,
                depth=depth + 1,
            )
        return payload
    if value_type in {
        RuntimeHandleRef,
        TabularDataRef,
        ArrayDataRef,
        TabularWindowRef,
        ArraySlice2DRef,
    }:
        raise ValueError(
            "durable accepted outputs cannot contain session-only carriers"
        )
    if value_type is TypedInlineValue:
        return {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_TYPED_INLINE_MARKER_VALUE,
            "data_type_id": value.data_type_id,
            "schema_version": value.schema_version,
            "payload": _durable_inline_payload(value.payload, depth=depth + 1),
        }
    if value_type is Interval1D:
        return {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_INTERVAL_1D_MARKER_VALUE,
            "start": value.start,
            "end": value.end,
        }
    if value_type is DataTree:
        return {
            _RUNTIME_VALUE_MARKER_KEY: _RUNTIME_DATA_TREE_MARKER_VALUE,
            "branches": [
                {
                    "path": list(path),
                    "items": [
                        _durable_inline_payload(item, depth=depth + 1)
                        for item in items
                    ],
                }
                for path, items in value.branches
            ],
        }
    if value_type in {list, tuple}:
        return [
            _durable_inline_payload(item, depth=depth + 1)
            for item in value
        ]
    if value_type is dict:
        if any(
            type(key) is not str or _durable_string_is_private_path(key)
            for key in value
        ):
            raise ValueError("durable mapping key contains a private path")
        return {
            key: _durable_inline_payload(item, depth=depth + 1)
            for key, item in value.items()
        }
    raise TypeError("durable inline value contains an unsupported carrier")


def _durable_runtime_value_from_payload(value: Any, *, depth: int = 0) -> Any:
    if depth > JSON_MAX_DEPTH:
        raise ValueError("durable runtime value exceeds the depth limit")
    value_type = type(value)
    if value is None or value_type in {str, bool, int}:
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError("durable runtime value contains a non-finite number")
        return value
    if value_type is list:
        return [
            _durable_runtime_value_from_payload(item, depth=depth + 1)
            for item in value
        ]
    if value_type is not dict:
        raise TypeError("durable runtime value contains an unsupported value")
    marker = value.get(_RUNTIME_VALUE_MARKER_KEY)
    if marker is None:
        if any(type(key) is not str for key in value):
            raise TypeError("durable runtime mapping keys must be strings")
        return {
            key: _durable_runtime_value_from_payload(item, depth=depth + 1)
            for key, item in value.items()
        }
    if marker == _RUNTIME_DATA_TREE_MARKER_VALUE:
        _validate_payload_fields(
            value,
            label="durable DataTree",
            required=frozenset({_RUNTIME_VALUE_MARKER_KEY, "branches"}),
        )
        branches = value["branches"]
        if type(branches) is not list:
            raise TypeError("durable DataTree branches must be a list")
        decoded_branches = []
        for branch in branches:
            if type(branch) is not dict:
                raise TypeError("durable DataTree branch must be a mapping")
            _validate_payload_fields(
                branch,
                label="durable DataTree branch",
                required=frozenset({"path", "items"}),
            )
            if type(branch["path"]) is not list or type(branch["items"]) is not list:
                raise TypeError("durable DataTree path/items must be lists")
            decoded_branches.append(
                (
                    tuple(branch["path"]),
                    tuple(
                        _durable_runtime_value_from_payload(
                            item,
                            depth=depth + 1,
                        )
                        for item in branch["items"]
                    ),
                )
            )
        return DataTree(decoded_branches)
    if marker == _RUNTIME_INTERVAL_1D_MARKER_VALUE:
        _validate_payload_fields(
            value,
            label="durable Interval1D",
            required=frozenset({_RUNTIME_VALUE_MARKER_KEY, "start", "end"}),
        )
        return Interval1D(start=value["start"], end=value["end"])
    if marker == _RUNTIME_TYPED_INLINE_MARKER_VALUE:
        _validate_payload_fields(
            value,
            label="durable TypedInlineValue",
            required=frozenset(
                {
                    _RUNTIME_VALUE_MARKER_KEY,
                    "data_type_id",
                    "schema_version",
                    "payload",
                }
            ),
        )
        return TypedInlineValue(
            data_type_id=value["data_type_id"],
            schema_version=value["schema_version"],
            payload=value["payload"],
        )
    if marker == _RUNTIME_IMAGE_MARKER_VALUE:
        _validate_payload_fields(
            value,
            label="durable ImageValue",
            required=frozenset(
                {
                    _RUNTIME_VALUE_MARKER_KEY,
                    "data_type_id",
                    "schema_version",
                    "format",
                    "width",
                    "height",
                    "sha256",
                    "encoded_base64",
                }
            ),
        )
        if value["data_type_id"] != IMAGE_VALUE_DATA_TYPE_ID:
            raise ValueError("durable ImageValue data type is invalid")
        encoded = value["encoded_base64"]
        if type(encoded) is not str or len(encoded) > IMAGE_VALUE_MAX_ENCODED_BYTES:
            raise ValueError("durable ImageValue payload is oversized")
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("durable ImageValue payload is invalid") from exc
        return ImageValue(
            encoded_bytes=image_bytes,
            format=value["format"],
            width=value["width"],
            height=value["height"],
            sha256=value["sha256"],
            schema_version=value["schema_version"],
        )
    if marker == _RUNTIME_ARTIFACT_MARKER_VALUE:
        _validate_payload_fields(
            value,
            label="durable RuntimeArtifactRef",
            required=frozenset(
                {
                    _RUNTIME_VALUE_MARKER_KEY,
                    "ref",
                    "artifact_id",
                    "scope",
                    "data_type_id",
                    "schema_version",
                    "format",
                    "size_bytes",
                    "sha256",
                    "provenance",
                }
            ),
            optional=frozenset({"metadata"}),
        )
        return RuntimeArtifactRef(
            ref=value["ref"],
            artifact_id=value["artifact_id"],
            scope=value["scope"],
            data_type_id=value["data_type_id"],
            schema_version=value["schema_version"],
            format=value["format"],
            size_bytes=value["size_bytes"],
            sha256=value["sha256"],
            provenance=value["provenance"],
            metadata=value.get("metadata"),
        )
    raise ValueError("durable runtime value marker is unsupported")


def durable_settled_outputs_from_payload(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Decode durable settled outputs structurally without catalog callbacks."""

    from ea_node_editor.runtime_contracts.settled_results import (
        MAX_OUTPUTS_PER_NODE,
        SettledPortResult,
    )

    if type(payload) is not dict:
        raise TypeError("durable settled outputs must be a mapping")
    if len(payload) > MAX_OUTPUTS_PER_NODE:
        raise ValueError("durable settled outputs exceed the output limit")
    outputs: dict[str, SettledPortResult] = {}
    for port_key, result_payload in payload.items():
        if (
            type(port_key) is not str
            or not port_key
            or port_key != port_key.strip()
            or type(result_payload) is not dict
        ):
            raise ValueError("durable settled output entry is invalid")
        _validate_payload_fields(
            result_payload,
            label="durable settled output",
            required=frozenset({"status", "value", "errors"}),
        )
        status = result_payload["status"]
        if status not in {"value", "empty"} or result_payload["errors"] != []:
            raise ValueError("durable settled output status/errors are invalid")
        value = (
            _durable_runtime_value_from_payload(result_payload["value"])
            if status == "value"
            else None
        )
        if status == "empty" and result_payload["value"] is not None:
            raise ValueError("empty durable settled output cannot carry a value")
        outputs[port_key] = SettledPortResult(status=status, value=value)
    normalized = durable_settled_outputs_to_payload(outputs)
    if normalized != payload:
        raise ValueError("durable settled outputs are not canonical")
    return outputs


def durable_settled_outputs_to_payload(
    outputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Encode validated durable settled outputs without catalog callbacks."""

    from ea_node_editor.runtime_contracts.settled_results import SettledPortResult

    if type(outputs) is not dict or any(
        type(port_key) is not str or not isinstance(result, SettledPortResult)
        for port_key, result in outputs.items()
    ):
        raise TypeError("durable settled outputs must contain settled results")
    return {
        port_key: {
            "status": result.status,
            "value": (
                _durable_inline_payload(result.value)
                if result.status == "value"
                else None
            ),
            "errors": [],
        }
        for port_key, result in sorted(outputs.items())
    }


def validate_durable_settled_outputs(
    outputs: Mapping[str, Any],
    descriptors: Any,
    catalog: DataTypeCatalog,
    artifact_context: Any,
) -> DurableRuntimeValueValidation:
    """Validate and canonically encode durable settled outputs without callbacks."""

    try:
        if not isinstance(outputs, Mapping) or not isinstance(descriptors, (list, tuple)):
            raise TypeError
        descriptors_by_port = {item.port_key: item for item in descriptors}
        if len(descriptors_by_port) != len(descriptors):
            raise ValueError
        if set(outputs) != set(descriptors_by_port):
            raise ValueError
        for port_key, result in outputs.items():
            if type(port_key) is not str:
                raise TypeError
            descriptor = descriptors_by_port[port_key]
            if result.status != descriptor.status:
                raise ValueError
            if result.status == "empty":
                continue
            if result.status != "value" or not isinstance(result.value, DataTree):
                raise ValueError
            type_ids = (descriptor.data_type_id, *descriptor.concrete_data_type_ids)
            if any(not _durable_type_is_eligible(catalog, type_id) for type_id in type_ids):
                return DurableRuntimeValueValidation(False, "durable_value_ineligible")
            if any(
                not catalog.is_assignable(type_id, descriptor.data_type_id)
                for type_id in descriptor.concrete_data_type_ids
            ):
                return DurableRuntimeValueValidation(False, "durable_value_ineligible")
            observed_types: set[str] = set()
            observed_kinds: set[str] = set()
            for _path, items in result.value.branches:
                for item in items:
                    actual_type_id, payload_kind = _durable_item_type_and_kind(
                        item,
                        descriptor.data_type_id,
                    )
                    if payload_kind == "forbidden":
                        return DurableRuntimeValueValidation(
                            False,
                            "durable_value_ineligible",
                        )
                    observed_types.add(actual_type_id)
                    observed_kinds.add(payload_kind)
                    reason = _validate_durable_value(
                        item,
                        catalog=catalog,
                        artifact_context=artifact_context,
                        depth=0,
                        declared_type_id=descriptor.data_type_id,
                    )
                    if reason:
                        return DurableRuntimeValueValidation(False, reason)
                    if payload_kind == "inline":
                        inline_payload = _durable_inline_payload(item)
                        if len(
                            json.dumps(
                                inline_payload,
                                allow_nan=False,
                                ensure_ascii=False,
                                separators=(",", ":"),
                                sort_keys=True,
                            ).encode("utf-8")
                        ) > INLINE_PAYLOAD_MAX_BYTES:
                            return DurableRuntimeValueValidation(
                                False,
                                "durable_value_ineligible",
                            )
            if not observed_types:
                observed_types.add(descriptor.data_type_id)
                observed_kinds.add("inline")
            if (
                tuple(sorted(observed_types))
                != descriptor.concrete_data_type_ids
                or tuple(sorted(observed_kinds)) != descriptor.payload_kinds
            ):
                return DurableRuntimeValueValidation(
                    False,
                    "durable_value_ineligible",
                )
        payload = {
            port_key: {
                "status": result.status,
                "value": (
                    _durable_inline_payload(result.value)
                    if result.status == "value"
                    else None
                ),
                "errors": [],
            }
            for port_key, result in sorted(outputs.items())
        }
        canonical = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if len(canonical) > 67_108_864:
            return DurableRuntimeValueValidation(False, "durable_value_ineligible")
        for port_key, descriptor in descriptors_by_port.items():
            if descriptor.status != "value":
                continue
            digest = hashlib.sha256(
                json.dumps(
                    {port_key: payload[port_key]},
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            if digest != descriptor.payload_digest:
                return DurableRuntimeValueValidation(False, "durable_value_ineligible")
        return DurableRuntimeValueValidation(
            True,
            "durable_value_eligible",
            canonical,
        )
    except (AttributeError, KeyError, TypeError, ValueError, DataTypeCatalogError):
        return DurableRuntimeValueValidation(False, "durable_value_ineligible")


__all__ = [
    "ArrayDataRef",
    "ArraySlice2DRef",
    "DataTree",
    "DurableRuntimeValueValidation",
    "IMAGE_VALUE_DATA_TYPE_ID",
    "IMAGE_VALUE_MAX_ENCODED_BYTES",
    "IMAGE_VALUE_SCHEMA_VERSION",
    "ImageValue",
    "RuntimeArtifactRef",
    "RuntimeArtifactScope",
    "RuntimeHandleRef",
    "RuntimeValueRef",
    "TabularDataRef",
    "TabularWindowRef",
    "TypedInlineValue",
    "coerce_array_data_ref",
    "coerce_array_slice_2d_ref",
    "coerce_runtime_artifact_ref",
    "coerce_runtime_handle_ref",
    "coerce_tabular_data_ref",
    "coerce_tabular_window_ref",
    "deserialize_runtime_value",
    "durable_settled_outputs_from_payload",
    "durable_settled_outputs_to_payload",
    "serialize_runtime_value",
    "validate_durable_settled_outputs",
]
