from __future__ import annotations

import dataclasses
import json
import os
import stat
import struct
import zlib
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QImage

import ea_node_editor.ui.image_value_preview_provider as image_preview_module
from ea_node_editor.execution.signal_plot_renderer import render_signal_plot
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.image_blobs import (
    PROJECT_IMAGE_MARKER_KEY,
    collect_project_image_garbage,
    externalize_project_images,
    hydrate_project_images,
    prune_project_images,
    stage_project_images,
    tracked_project_image_digests,
)
import ea_node_editor.persistence.artifact_store as artifact_store_module
import ea_node_editor.persistence.serializer as serializer_module
from ea_node_editor.persistence.artifact_store import ProjectArtifactLayout
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.runtime_contracts import (
    DataTree,
    ImageValue,
    deserialize_runtime_value,
    serialize_runtime_value,
)
from ea_node_editor.ui.plot_preview_cache_provider import ViewerPreviewCacheImageProvider


def _image() -> ImageValue:
    image, _warnings = render_signal_plot(
        {"values": DataTree((((0,), (1.0, 2.0, 1.5)),)), "marker_shapes": [0]}
    )
    return image


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _structural_png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(b""))
        + _png_chunk(b"IEND", b"")
    )


def _raster_png(
    raster: bytes,
    *,
    bit_depth: int = 8,
    color_type: int = 6,
    interlace: int = 0,
    compressed: bytes | None = None,
) -> bytes:
    ihdr = struct.pack(">IIBBBBB", 1, 1, bit_depth, color_type, 0, 0, interlace)
    plte = _png_chunk(b"PLTE", b"\x00\x00\x00") if color_type == 3 else b""
    idat = zlib.compress(raster) if compressed is None else compressed
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + plte
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )


def test_image_value_is_immutable_validated_and_runtime_round_trips() -> None:
    registry = build_default_registry()
    image = _image()
    with pytest.raises(dataclasses.FrozenInstanceError):
        image.width = 5  # type: ignore[misc]
    with pytest.raises(ValueError, match="PNG header"):
        ImageValue.from_png(b"not a png")
    with pytest.raises(ValueError, match="sha256"):
        ImageValue(image.encoded_bytes, "png", image.width, image.height, "0" * 64)
    wire = serialize_runtime_value(image, catalog=registry.data_types)
    assert deserialize_runtime_value(json.loads(json.dumps(wire)), catalog=registry.data_types) == image


def test_image_value_rejects_exact_type_png_structure_crc_and_pixel_limit() -> None:
    image = _image()
    for changes in (
        {"width": True},
        {"height": 1.0},
        {"schema_version": True},
        {"format": b"png"},
        {"sha256": b"0" * 64},
    ):
        with pytest.raises(TypeError):
            dataclasses.replace(image, **changes)
    with pytest.raises(TypeError):
        ImageValue.from_png(bytearray(image.encoded_bytes))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="truncated|length"):
        ImageValue.from_png(image.encoded_bytes[:-2])
    corrupted = bytearray(image.encoded_bytes)
    corrupted[-1] ^= 1
    with pytest.raises(ValueError, match="CRC"):
        ImageValue.from_png(bytes(corrupted))
    with pytest.raises(ValueError, match="IEND"):
        ImageValue.from_png(_structural_png(1, 1)[:-12])
    with pytest.raises(ValueError, match="64 megapixels"):
        ImageValue.from_png(_structural_png(8001, 8000))


def test_image_value_validates_decoded_idat_raster_structure() -> None:
    valid_rgba = b"\x00\x01\x02\x03\x04"
    invalid_payloads = (
        (_raster_png(valid_rgba, compressed=b""), "zlib|EOF"),
        (_raster_png(valid_rgba, compressed=zlib.compress(valid_rgba)[:-2]), "zlib|EOF"),
        (_raster_png(valid_rgba + b"\x00"), "exceeds|byte count"),
        (_raster_png(b"\x05\x01\x02\x03\x04"), "filter"),
        (_raster_png(valid_rgba, compressed=b"not-zlib"), "zlib"),
        (_raster_png(valid_rgba, interlace=1), "interlaced"),
    )
    for payload, message in invalid_payloads:
        with pytest.raises(ValueError, match=message):
            ImageValue.from_png(payload)

    valid_by_color_type = (
        _raster_png(b"\x00\x7f", color_type=0),
        _raster_png(b"\x00\x01\x02\x03", color_type=2),
        _raster_png(b"\x00\x00", color_type=3),
        _raster_png(b"\x00\x01\x02", color_type=4),
        _raster_png(valid_rgba, color_type=6),
    )
    for payload in valid_by_color_type:
        assert ImageValue.from_png(payload).encoded_bytes == payload


@pytest.fixture
def image_preview_provider() -> Iterator[ViewerPreviewCacheImageProvider]:
    provider = ViewerPreviewCacheImageProvider()
    image_preview_module.set_active_image_value_preview_provider(provider)
    image_preview_module.clear_image_value_previews()
    try:
        yield provider
    finally:
        image_preview_module.clear_image_value_previews()
        image_preview_module.set_active_image_value_preview_provider(None)


def test_image_preview_reuses_same_and_equivalent_values_without_decode_or_publication(
    image_preview_provider: ViewerPreviewCacheImageProvider,
) -> None:
    value = ImageValue.from_png(_raster_png(b"\x00\x01\x02\x03\xff"))
    equivalent = ImageValue.from_png(value.encoded_bytes)
    assert equivalent is not value
    with (
        patch.object(image_preview_module, "QImage", wraps=QImage) as decoder,
        patch.object(
            image_preview_provider, "set_preview", wraps=image_preview_provider.set_preview
        ) as publish,
    ):
        source = image_preview_module.image_value_preview_source(value)
        assert source.startswith("image://viewer-preview-cache/")
        assert image_preview_module.image_value_preview_source(value) == source
        assert image_preview_module.image_value_preview_source(equivalent) == source
        lookalike = SimpleNamespace(**dataclasses.asdict(value))
        assert image_preview_module.image_value_preview_source(lookalike) == ""
        decoder.fromData.assert_called_once_with(value.encoded_bytes, "PNG")
        publish.assert_called_once()


def test_image_preview_changed_content_has_its_own_pixels_and_url(
    image_preview_provider: ViewerPreviewCacheImageProvider,
) -> None:
    blue = ImageValue.from_png(_raster_png(b"\x00\x00\x00\xff\xff"))
    red = ImageValue.from_png(_raster_png(b"\x00\xff\x00\x00\xff"))
    blue_source = image_preview_module.image_value_preview_source(blue)
    red_source = image_preview_module.image_value_preview_source(red)
    assert red_source != blue_source
    for source, rgba in ((blue_source, (0, 0, 255, 255)), (red_source, (255, 0, 0, 255))):
        pixels, size = image_preview_provider.requestImage(
            source.split("image://viewer-preview-cache/", 1)[1], QSize()
        )
        assert size == QSize(1, 1)
        assert pixels.pixelColor(0, 0).getRgb() == rgba
    assert image_preview_module.image_value_preview_source(blue) == blue_source


@pytest.mark.parametrize("cache_loss", ["entry", "all", "adapter", "signature"])
def test_image_preview_registers_again_after_cache_loss_or_signature_mismatch(
    image_preview_provider: ViewerPreviewCacheImageProvider,
    cache_loss: str,
) -> None:
    value = ImageValue.from_png(_raster_png(b"\x00\x01\x02\x03\xff"))
    namespace = image_preview_module.IMAGE_VALUE_PREVIEW_WORKSPACE_ID
    source = image_preview_module.image_value_preview_source(value)
    if cache_loss == "entry":
        assert image_preview_provider.clear_preview(namespace, value.sha256)
    elif cache_loss == "all":
        assert image_preview_provider.clear_all()
    elif cache_loss == "adapter":
        image_preview_module.clear_image_value_previews()
        assert not image_preview_provider.has_preview(namespace, value.sha256)
    else:
        assert image_preview_provider.set_preview(
            namespace, value.sha256, QImage.fromData(value.encoded_bytes, "PNG"),
            signature="different-content",
        )
    with (
        patch.object(image_preview_module, "QImage", wraps=QImage) as decoder,
        patch.object(
            image_preview_provider, "set_preview", wraps=image_preview_provider.set_preview
        ) as publish,
    ):
        refreshed_source = image_preview_module.image_value_preview_source(value)
        assert refreshed_source and refreshed_source != source
        assert image_preview_provider.preview_signature(namespace, value.sha256) == value.sha256
        assert image_preview_module.image_value_preview_source(value) == refreshed_source
        decoder.fromData.assert_called_once_with(value.encoded_bytes, "PNG")
        publish.assert_called_once()


def test_image_preview_provider_replacement_registers_in_active_provider(
    image_preview_provider: ViewerPreviewCacheImageProvider,
) -> None:
    value = ImageValue.from_png(_raster_png(b"\x00\x01\x02\x03\xff"))
    namespace = image_preview_module.IMAGE_VALUE_PREVIEW_WORKSPACE_ID
    image_preview_module.image_value_preview_source(value)
    replacement = ViewerPreviewCacheImageProvider()
    image_preview_module.set_active_image_value_preview_provider(None)
    assert image_preview_module.image_value_preview_source(value) == ""
    image_preview_module.set_active_image_value_preview_provider(replacement)
    with patch.object(replacement, "set_preview", wraps=replacement.set_preview) as publish:
        source = image_preview_module.image_value_preview_source(value)
        assert source == replacement.preview_source(namespace, value.sha256)
        assert replacement.has_preview(namespace, value.sha256)
        assert image_preview_module.image_value_preview_source(value) == source
        publish.assert_called_once()
    image_preview_module.clear_image_value_previews()
    assert not replacement.has_preview(namespace, value.sha256)
    assert image_preview_provider.has_preview(namespace, value.sha256)


def test_image_preview_existing_active_entry_is_reused_and_tracked_for_cleanup(
    image_preview_provider: ViewerPreviewCacheImageProvider,
) -> None:
    value = ImageValue.from_png(_raster_png(b"\x00\x01\x02\x03\xff"))
    namespace = image_preview_module.IMAGE_VALUE_PREVIEW_WORKSPACE_ID
    assert image_preview_provider.set_preview(
        namespace, value.sha256, QImage.fromData(value.encoded_bytes, "PNG"),
        signature=value.sha256,
    )
    source = image_preview_provider.preview_source(namespace, value.sha256)
    with patch.object(image_preview_module, "QImage") as decoder:
        assert image_preview_module.image_value_preview_source(value) == source
        decoder.fromData.assert_not_called()
    image_preview_module.clear_image_value_previews()
    assert not image_preview_provider.has_preview(namespace, value.sha256)


@pytest.mark.parametrize("decoded_size", [(0, 0), (2, 1)])
def test_image_preview_rejects_null_or_dimension_mismatched_decode(
    image_preview_provider: ViewerPreviewCacheImageProvider,
    decoded_size: tuple[int, int],
) -> None:
    value = ImageValue.from_png(_raster_png(b"\x00\x01\x02\x03\xff"))
    decoded = QImage(*decoded_size, QImage.Format.Format_ARGB32)
    with patch.object(image_preview_module, "QImage") as decoder:
        decoder.fromData.return_value = decoded
        assert image_preview_module.image_value_preview_source(value) == ""
    assert not image_preview_provider.has_preview(
        image_preview_module.IMAGE_VALUE_PREVIEW_WORKSPACE_ID, value.sha256
    )


def test_project_image_blobs_deduplicate_hydrate_and_prune(tmp_path: Path) -> None:
    registry = build_default_registry()
    image = _image()
    project_path = tmp_path / "images.cxproj"
    wire = serialize_runtime_value(image, catalog=registry.data_types)
    document = {"schema_version": 5, "workspaces": [], "metadata": {}, "values": [wire, wire]}
    externalized = externalize_project_images(document, project_path=project_path, catalog=registry.data_types)
    assert all(PROJECT_IMAGE_MARKER_KEY in value for value in externalized["values"])
    image_root = ProjectArtifactLayout.from_project_path(project_path).sidecar_root / "images"
    blob = image_root / f"{image.sha256}.png"
    assert [path.name for path in image_root.glob("*.png")] == [f"{image.sha256}.png"]
    hydrated = hydrate_project_images(externalized, project_path=project_path, catalog=registry.data_types)
    restored = [deserialize_runtime_value(value, catalog=registry.data_types) for value in hydrated["values"]]
    assert restored == [image, image]

    untracked = image_root / f"{'f' * 64}.png"
    untracked.write_bytes(image.encoded_bytes)
    prune_project_images(
        project_path=project_path,
        tracked_digests=tracked_project_image_digests(externalized),
        retained_digests=frozenset(),
    )
    assert not blob.exists()
    assert untracked.exists()


def test_project_image_blob_rejects_missing_or_tampered_payload(tmp_path: Path) -> None:
    registry = build_default_registry()
    image = _image()
    project_path = tmp_path / "images.cxproj"
    document = {
        "metadata": {},
        "value": serialize_runtime_value(image, catalog=registry.data_types),
    }
    externalized = externalize_project_images(document, project_path=project_path, catalog=registry.data_types)
    blob = ProjectArtifactLayout.from_project_path(project_path).sidecar_root / "images" / f"{image.sha256}.png"
    blob.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="metadata does not match|PNG header"):
        hydrate_project_images(externalized, project_path=project_path, catalog=registry.data_types)


def test_project_image_blob_rejects_reparse_ancestor_for_read_and_prune(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = build_default_registry()
    image = _image()
    project_path = tmp_path / "images.cxproj"
    externalized = externalize_project_images(
        {"metadata": {}, "value": serialize_runtime_value(image, catalog=registry.data_types)},
        project_path=project_path,
        catalog=registry.data_types,
    )
    image_root = ProjectArtifactLayout.from_project_path(project_path).sidecar_root / "images"
    blob = image_root / f"{image.sha256}.png"
    unsafe_key = os.path.normcase(os.path.abspath(image_root.parent))
    real_lstat = artifact_store_module.os.lstat

    def reparse_lstat(path: str | os.PathLike[str]) -> object:
        result = real_lstat(path)
        if os.path.normcase(os.path.abspath(path)) == unsafe_key:
            return SimpleNamespace(
                st_mode=result.st_mode,
                st_file_attributes=getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400),
            )
        return result

    monkeypatch.setattr(artifact_store_module.os, "lstat", reparse_lstat)
    with pytest.raises(ValueError, match="unsafe"):
        hydrate_project_images(externalized, project_path=project_path, catalog=registry.data_types)
    prune_project_images(
        project_path=project_path,
        tracked_digests=frozenset({image.sha256}),
        retained_digests=frozenset(),
    )
    assert blob.exists()


def test_project_save_failure_preserves_previous_document_and_tracked_blobs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = build_default_registry()
    old_image = _image()
    new_image, _warnings = render_signal_plot(
        {"values": DataTree((((0,), (3.0, 2.0, 1.0)),)), "marker_shapes": [0]}
    )
    project_path = tmp_path / "transaction.cxproj"
    old_document = externalize_project_images(
        {"metadata": {}, "value": serialize_runtime_value(old_image, catalog=registry.data_types)},
        project_path=project_path,
        catalog=registry.data_types,
    )
    project_path.write_text(json.dumps(old_document), encoding="utf-8")
    old_blob = (
        ProjectArtifactLayout.from_project_path(project_path).sidecar_root
        / "images"
        / f"{old_image.sha256}.png"
    )
    serializer = JsonProjectSerializer(registry)
    monkeypatch.setattr(serializer._codec, "validate_persistent_document", lambda _document: None)
    real_replace = serializer_module.os.replace

    def fail_document_replace(
        source: str | os.PathLike[str],
        destination: str | os.PathLike[str],
    ) -> None:
        if Path(destination) == project_path:
            raise OSError("document replace failed")
        real_replace(source, destination)

    monkeypatch.setattr(serializer_module.os, "replace", fail_document_replace)
    with pytest.raises(OSError, match="project document was not published"):
        serializer.save_document(
            str(project_path),
            {"metadata": {}, "value": serialize_runtime_value(new_image, catalog=registry.data_types)},
        )
    assert json.loads(project_path.read_text(encoding="utf-8")) == old_document
    assert old_blob.read_bytes() == old_image.encoded_bytes
    hydrated = hydrate_project_images(old_document, project_path=project_path, catalog=registry.data_types)
    assert deserialize_runtime_value(hydrated["value"], catalog=registry.data_types) == old_image


def test_image_stage_never_replaces_a_conflicting_digest_blob(tmp_path: Path) -> None:
    registry = build_default_registry()
    image = _image()
    project_path = tmp_path / "image.cxproj"
    document = {
        "metadata": {},
        "value": serialize_runtime_value(image, catalog=registry.data_types),
    }
    first = stage_project_images(
        document,
        project_path=project_path,
        catalog=registry.data_types,
    )
    blob = (
        ProjectArtifactLayout.from_project_path(project_path).sidecar_root
        / "images"
        / f"{image.sha256}.png"
    )
    assert first.staged_new_bytes == len(image.encoded_bytes)
    blob.write_bytes(b"conflicting committed bytes")

    with pytest.raises(ValueError, match="image digest conflict"):
        stage_project_images(
            document,
            project_path=project_path,
            catalog=registry.data_types,
        )

    assert blob.read_bytes() == b"conflicting committed bytes"


def test_project_image_gc_partial_batch_returns_retryable_remaining_digests(
    tmp_path: Path,
) -> None:
    project = tmp_path / "images.cxproj"
    image_root = ProjectArtifactLayout.from_project_path(project).sidecar_root / "images"
    image_root.mkdir(parents=True)
    digests = ("a" * 64, "b" * 64)
    for digest in digests:
        (image_root / f"{digest}.png").write_bytes(digest.encode("ascii"))
    first = collect_project_image_garbage(
        project_path=project,
        candidate_digests=digests,
        limit=1,
    )
    assert first.has_more
    assert len(first.removed_digests) == 1
    assert len(first.remaining_digests) == 1
    second = collect_project_image_garbage(
        project_path=project,
        candidate_digests=first.remaining_digests,
    )
    assert not second.has_more
    assert second.remaining_digests == ()
