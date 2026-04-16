from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QWidget

from ea_node_editor.ui_qml.dpf_viewer_widget_binder import DpfViewerWidgetBinder
from ea_node_editor.ui_qml.viewer_widget_binder import (
    ViewerWidgetBindRequest,
    ViewerWidgetNoBind,
    ViewerWidgetReleaseRequest,
)


class _FakeCamera:
    def __init__(self) -> None:
        self.position = None
        self.focal_point = None
        self.up = None
        self.parallel_projection = None
        self.parallel_scale = None
        self.view_angle = None
        self.zoom_calls: list[float] = []

    def zoom(self, value: float) -> None:
        self.zoom_calls.append(float(value))


class _FakeInteractor(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.clear_calls = 0
        self.add_mesh_calls: list[dict[str, object]] = []
        self.add_text_calls: list[dict[str, object]] = []
        self.reset_camera_calls = 0
        self.render_calls = 0
        self.screenshot_calls = 0
        self.screenshot_kwargs: list[dict[str, object]] = []
        self.screenshot_image = QImage(16, 10, QImage.Format.Format_ARGB32)
        self.screenshot_image.fill(0xFF2F89FF)
        self.camera_position = None
        self.camera = _FakeCamera()
        self.resize(320, 240)

    def clear(self) -> None:
        self.clear_calls += 1

    def add_mesh(self, mesh, **kwargs):  # noqa: ANN001
        self.add_mesh_calls.append({"mesh": mesh, **kwargs})
        return object()

    def add_text(self, text, **kwargs):  # noqa: ANN001
        self.add_text_calls.append({"text": text, **kwargs})
        return object()

    def reset_camera(self) -> None:
        self.reset_camera_calls += 1

    def render(self) -> None:
        self.render_calls += 1

    def screenshot(self, **kwargs):  # noqa: ANN001
        self.screenshot_calls += 1
        self.screenshot_kwargs.append(dict(kwargs))
        return self.screenshot_image.copy()


class _FakeMesh:
    def __init__(self, *array_names: str) -> None:
        self.array_names = list(array_names)


class _FakeMultiBlock:
    def __init__(self, blocks: list[_FakeMesh | None]) -> None:
        self._blocks = list(blocks)
        self.n_blocks = len(self._blocks)

    def __getitem__(self, index: int):
        return self._blocks[index]


def _write_transport_bundle(root: Path, *, result_name: str = "stress") -> tuple[Path, Path]:
    dataset_dir = root / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    entry_path = dataset_dir / "dataset.vtm"
    entry_path.write_text("fake transport entry", encoding="utf-8")
    manifest_path = root / "transport_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "ea.dpf.viewer_transport_bundle.v1",
                "workspace_id": "ws-tests",
                "session_id": "session-tests",
                "transport_revision": 3,
                "entry_file": "dataset/dataset.vtm",
                "files": ["dataset/dataset.vtm"],
                "metadata": {
                    "result_name": result_name,
                    "set_ids": [1, 2, 3],
                },
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return manifest_path, entry_path


def _bind_request(
    *,
    manifest_path: Path,
    entry_path: Path,
    current_widget: QWidget | None = None,
    playback_step_index: int = 0,
    camera_state: dict[str, object] | None = None,
    summary: dict[str, object] | None = None,
) -> ViewerWidgetBindRequest:
    return ViewerWidgetBindRequest(
        workspace_id="ws-tests",
        node_id="node-tests",
        session_id="session-tests",
        backend_id=DpfViewerWidgetBinder.backend_id,
        transport_revision=3,
        live_mode="full",
        cache_state="live_ready",
        live_open_status="ready",
        transport={
            "kind": "dpf_transport_bundle",
            "manifest_path": str(manifest_path),
            "entry_path": str(entry_path),
            "metadata": {"result_name": "stress"},
        },
        camera_state=dict(camera_state or {}),
        playback_state={"state": "paused", "step_index": playback_step_index},
        summary={
            "result_name": "Displacement",
            "set_label": "Set 4",
            **dict(summary or {}),
        },
        container=QWidget(),
        current_widget=current_widget,
    )


class DpfViewerWidgetBinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_bind_widget_loads_transport_bundle_and_applies_camera_and_playback_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            blocks = [
                _FakeMesh("node_id", "stress"),
                _FakeMesh("node_id", "stress"),
                _FakeMesh("node_id", "stress"),
            ]
            binder = DpfViewerWidgetBinder(
                interactor_factory=lambda parent: _FakeInteractor(parent),
                dataset_loader=lambda _path: _FakeMultiBlock(blocks),
            )

            request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                playback_step_index=1,
                camera_state={
                    "position": [1.0, 2.0, 3.0],
                    "focal_point": [0.0, 0.0, 0.0],
                    "viewup": [0.0, 1.0, 0.0],
                    "view_angle": 22.5,
                    "parallel_projection": True,
                    "parallel_scale": 3.25,
                },
            )
            widget = binder.bind_widget(request)

        self.assertIsInstance(widget, _FakeInteractor)
        self.assertEqual(widget.clear_calls, 1)
        self.assertEqual(len(widget.add_mesh_calls), 1)
        self.assertIs(widget.add_mesh_calls[0]["mesh"], blocks[1])
        self.assertEqual(widget.add_mesh_calls[0]["scalars"], "stress")
        self.assertEqual(
            widget.add_mesh_calls[0]["scalar_bar_args"],
            {
                "vertical": True,
                "title_font_size": 10,
                "label_font_size": 8,
                "height": 0.46,
                "width": 0.09,
                "position_x": 0.87,
                "position_y": 0.10,
            },
        )
        self.assertEqual(
            widget.add_text_calls,
            [
                {
                    "text": "Result: Displacement\nSet: Set 4\nStep: 1",
                    "position": "upper_left",
                    "font_size": 9,
                    "color": "#F4F6F8",
                    "shadow": True,
                    "name": "ea.dpf.viewer.metadata",
                    "render": False,
                },
            ],
        )
        self.assertEqual(
            widget.camera_position,
            [
                (1.0, 2.0, 3.0),
                (0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
            ],
        )
        self.assertEqual(widget.camera.view_angle, 22.5)
        self.assertTrue(widget.camera.parallel_projection)
        self.assertEqual(widget.camera.parallel_scale, 3.25)
        self.assertEqual(widget.camera.zoom_calls, [])
        self.assertEqual(widget.reset_camera_calls, 0)
        self.assertEqual(widget.render_calls, 1)
        self.assertEqual(widget.property("ea.viewer.backend_id"), DpfViewerWidgetBinder.backend_id)
        self.assertEqual(widget.property("ea.viewer.session_id"), "session-tests")
        self.assertEqual(widget.property("ea.viewer.transport_revision"), 3)
        self.assertEqual(widget.property("ea.viewer.step_index"), 1)

    def test_bind_widget_reuses_current_interactor_for_rebinds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            blocks = [
                _FakeMesh("stress"),
                _FakeMesh("stress"),
                _FakeMesh("stress"),
            ]
            created_widgets: list[_FakeInteractor] = []
            binder = DpfViewerWidgetBinder(
                interactor_factory=lambda parent: created_widgets.append(_FakeInteractor(parent)) or created_widgets[-1],
                dataset_loader=lambda _path: _FakeMultiBlock(blocks),
            )

            first_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                playback_step_index=0,
            )
            first_widget = binder.bind_widget(first_request)
            rebind_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                playback_step_index=2,
                current_widget=first_widget,
            )
            rebound_widget = binder.bind_widget(rebind_request)

        self.assertIs(first_widget, rebound_widget)
        self.assertEqual(len(created_widgets), 1)
        self.assertEqual(first_widget.clear_calls, 2)
        self.assertEqual(len(first_widget.add_mesh_calls), 2)
        self.assertIs(first_widget.add_mesh_calls[-1]["mesh"], blocks[2])
        self.assertEqual(first_widget.property("ea.viewer.step_index"), 2)

    def test_bind_widget_raises_no_bind_when_transport_is_unavailable(self) -> None:
        created_widgets: list[_FakeInteractor] = []
        binder = DpfViewerWidgetBinder(
            interactor_factory=lambda parent: created_widgets.append(_FakeInteractor(parent)) or created_widgets[-1],
            dataset_loader=lambda _path: _FakeMesh("stress"),
        )
        request = ViewerWidgetBindRequest(
            workspace_id="ws-tests",
            node_id="node-tests",
            session_id="session-tests",
            backend_id=DpfViewerWidgetBinder.backend_id,
            transport_revision=1,
            live_mode="full",
            cache_state="live_ready",
            live_open_status="ready",
            transport={
                "kind": "dpf_transport_bundle",
                "manifest_path": "",
                "entry_path": "",
            },
            container=QWidget(),
        )

        with self.assertRaises(ViewerWidgetNoBind):
            binder.bind_widget(request)

        self.assertEqual(created_widgets, [])

    def test_release_widget_clears_interactor_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            binder = DpfViewerWidgetBinder(
                interactor_factory=lambda parent: _FakeInteractor(parent),
                dataset_loader=lambda _path: _FakeMesh("stress"),
            )
            request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                playback_step_index=0,
            )
            widget = binder.bind_widget(request)

        binder.release_widget(
            ViewerWidgetReleaseRequest(
                workspace_id="ws-tests",
                node_id="node-tests",
                session_id="session-tests",
                backend_id=DpfViewerWidgetBinder.backend_id,
                transport_revision=3,
                widget=widget,
                reason="test_release",
            )
        )

        self.assertEqual(widget.clear_calls, 2)
        self.assertEqual(widget.render_calls, 2)
        self.assertEqual(widget.property("ea.viewer.session_id"), "")
        self.assertEqual(widget.property("ea.viewer.transport_revision"), 0)
        self.assertEqual(widget.property("ea.viewer.manifest_path"), "")
        self.assertEqual(widget.property("ea.viewer.entry_path"), "")

    def test_capture_camera_state_reads_live_interactor_camera(self) -> None:
        binder = DpfViewerWidgetBinder(
            interactor_factory=lambda parent: _FakeInteractor(parent),
            dataset_loader=lambda _path: _FakeMesh("stress"),
        )
        widget = _FakeInteractor()
        widget.camera_position = [
            (4.0, 5.0, 6.0),
            (1.0, 1.5, 2.0),
            (0.0, 0.0, 1.0),
        ]
        widget.setProperty("ea.viewer.backend_id", DpfViewerWidgetBinder.backend_id)
        widget.camera.parallel_projection = True
        widget.camera.parallel_scale = 2.5
        widget.camera.view_angle = 18.0

        captured = binder.capture_camera_state(widget)

        self.assertEqual(
            captured,
            {
                "position": [4.0, 5.0, 6.0],
                "focal_point": [1.0, 1.5, 2.0],
                "viewup": [0.0, 0.0, 1.0],
                "camera_position": [
                    [4.0, 5.0, 6.0],
                    [1.0, 1.5, 2.0],
                    [0.0, 0.0, 1.0],
                ],
                "parallel_projection": True,
                "parallel_scale": 2.5,
                "view_angle": 18.0,
            },
        )

    def test_capture_preview_image_uses_live_interactor_screenshot(self) -> None:
        binder = DpfViewerWidgetBinder(
            interactor_factory=lambda parent: _FakeInteractor(parent),
            dataset_loader=lambda _path: _FakeMesh("stress"),
        )
        widget = _FakeInteractor()
        widget.setProperty("ea.viewer.backend_id", DpfViewerWidgetBinder.backend_id)

        captured = binder.capture_preview_image(widget)

        self.assertIsInstance(captured, QImage)
        self.assertFalse(captured.isNull())
        self.assertEqual(captured.size(), widget.screenshot_image.size())
        self.assertEqual(widget.screenshot_calls, 1)
        self.assertEqual(widget.screenshot_kwargs, [{"return_img": True}])


if __name__ == "__main__":
    unittest.main()
