from __future__ import annotations

import math
import unittest

from vtkmodules.vtkRenderingCore import vtkCamera, vtkRenderer

from ea_node_editor.ui_qml.engineering_viewer_orbit import (
    create_pivot_marker_actor,
    depth_pick_world_point,
    orbit_camera_about_point,
    trackball_orbit_angles,
    visible_bounds_center,
    world_to_display_point,
)


def _camera(*, parallel: bool = False) -> vtkCamera:
    camera = vtkCamera()
    camera.SetPosition(3.0, -4.0, 5.0)
    camera.SetFocalPoint(0.5, 0.2, -0.3)
    camera.SetViewUp(0.0, 0.0, 1.0)
    camera.OrthogonalizeViewUp()
    camera.SetParallelProjection(parallel)
    camera.SetClippingRange(0.1, 100.0)
    return camera


def _normalized_device_xy(camera: vtkCamera, point: tuple[float, float, float]) -> tuple[float, float]:
    matrix = camera.GetCompositeProjectionTransformMatrix(1.5, -1.0, 1.0)
    x_value, y_value, _z_value, weight = matrix.MultiplyPoint((*point, 1.0))
    return x_value / weight, y_value / weight


class _FakeRenderer:
    def __init__(
        self,
        *,
        depth: float = 1.0,
        world_point: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0),
        bounds: tuple[float, ...] = (1.0, -1.0, 1.0, -1.0, 1.0, -1.0),
        display_point: tuple[float, float, float] = (0.0, 0.0, 0.5),
    ) -> None:
        self.depth = depth
        self.world_point = world_point
        self.bounds = bounds
        self.display_point = display_point
        self.display_input: tuple[float, float, float] | None = None

    def GetZ(self, _x: int, _y: int) -> float:  # noqa: N802
        return self.depth

    def SetDisplayPoint(self, x: float, y: float, z: float) -> None:  # noqa: N802
        self.display_input = (x, y, z)

    def DisplayToWorld(self) -> None:  # noqa: N802
        return None

    def GetWorldPoint(self) -> tuple[float, float, float, float]:  # noqa: N802
        return self.world_point

    def ComputeVisiblePropBounds(self) -> tuple[float, ...]:  # noqa: N802
        return self.bounds

    def SetWorldPoint(self, *_values: float) -> None:  # noqa: N802
        return None

    def WorldToDisplay(self) -> None:  # noqa: N802
        return None

    def GetDisplayPoint(self) -> tuple[float, float, float]:  # noqa: N802
        return self.display_point


class EngineeringViewerOrbitTests(unittest.TestCase):
    def test_trackball_angles_match_vtk_trackball_camera_formula(self) -> None:
        azimuth, elevation = trackball_orbit_angles(50, -25, (1000, 500), 10.0)
        self.assertAlmostEqual(azimuth, -10.0)
        self.assertAlmostEqual(elevation, 10.0)
        self.assertEqual(trackball_orbit_angles(3, 4, (0, 0), 0.0), (0.0, 0.0))

    def test_orbit_about_focal_point_matches_vtk_azimuth_and_elevation(self) -> None:
        expected = _camera()
        expected.Azimuth(17.0)
        expected.Elevation(-23.0)
        expected.OrthogonalizeViewUp()
        actual = _camera()

        self.assertTrue(
            orbit_camera_about_point(actual, actual.GetFocalPoint(), azimuth=17.0, elevation=-23.0)
        )

        for getter in ("GetPosition", "GetFocalPoint", "GetViewUp"):
            for expected_value, actual_value in zip(
                getattr(expected, getter)(),
                getattr(actual, getter)(),
                strict=True,
            ):
                self.assertAlmostEqual(expected_value, actual_value, places=9, msg=getter)

    def test_orbit_keeps_off_center_pivot_fixed_on_screen(self) -> None:
        pivot = (1.7, -0.9, 0.8)
        for parallel in (False, True):
            with self.subTest(parallel_projection=parallel):
                camera = _camera(parallel=parallel)
                screen_before = _normalized_device_xy(camera, pivot)
                distance_before = math.dist(camera.GetPosition(), pivot)
                focal_before = camera.GetFocalPoint()

                for _step in range(20):
                    self.assertTrue(
                        orbit_camera_about_point(camera, pivot, azimuth=13.0, elevation=-11.0)
                    )

                for before, after in zip(screen_before, _normalized_device_xy(camera, pivot), strict=True):
                    self.assertAlmostEqual(before, after, places=9)
                self.assertAlmostEqual(math.dist(camera.GetPosition(), pivot), distance_before, places=9)
                self.assertNotAlmostEqual(math.dist(camera.GetFocalPoint(), focal_before), 0.0)
                view_up = camera.GetViewUp()
                direction = camera.GetDirectionOfProjection()
                self.assertAlmostEqual(math.hypot(*view_up), 1.0, places=9)
                self.assertAlmostEqual(sum(a * b for a, b in zip(view_up, direction, strict=True)), 0.0, places=9)

    def test_orbit_rejects_degenerate_camera(self) -> None:
        class _DegenerateCamera:
            def GetPosition(self) -> tuple[float, float, float]:  # noqa: N802
                return (0.0, 0.0, 0.0)

            def GetFocalPoint(self) -> tuple[float, float, float]:  # noqa: N802
                return (0.0, 0.0, 0.0)

            def GetViewUp(self) -> tuple[float, float, float]:  # noqa: N802
                return (0.0, 0.0, 0.0)

        self.assertFalse(
            orbit_camera_about_point(_DegenerateCamera(), (1.0, 0.0, 0.0), azimuth=5.0, elevation=5.0)
        )
        self.assertFalse(orbit_camera_about_point(object(), (1.0, 0.0, 0.0), azimuth=5.0, elevation=5.0))

    def test_depth_pick_unprojects_drawn_pixels_and_ignores_background(self) -> None:
        self.assertIsNone(depth_pick_world_point(_FakeRenderer(depth=1.0), 10, 20))
        self.assertIsNone(depth_pick_world_point(object(), 10, 20))

        renderer = _FakeRenderer(depth=0.25, world_point=(2.0, 4.0, 6.0, 2.0))
        self.assertEqual(depth_pick_world_point(renderer, 10, 20), (1.0, 2.0, 3.0))
        self.assertEqual(renderer.display_input, (10.0, 20.0, 0.25))

        self.assertIsNone(
            depth_pick_world_point(_FakeRenderer(depth=0.25, world_point=(1.0, 1.0, 1.0, 0.0)), 10, 20)
        )

    def test_visible_bounds_center_rejects_empty_and_invalid_bounds(self) -> None:
        self.assertEqual(
            visible_bounds_center(_FakeRenderer(bounds=(-2.0, 4.0, -1.0, 1.0, 0.0, 2.0))),
            (1.0, 0.0, 1.0),
        )
        self.assertIsNone(visible_bounds_center(vtkRenderer()))
        self.assertIsNone(
            visible_bounds_center(_FakeRenderer(bounds=(0.0, math.inf, 0.0, 1.0, 0.0, 1.0)))
        )
        self.assertIsNone(visible_bounds_center(object()))

    def test_world_to_display_point_requires_depth_range(self) -> None:
        self.assertEqual(
            world_to_display_point(_FakeRenderer(display_point=(12.0, 34.0, 0.5)), (0.0, 0.0, 0.0)),
            (12.0, 34.0),
        )
        self.assertIsNone(
            world_to_display_point(_FakeRenderer(display_point=(12.0, 34.0, -0.2)), (0.0, 0.0, 0.0))
        )

    def test_pivot_marker_is_unpickable_display_disc_with_outline_under_fill(self) -> None:
        actor = create_pivot_marker_actor((120.0, 80.0), 4.0, 1.5)

        self.assertEqual(actor.GetPosition(), (120.0, 80.0))
        self.assertEqual(actor.GetPositionCoordinate().GetCoordinateSystemAsString(), "Display")
        self.assertFalse(actor.GetPickable())
        polydata = actor.GetMapper().GetInput()
        self.assertEqual(polydata.GetNumberOfPolys(), 2)
        colors = polydata.GetCellData().GetScalars()
        self.assertEqual(colors.GetTuple3(0), (31.0, 41.0, 55.0))
        self.assertEqual(colors.GetTuple3(1), (255.0, 224.0, 102.0))
        bounds = polydata.GetBounds()
        self.assertAlmostEqual(bounds[1], 5.5)
        self.assertAlmostEqual(bounds[0], -5.5)


if __name__ == "__main__":
    unittest.main()
