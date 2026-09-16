# Purpose: Camera math and screen aids for orbiting the Model Viewer around the point under the cursor.
# Map: feature_routes/viewer_session_overlay_fullscreen.md
# Tests: tests/test_engineering_viewer_orbit.py, tests/test_engineering_viewer_widget_binder.py
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

Vector = tuple[float, float, float]

# vtkInteractorStyleTrackballCamera::Rotate turns the camera by
# -20 / window-extent * delta * MotionFactor degrees; keep the same feel.
_TRACKBALL_DEGREES_PER_EXTENT = -20.0
DEFAULT_TRACKBALL_MOTION_FACTOR = 10.0
_MARKER_SIDES = 24
_MARKER_FILL_RGB = (255, 224, 102)
_MARKER_OUTLINE_RGB = (31, 41, 55)


def trackball_orbit_angles(
    delta_x: float,
    delta_y: float,
    render_size: Sequence[int],
    motion_factor: float = DEFAULT_TRACKBALL_MOTION_FACTOR,
) -> tuple[float, float]:
    """Return (azimuth, elevation) degrees for a mouse delta, matching VTK's trackball."""
    width, height = (max(1, int(value)) for value in render_size[:2])
    azimuth = _TRACKBALL_DEGREES_PER_EXTENT / width * float(delta_x) * motion_factor
    elevation = _TRACKBALL_DEGREES_PER_EXTENT / height * float(delta_y) * motion_factor
    return azimuth, elevation


def orbit_camera_about_point(
    camera: Any,
    center: Sequence[float],
    *,
    azimuth: float,
    elevation: float,
) -> bool:
    """Rigidly orbit a VTK camera about ``center``.

    Azimuth turns about the view-up axis and elevation about the camera-right
    axis, like ``vtkCamera.Azimuth``/``Elevation``, but both axes pass through
    ``center`` instead of the focal point. Position, focal point, and view-up
    rotate together, so ``center`` keeps its view-space coordinates and stays
    under the cursor for the whole drag.
    """
    try:
        position = _vector(camera.GetPosition())
        focal_point = _vector(camera.GetFocalPoint())
        view_up = _vector(camera.GetViewUp())
        pivot = _vector(center)
    except (AttributeError, TypeError, ValueError):
        return False

    up_axis = _normalized(view_up)
    if up_axis is not None and azimuth:
        position = _rotate_point(position, pivot, up_axis, azimuth)
        focal_point = _rotate_point(focal_point, pivot, up_axis, azimuth)

    # vtkCamera::Elevation rotates about the negated first row of the view
    # transform, i.e. -(view_up x (position - focal_point)).
    right_axis = _normalized(_cross(view_up, _subtract(position, focal_point)))
    if right_axis is not None and elevation:
        axis = _scale(right_axis, -1.0)
        position = _rotate_point(position, pivot, axis, elevation)
        focal_point = _rotate_point(focal_point, pivot, axis, elevation)
        view_up = _rotate_vector(view_up, axis, elevation)

    if up_axis is None and right_axis is None:
        return False
    camera.SetPosition(*position)
    camera.SetFocalPoint(*focal_point)
    camera.SetViewUp(*view_up)
    orthogonalize = getattr(camera, "OrthogonalizeViewUp", None)
    if callable(orthogonalize):
        orthogonalize()
    return True


def depth_pick_world_point(renderer: Any, x: int, y: int) -> Vector | None:
    """Return the rendered surface point at display ``(x, y)``, or None over background.

    Reads one depth-buffer pixel, so it costs the same for any mesh size and
    honors whatever is actually drawn (clipping, visibility, isolate, LOD).
    """
    get_z = getattr(renderer, "GetZ", None)
    if not callable(get_z):
        return None
    try:
        depth = float(get_z(int(x), int(y)))
    except (TypeError, ValueError, RuntimeError):
        return None
    # A cleared depth buffer reads 1.0 wherever nothing was drawn.
    if not math.isfinite(depth) or not 0.0 <= depth < 1.0:
        return None
    try:
        renderer.SetDisplayPoint(float(x), float(y), depth)
        renderer.DisplayToWorld()
        world = renderer.GetWorldPoint()
    except (AttributeError, TypeError, RuntimeError):
        return None
    return _homogeneous_point(world)


def visible_bounds_center(renderer: Any) -> Vector | None:
    """Return the center of the props ``reset_camera`` would frame, if any are visible."""
    compute = getattr(renderer, "ComputeVisiblePropBounds", None)
    if not callable(compute):
        return None
    try:
        bounds = [float(value) for value in compute()]
    except (TypeError, ValueError, RuntimeError):
        return None
    if len(bounds) != 6 or not all(math.isfinite(value) for value in bounds):
        return None
    # VTK reports uninitialized bounds (nothing visible) as min > max.
    if any(bounds[index] > bounds[index + 1] for index in (0, 2, 4)):
        return None
    return (
        0.5 * (bounds[0] + bounds[1]),
        0.5 * (bounds[2] + bounds[3]),
        0.5 * (bounds[4] + bounds[5]),
    )


def world_to_display_point(renderer: Any, point: Sequence[float]) -> tuple[float, float] | None:
    """Project a world point to display pixels, or None when it is outside the depth range."""
    try:
        world = _vector(point)
        renderer.SetWorldPoint(*world, 1.0)
        renderer.WorldToDisplay()
        display_x, display_y, display_z = (float(value) for value in renderer.GetDisplayPoint()[:3])
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None
    if not all(math.isfinite(value) for value in (display_x, display_y, display_z)):
        return None
    if not 0.0 <= display_z <= 1.0:
        return None
    return display_x, display_y


def create_pivot_marker_actor(
    display_point: Sequence[float],
    radius: float,
    outline: float,
) -> Any:
    """Build a screen-space pivot dot: a highlight-yellow disc with a dark outline.

    A 2D actor is never hidden by geometry (the model-center fallback lies
    inside solids) and never needs to move: orbiting keeps the pivot's screen
    position fixed.
    """
    from vtkmodules.vtkCommonCore import vtkPoints, vtkUnsignedCharArray
    from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
    from vtkmodules.vtkRenderingCore import vtkActor2D, vtkPolyDataMapper2D

    points = vtkPoints()
    polygons = vtkCellArray()
    colors = vtkUnsignedCharArray()
    colors.SetNumberOfComponents(3)
    # 2D mappers draw cells in order, so the fill disc paints over the outline disc.
    for disc_radius, color in ((radius + outline, _MARKER_OUTLINE_RGB), (radius, _MARKER_FILL_RGB)):
        polygons.InsertNextCell(_MARKER_SIDES)
        for index in range(_MARKER_SIDES):
            angle = 2.0 * math.pi * index / _MARKER_SIDES
            polygons.InsertCellPoint(
                points.InsertNextPoint(disc_radius * math.cos(angle), disc_radius * math.sin(angle), 0.0)
            )
        colors.InsertNextTuple3(*color)
    polydata = vtkPolyData()
    polydata.SetPoints(points)
    polydata.SetPolys(polygons)
    polydata.GetCellData().SetScalars(colors)

    mapper = vtkPolyDataMapper2D()
    mapper.SetInputData(polydata)
    mapper.SetScalarModeToUseCellData()
    mapper.SetColorModeToDirectScalars()
    actor = vtkActor2D()
    actor.SetMapper(mapper)
    actor.GetPositionCoordinate().SetCoordinateSystemToDisplay()
    actor.SetPosition(float(display_point[0]), float(display_point[1]))
    actor.PickableOff()
    return actor


def _vector(value: Sequence[float]) -> Vector:
    x_value, y_value, z_value = (float(component) for component in tuple(value)[:3])
    return x_value, y_value, z_value


def _homogeneous_point(value: Sequence[float]) -> Vector | None:
    try:
        x_value, y_value, z_value, weight = (float(component) for component in tuple(value)[:4])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(weight) or abs(weight) <= 1e-12:
        return None
    point = (x_value / weight, y_value / weight, z_value / weight)
    return point if all(math.isfinite(component) for component in point) else None


def _subtract(left: Vector, right: Vector) -> Vector:
    return left[0] - right[0], left[1] - right[1], left[2] - right[2]


def _add(left: Vector, right: Vector) -> Vector:
    return left[0] + right[0], left[1] + right[1], left[2] + right[2]


def _scale(value: Vector, factor: float) -> Vector:
    return value[0] * factor, value[1] * factor, value[2] * factor


def _dot(left: Vector, right: Vector) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _cross(left: Vector, right: Vector) -> Vector:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _normalized(value: Vector) -> Vector | None:
    length = math.sqrt(_dot(value, value))
    if not math.isfinite(length) or length <= 1e-12:
        return None
    return _scale(value, 1.0 / length)


def _rotate_vector(value: Vector, unit_axis: Vector, degrees: float) -> Vector:
    """Rodrigues rotation, right-handed like ``vtkTransform.RotateWXYZ``."""
    angle = math.radians(degrees)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return _add(
        _add(_scale(value, cosine), _scale(_cross(unit_axis, value), sine)),
        _scale(unit_axis, _dot(unit_axis, value) * (1.0 - cosine)),
    )


def _rotate_point(point: Vector, center: Vector, unit_axis: Vector, degrees: float) -> Vector:
    return _add(center, _rotate_vector(_subtract(point, center), unit_axis, degrees))


__all__ = [
    "DEFAULT_TRACKBALL_MOTION_FACTOR",
    "create_pivot_marker_actor",
    "depth_pick_world_point",
    "orbit_camera_about_point",
    "trackball_orbit_angles",
    "visible_bounds_center",
    "world_to_display_point",
]
