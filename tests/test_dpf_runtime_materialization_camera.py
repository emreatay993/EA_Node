from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ea_node_editor.execution.worker_services import WorkerServices


class _FakePlotterCamera:
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


class _FakePlotter:
    def __init__(self, *, off_screen: bool) -> None:
        self.off_screen = off_screen
        self.window_size = [1024, 768]
        self.camera = _FakePlotterCamera()
        self.camera_position = None
        self.add_mesh_calls: list[dict[str, object]] = []
        self.view_isometric_calls = 0
        self.show_calls: list[dict[str, object]] = []
        self.closed = False

    def add_mesh(self, dataset, **kwargs):  # noqa: ANN001
        self.add_mesh_calls.append({"dataset": dataset, **kwargs})

    def view_isometric(self) -> None:
        self.view_isometric_calls += 1

    def show(self, **kwargs) -> None:  # noqa: ANN003
        self.show_calls.append(dict(kwargs))

    def close(self) -> None:
        self.closed = True


class _FakePyVistaModule:
    def __init__(self) -> None:
        self.plotters: list[_FakePlotter] = []

    def Plotter(self, *, off_screen: bool):  # noqa: N802
        plotter = _FakePlotter(off_screen=off_screen)
        self.plotters.append(plotter)
        return plotter


class DpfRuntimeMaterializationCameraTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = WorkerServices().dpf_runtime_service
        self.fake_pyvista = _FakePyVistaModule()
        self.service._pyvista_module = lambda: self.fake_pyvista  # type: ignore[method-assign]
        self.service._build_viewer_dataset = lambda *_args, **_kwargs: {"dataset": "preview"}  # type: ignore[method-assign]
        self.service._preview_dataset = lambda dataset: dataset  # type: ignore[method-assign]
        self.service._preferred_array_name = lambda _dataset: "stress"  # type: ignore[method-assign]

    def test_write_png_export_applies_explicit_camera_state_instead_of_isometric_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "preview.png"
            self.service._write_png_export(  # noqa: SLF001
                object(),
                object(),
                output_path,
                camera_state={
                    "position": [5.0, 6.0, 7.0],
                    "focal_point": [0.0, 0.0, 0.0],
                    "viewup": [0.0, 1.0, 0.0],
                    "parallel_projection": True,
                    "parallel_scale": 4.0,
                    "view_angle": 18.0,
                },
            )

        plotter = self.fake_pyvista.plotters[-1]
        self.assertEqual(
            plotter.camera_position,
            [
                (5.0, 6.0, 7.0),
                (0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
            ],
        )
        self.assertTrue(plotter.camera.parallel_projection)
        self.assertEqual(plotter.camera.parallel_scale, 4.0)
        self.assertEqual(plotter.camera.view_angle, 18.0)
        self.assertEqual(plotter.view_isometric_calls, 0)
        self.assertEqual(
            plotter.add_mesh_calls[-1]["scalar_bar_args"],
            {
                "vertical": True,
                "title_font_size": 11,
                "label_font_size": 9,
                "height": 0.52,
                "width": 0.10,
                "position_x": 0.86,
                "position_y": 0.08,
            },
        )
        self.assertEqual(plotter.show_calls[-1]["screenshot"], str(output_path))
        self.assertTrue(plotter.closed)

    def test_write_png_export_falls_back_to_isometric_view_without_camera_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "preview.png"
            self.service._write_png_export(object(), object(), output_path)  # noqa: SLF001

        plotter = self.fake_pyvista.plotters[-1]
        self.assertEqual(plotter.view_isometric_calls, 1)
        self.assertEqual(
            plotter.add_mesh_calls[-1]["scalar_bar_args"],
            {
                "vertical": True,
                "title_font_size": 11,
                "label_font_size": 9,
                "height": 0.52,
                "width": 0.10,
                "position_x": 0.86,
                "position_y": 0.08,
            },
        )
        self.assertEqual(plotter.show_calls[-1]["screenshot"], str(output_path))
        self.assertTrue(plotter.closed)


if __name__ == "__main__":
    unittest.main()
