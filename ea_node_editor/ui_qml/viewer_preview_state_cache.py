# Purpose: Own the cached proxy frame and camera state a viewer node shows when it is not live.
# Map: subsystems/viewer_surfaces.md
# Tests: tests/test_viewer_preview_state_cache.py

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable, Mapping
from typing import Any
from urllib.parse import quote

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QWidget

from ea_node_editor.common.scene_protocol import ENGINEERING_VIEWER_BACKEND_ID
from ea_node_editor.ui.plot_preview_cache_provider import ViewerPreviewCacheImageProvider

OverlayKey = tuple[str, str]


def _string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple(sorted((_string(key), _freeze_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def cache_relevant_options(options: Mapping[str, Any]) -> dict[str, Any]:
    ignored_keys = {
        "export_formats",
        # The probe changes no committed pixels, so it must not invalidate
        # cached previews or camera state.
        "hover_probe",
        "live_mode",
        "output_profile",
        "playback",
        "playback_state",
        "step_index",
    }
    return {
        str(key): copy.deepcopy(value)
        for key, value in options.items()
        if str(key) not in ignored_keys
    }


class ViewerPreviewStateCache:
    """Single owner of what a viewer node shows once it leaves live mode.

    Two things outlive a live session per node: the raster frame served to
    QML through ``image://viewer-preview-cache``, and the VTK camera used to
    restore the view on the next bind. Both are keyed by ``(workspace, node)``
    and invalidated by signatures over the session projection, and both are
    taken from the same widget at the same moment, so the question "may we
    reuse what we already have?" is answered here instead of separately at
    every inline, detached and fullscreen presentation call site.

    Everything the cache needs from the host is injected, so it never reaches
    back into binding, overlay or session-bridge state.
    """

    def __init__(
        self,
        *,
        provider: ViewerPreviewCacheImageProvider | None,
        snapshot_for_key: Callable[[OverlayKey], Any],
        bound_for_key: Callable[[OverlayKey], Any],
        widget_for_bound: Callable[[OverlayKey, Any], QWidget | None],
        capture_image: Callable[[str, str], QImage],
        binding_signature: Callable[[Any], tuple[Any, ...]],
        report_error: Callable[[str], None],
        revision_changed: Callable[[], None],
    ) -> None:
        self._provider = provider
        self._snapshot_for_key = snapshot_for_key
        self._bound_for_key = bound_for_key
        self._widget_for_bound = widget_for_bound
        self._capture_image = capture_image
        self._binding_signature = binding_signature
        self._report_error = report_error
        self._revision_changed = revision_changed
        self._view_states: dict[OverlayKey, tuple[tuple[Any, ...], object]] = {}
        self._render_signatures: dict[OverlayKey, tuple[Any, ...]] = {}
        self._live_frame_dirty: set[OverlayKey] = set()
        self._stale_previews: set[OverlayKey] = set()
        self._preview_sizes: dict[OverlayKey, QSize] = {}
        self._revision = 0

    # ----------------------------------------------------------------- reads

    @property
    def revision(self) -> int:
        return self._revision

    def preview_source(self, key: OverlayKey) -> str:
        provider = self._provider
        return provider.preview_source(key[0], key[1]) if provider is not None else ""

    def has_preview(self, key: OverlayKey) -> bool:
        provider = self._provider
        return bool(provider is not None and provider.has_preview(key[0], key[1]))

    def preview_size(self, key: OverlayKey) -> QSize | None:
        """Size of the stored frame, for callers that must match its aspect."""
        return self._preview_sizes.get(key) if self.has_preview(key) else None

    def preview_stale(self, key: OverlayKey) -> bool:
        """The cached frame predates the node's current visual settings.

        A visual-option change keeps the frame rather than dropping the node
        back to an empty placeholder; the surface dims it and shows a status
        badge until the next live exit captures the settings in use.
        """
        return key in self._stale_previews and self.has_preview(key)

    def preview_image(self, key: OverlayKey) -> QImage:
        """The cached frame itself, for clipboard and screenshot export."""
        request_image = getattr(self._provider, "requestImage", None)
        if not callable(request_image):
            return QImage()
        workspace = quote(key[0], safe="")
        node = quote(key[1], safe="")
        try:
            image, _size = request_image(f"preview?workspace={workspace}&node={node}", QSize())
        except Exception as exc:  # noqa: BLE001
            self._report_error(str(exc))
            return QImage()
        return image if isinstance(image, QImage) else QImage()

    def cached_view_state(self, key: OverlayKey) -> object | None:
        cached = self._view_states.get(key)
        return None if cached is None else cached[1]

    # ------------------------------------------------------------- capturing

    def mark_live_frame_dirty(self, key: OverlayKey) -> None:
        """Record that the live widget may now differ from the cached frame.

        Every live presentation episode marks the key, and a successful
        capture clears it. Direct VTK mouse interaction never reaches this
        process boundary, so entering live mode alone has to count as a
        change; that keeps the proxy frame honest while still skipping the
        redundant second screenshot a single exit would otherwise take (once
        on demote, once when the binding is parked in the retained slot).
        """
        self._live_frame_dirty.add(key)

    def capture_live_state(self, key: OverlayKey) -> None:
        """Refresh the cached frame and camera from the live widget."""
        bound = self._bound_for_key(key)
        if bound is None:
            return
        current_snapshot = self._snapshot_for_key(key)
        if current_snapshot is None:
            self.clear_viewer_state(key)
            return
        camera_signature = self.camera_signature(current_snapshot)
        signature = self.preview_signature(current_snapshot)
        if self._binding_signature(current_snapshot) != bound.signature:
            # The camera is independent of visual options: keep it as long as
            # the session still shows the same transported geometry.
            if camera_signature == self.camera_signature(bound.snapshot):
                self._capture_view_state(key, bound, camera_signature)
            else:
                self._view_states.pop(key, None)
            if signature != self.preview_signature(bound.snapshot):
                self.clear_preview(key)
                return
        else:
            self._capture_view_state(key, bound, camera_signature)
        if self._provider is None:
            return
        cached_signature = self._provider.preview_signature(key[0], key[1])
        if cached_signature is not None and cached_signature != signature:
            self.clear_preview(key)
        if key not in self._live_frame_dirty and self.has_preview(key):
            return
        image = self._capture_image(bound.snapshot.node_id, bound.snapshot.workspace_id)
        if image.isNull():
            return
        self._set_preview(key, image, signature)
        self._live_frame_dirty.discard(key)
        self._stale_previews.discard(key)

    def restore_view_state(
        self,
        key: OverlayKey,
        binder: Any,
        widget: QWidget,
        signature: tuple[Any, ...],
    ) -> None:
        cached = self._view_states.get(key)
        if cached is None:
            return
        cached_signature, state = cached
        if cached_signature != signature:
            self.clear_viewer_state(key)
            return
        restore = getattr(binder, "restore_view_state", None)
        if not callable(restore):
            return
        try:
            restore(widget, self._copied(state))
        except Exception as exc:  # noqa: BLE001
            self._report_error(str(exc))

    def _capture_view_state(
        self,
        key: OverlayKey,
        bound: Any,
        signature: tuple[Any, ...],
    ) -> None:
        capture = getattr(bound.binder, "capture_view_state", None)
        if not callable(capture):
            return
        widget = self._widget_for_bound(key, bound)
        if widget is None:
            return
        try:
            state = capture(widget)
        except Exception as exc:  # noqa: BLE001
            self._report_error(str(exc))
            return
        if state is None:
            return
        self._view_states[key] = (signature, self._copied(state))

    # ---------------------------------------------------------- invalidation

    def clear_preview(self, key: OverlayKey) -> None:
        self._stale_previews.discard(key)
        self._preview_sizes.pop(key, None)
        provider = self._provider
        if provider is None:
            return
        if provider.clear_preview(key[0], key[1]):
            self._bump_revision()

    def _mark_preview_stale(self, key: OverlayKey) -> None:
        if key in self._stale_previews:
            return
        self._stale_previews.add(key)
        self._bump_revision()

    def clear_viewer_state(self, key: OverlayKey) -> None:
        self._view_states.pop(key, None)
        self.clear_preview(key)

    def migrate_viewer_state(self, key: OverlayKey, snapshot: Any) -> None:
        """Reconcile cached state with a changed session projection.

        A visual-option change leaves the transported geometry alone, so both
        the camera and the frame stay usable and the frame is only marked
        stale. New geometry invalidates both.
        """
        camera_signature = self.camera_signature(snapshot)
        cached = self._view_states.get(key)
        geometry_changed = cached is not None and cached[0] != camera_signature
        if geometry_changed:
            self._view_states.pop(key, None)
            self.clear_preview(key)
            return
        if self.has_preview(key):
            self._mark_preview_stale(key)
        else:
            self.clear_preview(key)

    def clear_all(self) -> None:
        provider = self._provider
        changed = provider.clear_all() if provider is not None else False
        self._render_signatures.clear()
        self._view_states.clear()
        self._live_frame_dirty.clear()
        self._stale_previews.clear()
        self._preview_sizes.clear()
        if changed:
            self._bump_revision()

    def sync_signatures(self, snapshots: Iterable[Any]) -> None:
        """Reconcile cached state against the current session projections."""
        provider = self._provider
        current: dict[OverlayKey, tuple[Any, ...]] = {}
        for snapshot in snapshots:
            key = snapshot.overlay_key
            signature = self.preview_signature(snapshot)
            current[key] = signature
            previous_signature = self._render_signatures.get(key)
            cached_signature = (
                provider.preview_signature(key[0], key[1]) if provider is not None else None
            )
            if (
                (previous_signature is not None and previous_signature != signature)
                or (cached_signature is not None and cached_signature != signature)
            ):
                self.migrate_viewer_state(key, snapshot)
        for key in set(self._render_signatures) - set(current):
            self.clear_viewer_state(key)
        self._render_signatures = current

    # -------------------------------------------------------------- internals

    def store_preview(self, key: OverlayKey, image: QImage, signature: tuple[Any, ...]) -> None:
        """Store a frame produced outside the live-capture path.

        Used by the warm-up render, which has no bound widget to capture
        from. It is current by definition, so it clears any stale mark.
        """
        if image.isNull():
            return
        self._set_preview(key, image, signature)
        self._stale_previews.discard(key)

    def _set_preview(self, key: OverlayKey, image: QImage, signature: tuple[Any, ...]) -> None:
        provider = self._provider
        if provider is None:
            return
        if provider.set_preview(key[0], key[1], image, signature=signature):
            self._preview_sizes[key] = image.size()
            self._bump_revision()

    def _bump_revision(self) -> None:
        self._revision += 1
        self._revision_changed()

    @staticmethod
    def _copied(state: Any) -> Any:
        try:
            return copy.deepcopy(state)
        except Exception:  # noqa: BLE001
            return state

    @staticmethod
    def preview_signature(snapshot: Any) -> tuple[Any, ...]:
        options = cache_relevant_options(snapshot.options)
        if snapshot.backend_id == ENGINEERING_VIEWER_BACKEND_ID:
            options.pop("scene_labels", None)
        return (
            *ViewerPreviewStateCache.camera_signature(snapshot),
            _freeze_value(snapshot.playback_state),
            _freeze_value(options),
        )

    @staticmethod
    def camera_signature(snapshot: Any) -> tuple[Any, ...]:
        # Camera state survives option and playback changes; it resets only
        # when the transported geometry itself changes.
        transport = snapshot.transport
        data_refs = snapshot.data_refs
        if snapshot.backend_id == ENGINEERING_VIEWER_BACKEND_ID:
            transport = {
                **transport,
                "layers": [
                    {key: value for key, value in layer.items() if key != "name"}
                    for layer in transport.get("layers", ())
                ],
            }
            data_refs = {key: value for key, value in data_refs.items() if key != "scene_labels"}
        return (
            snapshot.session_id,
            snapshot.backend_id,
            snapshot.transport_revision,
            _freeze_value(transport),
            _freeze_value(data_refs),
        )


__all__ = ["OverlayKey", "ViewerPreviewStateCache", "cache_relevant_options"]
