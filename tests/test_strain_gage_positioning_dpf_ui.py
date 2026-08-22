from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

pv = pytest.importorskip("pyvista")
pytest.importorskip("PyQt6")
pytest.importorskip("pyvistaqt")

REPO_ROOT = Path(__file__).resolve().parents[1]
SG_ROOT = REPO_ROOT / "scripts" / "Strain_Gage_Positioning" / "modular_version"
if str(SG_ROOT) not in sys.path:
    sys.path.insert(0, str(SG_ROOT))

from app import dpf_loader  # noqa: E402
from app import main_window  # noqa: E402
from app.ui_tools import (  # noqa: E402
    PLACEMENT_COLUMNS,
    build_gage_placements,
    project_to_tangent,
    surface_angle_from_axis,
    surface_axes_from_angle,
)


BENCHMARK_RST = Path(
    r"C:\Users\emre_\OneDrive\Desktop\J\ANSYS\Benchmark"
    r"\ENFO_conversion\enfo_conversion_example_files\dp0\SYS-6\MECH\file.rst"
)


def _plane_surface():
    surface = pv.Plane(
        center=(0.0, 0.0, 0.0),
        direction=(0.0, 0.0, 1.0),
        i_size=2.0,
        j_size=2.0,
    )
    return surface.compute_normals(point_normals=True, cell_normals=True, inplace=False)


def _candidate_df():
    return pd.DataFrame({
        "Node": [10, 11],
        "X": [0.0, 0.5],
        "Y": [0.0, 0.0],
        "Z": [0.0, 0.0],
        "Best_Strain": [120.0, 80.0],
        "Best_Angle": [0.0, 90.0],
        "Local_Std": [1.0, 2.0],
        "Quality": [10.0, 9.0],
    })


def test_rst_set_summary_does_not_dump_many_sets():
    assert main_window._format_rst_set_summary(range(1, 74)) == "sets 1-73 (73 sets)"
    assert main_window._format_rst_set_summary([1, 2, 5, 9, 12, 20, 30]) == "sets 1,2,5,...30 (7 sets)"


class _FakeCamera:
    def copy(self):
        return "camera-copy"


class _FakePlotter:
    def __init__(self):
        self.camera = _FakeCamera()
        self.add_mesh_calls = []
        self.clear_count = 0
        self.reset_count = 0
        self.render_count = 0

    def add_mesh(self, *args, **kwargs):
        self.add_mesh_calls.append((args, kwargs))

    def clear(self):
        self.clear_count += 1

    def reset_camera(self):
        self.reset_count += 1

    def render(self):
        self.render_count += 1


class _FakeVisualizationPanel:
    def __init__(self, plotter):
        self.vtk_widget = plotter
        self.enabled_values = []
        self._settings = {
            "show_surface_mesh": True,
            "surface_mesh_opacity": 0.42,
            "show_surface_normals": True,
            "show_gage_axes": True,
        }

    def get_settings(self):
        return dict(self._settings)

    def set_surface_placement_enabled(self, value):
        self.enabled_values.append(bool(value))


class _FakeInputPanel:
    def __init__(self):
        self.labels = []

    def set_file_label(self, label):
        self.labels.append(label)


class _FakeGagePlacementTool:
    def __init__(self):
        self.contexts = []

    def set_context(self, surface_info, candidates_df):
        self.contexts.append((surface_info, candidates_df))


def _preview_window(surface=None):
    plotter = _FakePlotter()
    window = SimpleNamespace(
        rst_surface_mesh={"surface": surface or _plane_surface()},
        visualization_panel=_FakeVisualizationPanel(plotter),
        gage_placement_tool=_FakeGagePlacementTool(),
        last_results={},
        preloaded_dataset=("old",),
        input_file=None,
        rst_named_selection="NS",
        input_panel=_FakeInputPanel(),
        project_dir=str(REPO_ROOT),
    )
    window.clear_visualization = (
        lambda preserve_camera=False: main_window.MainWindow.clear_visualization(
            window, preserve_camera=preserve_camera
        )
    )
    window.display_rst_surface_preview = (
        lambda preserve_camera=False: main_window.MainWindow.display_rst_surface_preview(
            window, preserve_camera=preserve_camera
        )
    )
    window._add_rst_surface_mesh = (
        lambda plotter: main_window.MainWindow._add_rst_surface_mesh(window, plotter)
    )
    return window


def test_surface_axes_are_orthonormal_and_angle_wraps():
    axis_x, axis_y, normal = surface_axes_from_angle((0.0, 0.0, 1.0), 195.0)

    assert np.isclose(np.linalg.norm(axis_x), 1.0)
    assert np.isclose(np.linalg.norm(axis_y), 1.0)
    assert np.isclose(np.linalg.norm(normal), 1.0)
    assert np.isclose(np.dot(axis_x, normal), 0.0, atol=1.0e-12)
    assert np.isclose(np.dot(axis_y, normal), 0.0, atol=1.0e-12)
    assert np.isclose(np.dot(axis_x, axis_y), 0.0, atol=1.0e-12)
    assert np.isclose(surface_angle_from_axis(normal, axis_x), 15.0)


def test_manual_direction_projects_to_tangent_plane():
    normal = np.asarray((0.0, 0.0, 1.0))
    projected = project_to_tangent((1.0, 1.0, 5.0), normal)

    assert np.allclose(projected, (1.0, 1.0, 0.0))
    assert np.isclose(surface_angle_from_axis(normal, projected), 45.0)


def test_build_gage_placements_csv_shape_and_override_axes():
    candidates = _candidate_df()
    original_columns = list(candidates.columns)
    records = build_gage_placements(
        candidates,
        _plane_surface(),
        named_selection="NS_FACES_FANDUCT",
        overrides={0: {
            "origin": np.asarray((0.0, 0.0, 0.0)),
            "direction_pick": np.asarray((1.0, 1.0, 5.0)),
        }},
    )
    df = pd.DataFrame(records, columns=PLACEMENT_COLUMNS)

    assert list(candidates.columns) == original_columns
    assert list(df.columns) == PLACEMENT_COLUMNS
    assert len(df) == 2
    assert bool(df.loc[0, "Manual_Override"])
    assert not bool(df.loc[1, "Manual_Override"])
    assert np.isclose(df.loc[0, "Surface_Angle_Deg"], 45.0)
    axis_x = df.loc[0, ["Axis_X_X", "Axis_X_Y", "Axis_X_Z"]].to_numpy(float)
    axis_y = df.loc[0, ["Axis_Y_X", "Axis_Y_Y", "Axis_Y_Z"]].to_numpy(float)
    normal = df.loc[0, ["Normal_X", "Normal_Y", "Normal_Z"]].to_numpy(float)
    assert np.isclose(np.linalg.norm(axis_x), 1.0)
    assert np.isclose(np.linalg.norm(axis_y), 1.0)
    assert np.isclose(np.linalg.norm(normal), 1.0)
    assert np.isclose(np.dot(axis_x, normal), 0.0, atol=1.0e-12)
    assert np.isclose(np.dot(axis_y, normal), 0.0, atol=1.0e-12)


def test_rst_surface_preview_draws_mesh_without_analysis_results():
    window = _preview_window()
    plotter = window.visualization_panel.vtk_widget

    main_window.MainWindow.display_rst_surface_preview(window, preserve_camera=False)

    assert plotter.clear_count == 1
    assert plotter.reset_count == 1
    assert plotter.render_count == 1
    assert len(plotter.add_mesh_calls) == 1
    _, kwargs = plotter.add_mesh_calls[0]
    assert kwargs["color"] == "lightgray"
    assert kwargs["opacity"] == 0.42
    assert kwargs["show_edges"] is True


def test_refresh_visualization_redraws_preview_before_analysis():
    window = _preview_window()
    plotter = window.visualization_panel.vtk_widget

    main_window.MainWindow.refresh_visualization(window)

    assert plotter.clear_count == 1
    assert plotter.reset_count == 0
    assert plotter.render_count == 1
    assert len(plotter.add_mesh_calls) == 1


def test_text_input_resets_rst_preview_state(monkeypatch, tmp_path):
    input_file = tmp_path / "strain.txt"
    input_file.write_text("dummy", encoding="utf-8")
    window = _preview_window()
    clear_calls = []
    window.clear_visualization = lambda preserve_camera=False: clear_calls.append(preserve_camera)

    monkeypatch.setattr(
        main_window.QFileDialog,
        "getOpenFileNames",
        lambda *args, **kwargs: ([str(input_file)], ""),
    )

    main_window.MainWindow.load_strain_data(window)

    assert window.input_file == str(input_file)
    assert window.preloaded_dataset is None
    assert window.rst_surface_mesh is None
    assert window.rst_named_selection is None
    assert window.visualization_panel.enabled_values == [False]
    assert window.gage_placement_tool.contexts[-1] == (None, None)
    assert clear_calls == [False]


@pytest.mark.skipif(not BENCHMARK_RST.exists(), reason="benchmark .rst is not available")
@pytest.mark.skipif(not dpf_loader.dpf_available(), reason="ansys-dpf-core is not available")
def test_benchmark_named_selection_surface_has_normals():
    info = dpf_loader.load_rst_surface_mesh(
        BENCHMARK_RST,
        named_selection="NS_FACES_FANDUCT",
    )
    surface = info["surface"]
    normals = np.asarray(surface.point_data["Normals"], dtype=float)
    norms = np.linalg.norm(normals, axis=1)

    assert info["n_points"] > 0
    assert info["n_cells"] > 0
    assert normals.shape[0] == surface.n_points
    assert np.allclose(norms, 1.0, atol=1.0e-6)
