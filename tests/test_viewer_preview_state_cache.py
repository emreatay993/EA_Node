from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import pytest
from PyQt6.QtGui import QColor, QImage

from ea_node_editor.common.scene_protocol import ENGINEERING_VIEWER_BACKEND_ID
from ea_node_editor.ui.plot_preview_cache_provider import ViewerPreviewCacheImageProvider
from ea_node_editor.ui_qml.viewer_preview_state_cache import (
    ViewerPreviewStateCache,
    cache_relevant_options,
)

WORKSPACE = "ws_main"
NODE = "node_viewer"
KEY = (WORKSPACE, NODE)


@dataclass
class _Snapshot:
    workspace_id: str = WORKSPACE
    node_id: str = NODE
    session_id: str = "session::node_viewer"
    backend_id: str = "tests.backend"
    transport_revision: int = 1
    transport: dict[str, Any] = field(default_factory=lambda: {"kind": "tests"})
    data_refs: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def overlay_key(self) -> tuple[str, str]:
        return self.workspace_id, self.node_id


class _Binder:
    def __init__(self, camera: dict[str, Any] | None = None) -> None:
        self.camera = dict(camera or {"position": [1.0, 2.0, 3.0]})
        self.restore_calls: list[dict[str, Any]] = []

    def capture_view_state(self, _widget: Any) -> dict[str, Any]:
        return dict(self.camera)

    def restore_view_state(self, _widget: Any, state: dict[str, Any]) -> bool:
        self.restore_calls.append(dict(state))
        return True


@dataclass
class _Bound:
    binder: _Binder
    snapshot: _Snapshot
    signature: tuple[Any, ...]


class _Host:
    """The slice of ViewerHostService the cache is allowed to reach."""

    def __init__(self, snapshot: _Snapshot, bound: _Bound | None) -> None:
        self.snapshot: _Snapshot | None = snapshot
        self.bound = bound
        self.widget = object()
        self.captures = 0
        self.errors: list[str] = []
        self.revisions = 0
        self.captured_image = QImage(8, 4, QImage.Format.Format_ARGB32)
        self.captured_image.fill(QColor("#67D487"))

    def capture_image(self, _node_id: str, _workspace_id: str) -> QImage:
        self.captures += 1
        return self.captured_image.copy()

    def build(self, provider: ViewerPreviewCacheImageProvider | None) -> ViewerPreviewStateCache:
        return ViewerPreviewStateCache(
            provider=provider,
            snapshot_for_key=lambda _key: self.snapshot,
            bound_for_key=lambda _key: self.bound,
            widget_for_bound=lambda _key, _bound: self.widget,
            capture_image=self.capture_image,
            binding_signature=lambda snapshot: (snapshot.session_id, snapshot.transport_revision),
            report_error=self.errors.append,
            revision_changed=lambda: setattr(self, "revisions", self.revisions + 1),
        )


def _cache(snapshot: _Snapshot | None = None, binder: _Binder | None = None):
    resolved_snapshot = snapshot or _Snapshot()
    resolved_binder = binder or _Binder()
    bound = _Bound(
        binder=resolved_binder,
        snapshot=resolved_snapshot,
        signature=(resolved_snapshot.session_id, resolved_snapshot.transport_revision),
    )
    host = _Host(resolved_snapshot, bound)
    provider = ViewerPreviewCacheImageProvider()
    return host.build(provider), host, provider


def test_first_capture_stores_the_frame_and_the_camera(qapp) -> None:  # noqa: ANN001
    del qapp
    cache, host, provider = _cache()

    cache.capture_live_state(KEY)

    assert host.captures == 1
    assert provider.has_preview(WORKSPACE, NODE)
    assert cache.preview_source(KEY).startswith("image://viewer-preview-cache/")
    assert cache.cached_view_state(KEY) == {"position": [1.0, 2.0, 3.0]}
    assert host.revisions == 1


def test_capture_is_skipped_until_a_live_episode_marks_the_frame_dirty(qapp) -> None:  # noqa: ANN001
    del qapp
    cache, host, _provider = _cache()
    cache.capture_live_state(KEY)
    first_source = cache.preview_source(KEY)

    cache.capture_live_state(KEY)
    cache.capture_live_state(KEY)

    assert host.captures == 1
    assert cache.preview_source(KEY) == first_source


def test_a_live_episode_forces_the_next_capture(qapp) -> None:  # noqa: ANN001
    del qapp
    cache, host, _provider = _cache()
    cache.capture_live_state(KEY)
    first_source = cache.preview_source(KEY)

    cache.mark_live_frame_dirty(KEY)
    cache.capture_live_state(KEY)

    assert host.captures == 2
    assert cache.preview_source(KEY) != first_source


def test_a_missing_frame_is_captured_even_without_a_dirty_mark(qapp) -> None:  # noqa: ANN001
    del qapp
    cache, host, _provider = _cache()
    cache.capture_live_state(KEY)
    cache.clear_preview(KEY)

    cache.capture_live_state(KEY)

    assert host.captures == 2
    assert cache.preview_source(KEY)


def test_visual_option_change_keeps_the_frame_and_marks_it_stale(qapp) -> None:  # noqa: ANN001
    """The node keeps showing its last frame instead of emptying out."""
    del qapp
    cache, host, _provider = _cache()
    cache.capture_live_state(KEY)
    camera = cache.cached_view_state(KEY)
    source = cache.preview_source(KEY)
    revisions = host.revisions

    restyled = replace(_Snapshot(), options={"representation": "wireframe"})
    cache.migrate_viewer_state(KEY, restyled)

    assert cache.cached_view_state(KEY) == camera
    assert cache.has_preview(KEY)
    assert cache.preview_source(KEY) == source
    assert cache.preview_stale(KEY)
    assert host.revisions == revisions + 1

    # Marking again must not churn the revision QML binds to.
    cache.migrate_viewer_state(KEY, restyled)
    assert host.revisions == revisions + 1


def test_the_next_live_exit_clears_the_stale_mark(qapp) -> None:  # noqa: ANN001
    del qapp
    snapshot = _Snapshot()
    cache, _host, _provider = _cache(snapshot)
    cache.capture_live_state(KEY)
    cache.migrate_viewer_state(KEY, replace(snapshot, options={"representation": "wireframe"}))
    assert cache.preview_stale(KEY)

    cache.mark_live_frame_dirty(KEY)
    cache.capture_live_state(KEY)

    assert cache.has_preview(KEY)
    assert not cache.preview_stale(KEY)


def test_a_cleared_frame_is_never_reported_as_stale(qapp) -> None:  # noqa: ANN001
    del qapp
    snapshot = _Snapshot()
    cache, _host, _provider = _cache(snapshot)
    cache.capture_live_state(KEY)
    cache.migrate_viewer_state(KEY, replace(snapshot, options={"representation": "wireframe"}))

    cache.clear_preview(KEY)

    assert not cache.preview_stale(KEY)


def test_engineering_scene_label_changes_preserve_camera_and_fresh_preview(qapp) -> None:  # noqa: ANN001
    del qapp
    snapshot = _Snapshot(
        backend_id=ENGINEERING_VIEWER_BACKEND_ID,
        transport={"layers": [{"id": "scene_1", "name": "Scene 1", "display_asset": {"name": "memory_a"}}]},
        data_refs={"scene_order": ["scene_1"], "scene_labels": {"scene_1": "Scene 1"}, "scene:scene_1": "handle_a"},
        options={"scene_labels": {"scene_1": "Scene 1"}},
    )
    cache, host, _ = _cache(snapshot)
    cache.capture_live_state(KEY)
    cache.sync_signatures([snapshot])
    source, camera, revisions = cache.preview_source(KEY), cache.cached_view_state(KEY), host.revisions
    renamed = replace(
        snapshot,
        transport={"layers": [{**snapshot.transport["layers"][0], "name": "Renamed"}]},
        data_refs={**snapshot.data_refs, "scene_labels": {"scene_1": "Renamed"}},
        options={"scene_labels": {"scene_1": "Renamed"}},
    )
    cache.sync_signatures([renamed])
    assert cache.preview_source(KEY) == source
    assert cache.cached_view_state(KEY) == camera
    assert not cache.preview_stale(KEY)
    assert host.revisions == revisions
    assert host.captures == 1


@pytest.mark.parametrize("changed", ["handle", "scene_order", "asset_name", "layer_id"])
def test_engineering_scene_geometry_fields_still_invalidate(qapp, changed) -> None:  # noqa: ANN001
    del qapp
    snapshot = _Snapshot(
        backend_id=ENGINEERING_VIEWER_BACKEND_ID,
        transport={"layers": [{"id": "scene_1", "name": "Scene 1", "display_asset": {"name": "memory_a"}}]},
        data_refs={"scene_order": ["scene_1"], "scene:scene_1": "handle_a"},
    )
    cache, _, _ = _cache(snapshot)
    cache.capture_live_state(KEY)
    layer = dict(snapshot.transport["layers"][0])
    refs = dict(snapshot.data_refs)
    if changed == "handle":
        refs["scene:scene_1"] = "handle_b"
    elif changed == "scene_order":
        refs["scene_order"] = ["scene_1", "scene_2"]
    elif changed == "asset_name":
        layer["display_asset"] = {"name": "memory_b"}
    else:
        layer["id"] = "scene_2"
    cache.sync_signatures([replace(snapshot, transport={"layers": [layer]}, data_refs=refs)])
    assert cache.cached_view_state(KEY) is None
    assert not cache.has_preview(KEY)


def test_other_backends_keep_scene_label_options_in_preview_identity() -> None:
    before = _Snapshot(options={"scene_labels": {"scene_1": "First"}})
    after = replace(before, options={"scene_labels": {"scene_1": "Second"}})
    assert ViewerPreviewStateCache.preview_signature(before) != ViewerPreviewStateCache.preview_signature(after)


def test_new_geometry_drops_the_camera_as_well(qapp) -> None:  # noqa: ANN001
    del qapp
    cache, _host, _provider = _cache()
    cache.capture_live_state(KEY)

    regeometried = replace(_Snapshot(), transport_revision=2)
    cache.migrate_viewer_state(KEY, regeometried)

    assert cache.cached_view_state(KEY) is None
    assert not cache.has_preview(KEY)
    assert not cache.preview_stale(KEY)


def test_sync_signatures_drops_state_for_keys_that_are_gone(qapp) -> None:  # noqa: ANN001
    del qapp
    snapshot = _Snapshot()
    cache, _host, _provider = _cache(snapshot)
    cache.capture_live_state(KEY)
    cache.sync_signatures([snapshot])

    cache.sync_signatures([])

    assert cache.cached_view_state(KEY) is None
    assert not cache.has_preview(KEY)


def test_restore_view_state_rejects_a_stale_camera_signature(qapp) -> None:  # noqa: ANN001
    del qapp
    binder = _Binder()
    snapshot = _Snapshot()
    cache, _host, _provider = _cache(snapshot, binder)
    cache.capture_live_state(KEY)

    cache.restore_view_state(KEY, binder, object(), ViewerPreviewStateCache.camera_signature(snapshot))
    assert binder.restore_calls == [{"position": [1.0, 2.0, 3.0]}]

    stale = ViewerPreviewStateCache.camera_signature(replace(snapshot, transport_revision=9))
    cache.restore_view_state(KEY, binder, object(), stale)

    assert binder.restore_calls == [{"position": [1.0, 2.0, 3.0]}]
    assert cache.cached_view_state(KEY) is None


def test_camera_signature_ignores_options_that_preview_signature_tracks() -> None:
    base = _Snapshot()
    restyled = replace(base, options={"representation": "wireframe"})

    assert ViewerPreviewStateCache.camera_signature(base) == ViewerPreviewStateCache.camera_signature(
        restyled
    )
    assert ViewerPreviewStateCache.preview_signature(base) != ViewerPreviewStateCache.preview_signature(
        restyled
    )


def test_cache_relevant_options_ignores_non_visual_keys() -> None:
    filtered = cache_relevant_options(
        {
            "representation": "surface",
            "hover_probe": {"x": 1},
            "live_mode": "full",
            "step_index": 4,
        }
    )

    assert filtered == {"representation": "surface"}


@pytest.mark.parametrize("provider", [None])
def test_cache_without_a_provider_never_captures(qapp, provider) -> None:  # noqa: ANN001
    del qapp
    snapshot = _Snapshot()
    binder = _Binder()
    bound = _Bound(binder=binder, snapshot=snapshot, signature=(snapshot.session_id, 1))
    host = _Host(snapshot, bound)
    cache = host.build(provider)

    cache.capture_live_state(KEY)

    assert host.captures == 0
    assert cache.preview_source(KEY) == ""
    # The camera is still tracked; only the raster needs a provider.
    assert cache.cached_view_state(KEY) == {"position": [1.0, 2.0, 3.0]}
