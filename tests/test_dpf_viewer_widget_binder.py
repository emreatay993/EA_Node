from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QWidget

from ea_node_editor.execution.viewer_pyvista_style import (
    scalar_bar_args_for_viewport,
    set_viewer_canvas_dark,
    viewer_canvas_style,
)
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
        self.set_background_calls: list[dict[str, object]] = []
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

    def set_background(self, color, **kwargs):  # noqa: ANN001
        self.set_background_calls.append({"color": color, **kwargs})

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


class _FakeVectorMesh:
    def __init__(
        self,
        name: str = "displacement",
        vectors: object | None = None,
        bounds: tuple[float, ...] = (0.0, 1.0, 0.0, 1.0, 0.0, 1.0),
    ) -> None:
        import numpy as np

        resolved_vectors = np.asarray(
            vectors if vectors is not None else [[0.0, 0.0, 0.0], [0.03, 0.04, 0.0]],
            dtype=float,
        )
        self.array_names = ["node_id", name]
        self.point_data = {
            "node_id": np.arange(101, 101 + resolved_vectors.shape[0]),
            name: resolved_vectors,
        }
        self.points = np.asarray(
            [[float(index), 0.0, 0.0] for index in range(resolved_vectors.shape[0])],
            dtype=float,
        )
        self.bounds = bounds
        self.warp_calls: list[tuple[str, float]] = []
        self.warp_result: _FakeVectorMesh | None = None

    def warp_by_vector(self, name: str, factor: float):
        self.warp_calls.append((str(name), float(factor)))
        if self.warp_result is None:
            self.warp_result = _FakeVectorMesh(name)
        return self.warp_result


class _FakeScalarPointMesh:
    def __init__(self, name: str = "temperature") -> None:
        import numpy as np

        self.array_names = ["node_id", name]
        self.point_data = {name: np.asarray([1.0, 2.0, 3.0], dtype=float)}
        self.bounds = (0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
        self.warp_calls: list[tuple[str, float]] = []

    def warp_by_vector(self, name: str, factor: float):
        self.warp_calls.append((str(name), float(factor)))
        return self


class _CmapRejectingInteractor(_FakeInteractor):
    def add_mesh(self, mesh, **kwargs):  # noqa: ANN001
        if "cmap" in kwargs:
            self.add_mesh_calls.append({"mesh": mesh, **kwargs, "_rejected": True})
            raise ValueError("cmap requires matplotlib")
        return super().add_mesh(mesh, **kwargs)


class _FakeIren:
    def __init__(self) -> None:
        self.observers: dict[int, tuple[str, object]] = {}
        self._next_id = 1

    def add_observer(self, event, handler, **_kwargs):  # noqa: ANN001
        observer_id = self._next_id
        self._next_id += 1
        self.observers[observer_id] = (str(event), handler)
        return observer_id

    def remove_observer(self, observer_id) -> None:  # noqa: ANN001
        self.observers.pop(observer_id, None)

    def get_event_position(self) -> tuple[int, int]:
        return (0, 0)


class _ProbeInteractor(_FakeInteractor):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.iren = _FakeIren()
        self.renderer = object()
        self.add_point_labels_calls: list[dict[str, object]] = []

    def add_point_labels(self, points, labels, **kwargs):  # noqa: ANN001
        self.add_point_labels_calls.append({"points": points, "labels": labels, **kwargs})
        return object()


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
    options: dict[str, object] | None = None,
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
        options=dict(options or {}),
        container=QWidget(),
        current_widget=current_widget,
    )


class DpfViewerWidgetBinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_bind_widget_loads_transport_bundle_and_applies_camera_and_playback_snapshot(self) -> None:
        set_viewer_canvas_dark(True)
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
        self.assertTrue(widget.property("ea.nativeWindowOverlay"))
        self.assertEqual(widget.clear_calls, 1)
        self.assertEqual(len(widget.add_mesh_calls), 1)
        self.assertIs(widget.add_mesh_calls[0]["mesh"], blocks[1])
        self.assertEqual(widget.add_mesh_calls[0]["scalars"], "stress")
        self.assertFalse(widget.add_mesh_calls[0]["show_edges"])
        self.assertEqual(
            widget.add_mesh_calls[0]["scalar_bar_args"],
            {
                "vertical": True,
                "title_font_size": 10,
                "label_font_size": 8,
                "height": 0.46,
                "width": 0.04,
                "position_x": 0.90,
                "position_y": 0.10,
                "color": "#E8ECF1",
                "font_family": "arial",
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
                    "font": "arial",
                    "shadow": False,
                    "name": "ea.dpf.viewer.metadata",
                    "render": False,
                },
            ],
        )
        self.assertGreaterEqual(len(widget.set_background_calls), 1)
        self.assertEqual(
            widget.set_background_calls[-1],
            {"color": "#151A20", "top": "#232A33"},
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
        widget_state = binder._widget_state[widget]
        self.assertEqual(widget_state.backend_id, DpfViewerWidgetBinder.backend_id)
        self.assertEqual(widget_state.session_id, "session-tests")
        self.assertEqual(widget_state.transport_revision, 3)
        self.assertEqual(widget_state.step_index, 1)

    def test_bind_widget_passes_mesh_edge_option_to_pyvista(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            binder = DpfViewerWidgetBinder(
                interactor_factory=lambda parent: _FakeInteractor(parent),
                dataset_loader=lambda _path: _FakeMesh("stress"),
            )

            request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                options={"show_mesh_edges": True},
            )
            widget = binder.bind_widget(request)

        self.assertTrue(widget.add_mesh_calls[0]["show_edges"])

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
            first_widget.setProperty("ea.nativeWindowOverlay", False)
            rebind_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                playback_step_index=2,
                current_widget=first_widget,
            )
            rebound_widget = binder.bind_widget(rebind_request)

        self.assertIs(first_widget, rebound_widget)
        self.assertTrue(rebound_widget.property("ea.nativeWindowOverlay"))
        self.assertEqual(len(created_widgets), 1)
        self.assertEqual(first_widget.clear_calls, 2)
        self.assertEqual(len(first_widget.add_mesh_calls), 2)
        self.assertIs(first_widget.add_mesh_calls[-1]["mesh"], blocks[2])
        self.assertEqual(binder._widget_state[first_widget].step_index, 2)

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
        widget_state = binder._widget_state[widget]
        self.assertEqual(widget_state.session_id, "")
        self.assertEqual(widget_state.transport_revision, 0)
        self.assertEqual(widget_state.manifest_path, "")
        self.assertEqual(widget_state.entry_path, "")

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
        binder._set_widget_state(
            widget,
            session_id="session-tests",
            transport_revision=1,
            manifest_path="",
            entry_path="",
            step_index=0,
        )
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

    def test_capture_and_restore_view_state_use_existing_camera_helpers(self) -> None:
        binder = DpfViewerWidgetBinder(
            interactor_factory=lambda parent: _FakeInteractor(parent),
            dataset_loader=lambda _path: _FakeMesh("stress"),
        )
        widget = _FakeInteractor()
        binder._set_widget_state(
            widget,
            session_id="session-tests",
            transport_revision=1,
            manifest_path="",
            entry_path="",
            step_index=0,
        )
        widget.camera_position = [
            (4.0, 5.0, 6.0),
            (1.0, 1.5, 2.0),
            (0.0, 0.0, 1.0),
        ]

        captured = binder.capture_view_state(widget)
        restored = binder.restore_view_state(
            widget,
            {
                "position": [7.0, 8.0, 9.0],
                "focal_point": [1.0, 2.0, 3.0],
                "viewup": [0.0, 1.0, 0.0],
                "view_angle": 21.0,
            },
        )

        self.assertEqual(captured["position"], [4.0, 5.0, 6.0])
        self.assertTrue(restored)
        self.assertEqual(
            widget.camera_position,
            [
                (7.0, 8.0, 9.0),
                (1.0, 2.0, 3.0),
                (0.0, 1.0, 0.0),
            ],
        )
        self.assertEqual(widget.camera.view_angle, 21.0)
        self.assertGreaterEqual(widget.render_calls, 1)

    def test_capture_preview_image_uses_live_interactor_screenshot(self) -> None:
        binder = DpfViewerWidgetBinder(
            interactor_factory=lambda parent: _FakeInteractor(parent),
            dataset_loader=lambda _path: _FakeMesh("stress"),
        )
        widget = _FakeInteractor()
        binder._set_widget_state(
            widget,
            session_id="session-tests",
            transport_revision=1,
            manifest_path="",
            entry_path="",
            step_index=0,
        )

        captured = binder.capture_preview_image(widget)

        self.assertIsInstance(captured, QImage)
        self.assertFalse(captured.isNull())
        self.assertEqual(captured.size(), widget.screenshot_image.size())
        self.assertEqual(widget.screenshot_calls, 1)
        self.assertEqual(widget.screenshot_kwargs, [{"return_img": True}])


class DpfViewerRenderStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _bind(self, dataset, *, options, interactor_factory=None, current_widget=None, camera_state=None):  # noqa: ANN001
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            binder = DpfViewerWidgetBinder(
                interactor_factory=interactor_factory or (lambda parent: _FakeInteractor(parent)),
                dataset_loader=lambda _path: dataset,
            )
            request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                options=options,
                current_widget=current_widget,
                camera_state=camera_state,
            )
            widget = binder.bind_widget(request)
        return binder, widget

    def test_render_style_options_flow_into_add_mesh(self) -> None:
        _binder, widget = self._bind(
            _FakeMesh("stress"),
            options={
                "colormap": "turbo",
                "scalar_range_mode": "custom",
                "scalar_range_min": "5",
                "scalar_range_max": "1",
                "show_scalar_bar": False,
            },
        )
        call = widget.add_mesh_calls[0]
        self.assertEqual(call["cmap"], "turbo")
        self.assertEqual(call["clim"], (1.0, 5.0))
        self.assertFalse(call["show_scalar_bar"])
        self.assertIsNone(call["scalar_bar_args"])
        self.assertIsNone(call["component"])

    def test_auto_range_mode_leaves_clim_unset(self) -> None:
        _binder, widget = self._bind(
            _FakeMesh("stress"),
            options={
                "scalar_range_mode": "auto",
                "scalar_range_min": "5",
                "scalar_range_max": "10",
            },
        )
        self.assertIsNone(widget.add_mesh_calls[0]["clim"])
        self.assertTrue(widget.add_mesh_calls[0]["show_scalar_bar"])
        self.assertIsInstance(widget.add_mesh_calls[0]["scalar_bar_args"], dict)

    def test_component_selection_on_vector_point_data(self) -> None:
        dataset = _FakeVectorMesh("displacement")
        _binder, widget = self._bind(dataset, options={"result_component": "y"})
        call = widget.add_mesh_calls[0]
        self.assertEqual(call["component"], 1)
        self.assertEqual(call["scalars"], "displacement")
        self.assertEqual(call["scalar_bar_args"]["title"], "displacement (Y)")

    def test_magnitude_component_renders_with_none_index_and_label(self) -> None:
        dataset = _FakeVectorMesh("displacement")
        _binder, widget = self._bind(dataset, options={"result_component": "magnitude"})
        call = widget.add_mesh_calls[0]
        self.assertIsNone(call["component"])
        self.assertEqual(call["scalar_bar_args"]["title"], "displacement (Magnitude)")

    def test_component_is_ignored_for_scalar_arrays(self) -> None:
        dataset = _FakeScalarPointMesh("temperature")
        _binder, widget = self._bind(dataset, options={"result_component": "z"})
        call = widget.add_mesh_calls[0]
        self.assertIsNone(call["component"])
        self.assertNotIn("title", call["scalar_bar_args"])

    def test_numeric_deform_scale_warps_vector_dataset(self) -> None:
        dataset = _FakeVectorMesh("displacement")
        _binder, widget = self._bind(dataset, options={"deform_scale": "2.5"})
        self.assertEqual(dataset.warp_calls, [("displacement", 2.5)])
        self.assertIs(widget.add_mesh_calls[0]["mesh"], dataset.warp_result)

    def test_auto_deform_scale_uses_bbox_fraction_of_max_magnitude(self) -> None:
        dataset = _FakeVectorMesh(
            "displacement",
            vectors=[[0.0, 0.0, 0.0], [0.03, 0.04, 0.0]],
            bounds=(0.0, 1.0, 0.0, 1.0, 0.0, 1.0),
        )
        _binder, _widget = self._bind(dataset, options={"deform_scale": "auto"})
        self.assertEqual(len(dataset.warp_calls), 1)
        expected_factor = 0.1 * (3.0**0.5) / 0.05
        self.assertAlmostEqual(dataset.warp_calls[0][1], expected_factor, places=9)

    def test_deform_scale_off_and_scalar_results_do_not_warp(self) -> None:
        vector_dataset = _FakeVectorMesh("displacement")
        self._bind(vector_dataset, options={"deform_scale": "off"})
        self.assertEqual(vector_dataset.warp_calls, [])

        scalar_dataset = _FakeScalarPointMesh("temperature")
        self._bind(scalar_dataset, options={"deform_scale": "2.0"})
        self.assertEqual(scalar_dataset.warp_calls, [])

    def test_unavailable_cmap_falls_back_to_default_colormap(self) -> None:
        _binder, widget = self._bind(
            _FakeMesh("stress"),
            options={"colormap": "turbo"},
            interactor_factory=lambda parent: _CmapRejectingInteractor(parent),
        )
        self.assertEqual(len(widget.add_mesh_calls), 2)
        self.assertIn("cmap", widget.add_mesh_calls[0])
        self.assertNotIn("cmap", widget.add_mesh_calls[1])

    def test_same_session_repopulate_without_camera_state_preserves_camera(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            binder = DpfViewerWidgetBinder(
                interactor_factory=lambda parent: _FakeInteractor(parent),
                dataset_loader=lambda _path: _FakeMesh("stress"),
            )
            first_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                camera_state={
                    "position": [5.0, 6.0, 7.0],
                    "focal_point": [0.0, 0.0, 0.0],
                    "viewup": [0.0, 1.0, 0.0],
                },
            )
            widget = binder.bind_widget(first_request)
            self.assertEqual(widget.reset_camera_calls, 0)
            first_camera_position = widget.camera_position

            second_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                current_widget=widget,
                camera_state={},
                options={"show_mesh_edges": True},
            )
            rebound = binder.bind_widget(second_request)

        self.assertIs(rebound, widget)
        self.assertEqual(widget.reset_camera_calls, 0)
        self.assertEqual(widget.camera_position, first_camera_position)

    def test_fresh_bind_without_camera_state_still_resets_camera(self) -> None:
        _binder, widget = self._bind(_FakeMesh("stress"), options={}, camera_state={})
        self.assertEqual(widget.reset_camera_calls, 1)

    def test_render_stats_report_component_extremes_with_entity_ids(self) -> None:
        dataset = _FakeVectorMesh(
            "displacement",
            vectors=[[0.0, 0.0, 0.0], [0.03, 0.04, 0.0], [0.01, -0.06, 0.0]],
        )
        binder, widget = self._bind(dataset, options={"result_component": "y"})
        stats = binder.render_stats(widget)
        self.assertEqual(stats["array"], "displacement")
        self.assertEqual(stats["component"], "Y")
        self.assertAlmostEqual(stats["min"], -0.06)
        self.assertAlmostEqual(stats["max"], 0.04)
        self.assertEqual(stats["min_entity_id"], 103)
        self.assertEqual(stats["max_entity_id"], 102)
        self.assertEqual(stats["entity_kind"], "node")

    def test_render_stats_use_magnitude_for_default_component(self) -> None:
        dataset = _FakeVectorMesh(
            "displacement",
            vectors=[[0.0, 0.0, 0.0], [0.03, 0.04, 0.0]],
        )
        binder, widget = self._bind(dataset, options={})
        stats = binder.render_stats(widget)
        self.assertEqual(stats["component"], "Magnitude")
        self.assertAlmostEqual(stats["min"], 0.0)
        self.assertAlmostEqual(stats["max"], 0.05)

    def test_hover_probe_observer_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            binder = DpfViewerWidgetBinder(
                interactor_factory=lambda parent: _ProbeInteractor(parent),
                dataset_loader=lambda _path: _FakeVectorMesh("displacement"),
            )

            first_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                options={"hover_probe": True},
            )
            widget = binder.bind_widget(first_request)
            self.assertEqual(len(widget.iren.observers), 1)

            second_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                current_widget=widget,
                options={"hover_probe": False},
            )
            rebound = binder.bind_widget(second_request)
            self.assertIs(rebound, widget)
            self.assertEqual(len(widget.iren.observers), 0)

            third_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                current_widget=widget,
                options={"hover_probe": True},
            )
            binder.bind_widget(third_request)
            self.assertEqual(len(widget.iren.observers), 1)

            binder.release_widget(
                ViewerWidgetReleaseRequest(
                    workspace_id="ws-tests",
                    node_id="node-tests",
                    session_id="session-tests",
                    backend_id=DpfViewerWidgetBinder.backend_id,
                    transport_revision=3,
                    widget=widget,
                    reason="tests",
                )
            )
            self.assertEqual(len(widget.iren.observers), 0)

    def test_minmax_markers_toggle_adds_point_labels(self) -> None:
        dataset = _FakeVectorMesh(
            "displacement",
            vectors=[[0.0, 0.0, 0.0], [0.03, 0.04, 0.0], [0.01, 0.01, 0.0]],
        )
        _binder, widget = self._bind(
            dataset,
            options={"show_minmax_markers": True},
            interactor_factory=lambda parent: _ProbeInteractor(parent),
        )
        self.assertEqual(len(widget.add_point_labels_calls), 1)
        call = widget.add_point_labels_calls[0]
        self.assertEqual(len(call["points"]), 2)
        self.assertTrue(str(call["labels"][0]).startswith("Min"))
        self.assertTrue(str(call["labels"][1]).startswith("Max"))

        plain_dataset = _FakeVectorMesh("displacement")
        _binder2, plain_widget = self._bind(
            plain_dataset,
            options={},
            interactor_factory=lambda parent: _ProbeInteractor(parent),
        )
        self.assertEqual(plain_widget.add_point_labels_calls, [])

    def test_render_stats_cleared_on_release(self) -> None:
        dataset = _FakeVectorMesh("displacement")
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            binder = DpfViewerWidgetBinder(
                interactor_factory=lambda parent: _FakeInteractor(parent),
                dataset_loader=lambda _path: dataset,
            )
            request = _bind_request(manifest_path=manifest_path, entry_path=entry_path)
            widget = binder.bind_widget(request)
            self.assertTrue(binder.render_stats(widget))
            binder.release_widget(
                ViewerWidgetReleaseRequest(
                    workspace_id="ws-tests",
                    node_id="node-tests",
                    session_id="session-tests",
                    backend_id=DpfViewerWidgetBinder.backend_id,
                    transport_revision=3,
                    reason="tests",
                    widget=widget,
                )
            )
            self.assertEqual(binder.render_stats(widget), {})


class ViewerCanvasThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_light_shell_theme_switches_canvas_and_scalar_bar_styles(self) -> None:
        binder = DpfViewerWidgetBinder()
        widget = _FakeInteractor()
        set_viewer_canvas_dark(False)
        try:
            style = viewer_canvas_style()
            self.assertFalse(style["dark"])
            args = scalar_bar_args_for_viewport(400, 300, themed=True)
            self.assertEqual(args["color"], "#2A3441")
            self.assertEqual(args["font_family"], "arial")
            self.assertTrue(binder.apply_canvas_theme(widget))
            self.assertEqual(
                widget.set_background_calls[-1],
                {"color": "#E9EEF4", "top": "#FBFCFE"},
            )
            self.assertGreaterEqual(widget.render_calls, 1)
        finally:
            set_viewer_canvas_dark(True)

    def test_untheme_scalar_bar_args_keep_export_defaults(self) -> None:
        args = scalar_bar_args_for_viewport(400, 300)
        self.assertNotIn("color", args)
        self.assertNotIn("font_family", args)

    def test_apply_canvas_theme_requires_widget(self) -> None:
        binder = DpfViewerWidgetBinder()
        self.assertFalse(binder.apply_canvas_theme(None))

    def test_viewer_background_option_overrides_theme_canvas(self) -> None:
        set_viewer_canvas_dark(True)
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            binder = DpfViewerWidgetBinder(
                interactor_factory=lambda parent: _FakeInteractor(parent),
                dataset_loader=lambda _path: _FakeMesh("node_id", "stress"),
            )
            request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                options={"viewer_background": "white"},
            )
            widget = binder.bind_widget(request)

        self.assertEqual(
            widget.set_background_calls[-1],
            {"color": "#FFFFFF", "top": "#FFFFFF"},
        )
        self.assertEqual(widget.add_text_calls[-1]["color"], "#26303B")
        self.assertEqual(widget.add_mesh_calls[0]["scalar_bar_args"]["color"], "#2A3441")
        # The theme sweep must keep the explicit override.
        self.assertTrue(binder.apply_canvas_theme(widget, {"viewer_background": "white"}))
        self.assertEqual(
            widget.set_background_calls[-1],
            {"color": "#FFFFFF", "top": "#FFFFFF"},
        )

    def test_rebind_keeps_live_camera_over_stale_payload_state(self) -> None:
        set_viewer_canvas_dark(True)
        persisted_camera = {
            "position": [1.0, 2.0, 3.0],
            "focal_point": [0.0, 0.0, 0.0],
            "viewup": [0.0, 1.0, 0.0],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path, entry_path = _write_transport_bundle(Path(temp_dir))
            binder = DpfViewerWidgetBinder(
                interactor_factory=lambda parent: _FakeInteractor(parent),
                dataset_loader=lambda _path: _FakeMesh("node_id", "stress"),
            )
            first_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                camera_state=persisted_camera,
            )
            widget = binder.bind_widget(first_request)
            self.assertEqual(widget.camera_position[0], (1.0, 2.0, 3.0))

            # Simulate the user orbiting the live view, then a view-option
            # change repopulating with the stale persisted camera payload.
            widget.camera_position = [
                (9.0, 8.0, 7.0),
                (0.5, 0.5, 0.5),
                (0.0, 0.0, 1.0),
            ]
            widget.camera.position = (9.0, 8.0, 7.0)
            widget.camera.focal_point = (0.5, 0.5, 0.5)
            widget.camera.up = (0.0, 0.0, 1.0)
            rebind_request = _bind_request(
                manifest_path=manifest_path,
                entry_path=entry_path,
                camera_state=persisted_camera,
                current_widget=widget,
                options={"show_mesh_edges": True},
            )
            binder.bind_widget(rebind_request)

        self.assertEqual(widget.camera_position[0], (9.0, 8.0, 7.0))
        self.assertEqual(widget.camera_position[1], (0.5, 0.5, 0.5))


if __name__ == "__main__":
    unittest.main()
