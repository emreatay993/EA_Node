from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Force a deterministic non-interactive platform plugin for headless runs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QMarginsF, QObject, QRectF, Qt, QUrl, pyqtProperty, pyqtSlot
from PyQt6.QtGui import QColor, QImage, QPainter, QPageLayout, QPageSize, QPdfWriter
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtQuick import QQuickItem, QQuickWindow, QSGRendererInterface
from PyQt6.QtWidgets import QApplication

from ea_node_editor.app_preferences import normalize_graphics_performance_mode
from ea_node_editor.graph.model import EdgeInstance, GraphModel, NodeInstance, ProjectData, ViewState, WorkspaceData
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui.media_preview_provider import LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider
from ea_node_editor.ui.pdf_preview_provider import (
    LOCAL_PDF_PREVIEW_PROVIDER_ID,
    LocalPdfPreviewImageProvider,
    describe_pdf_preview,
)
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

_DEFAULT_BENCHMARK_SCENARIO = "synthetic_exec"
_BENCHMARK_SCENARIOS = (_DEFAULT_BENCHMARK_SCENARIO, "heavy_media")
_TARGETED_PROFILING_PHASES = ("pan", "zoom")
_TARGETED_TIMING_SUFFIXES = (
    "edge_snapshot_build_ms",
    "grid_paint_ms",
)
_TARGETED_COUNT_SUFFIXES = (
    "visible_node_card_count",
    "active_node_surface_count",
    "visible_edge_label_count",
    "visible_edge_count",
)


@dataclass(slots=True, frozen=True)
class SyntheticGraphConfig:
    node_count: int = 1000
    edge_count: int = 5000
    seed: int = 1337


@dataclass(slots=True, frozen=True)
class BenchmarkConfig:
    synthetic_graph: SyntheticGraphConfig = SyntheticGraphConfig()
    load_iterations: int = 5
    interaction_samples: int = 200
    interaction_zoom_min: float = 0.5
    interaction_zoom_max: float = 2.0
    performance_mode: str = "full_fidelity"
    scenario: str = _DEFAULT_BENCHMARK_SCENARIO
    interaction_warmup_samples: int = 3


@dataclass(slots=True, frozen=True)
class _MeasuredInteractionStep:
    elapsed_ms: float
    profiling_snapshot: dict[str, float]


@dataclass(slots=True)
class _ScenarioProject:
    project: ProjectData
    scenario_details: dict[str, Any]
    temp_dir: tempfile.TemporaryDirectory[str] | None = None

    def close(self) -> None:
        if self.temp_dir is not None:
            self.temp_dir.cleanup()
            self.temp_dir = None

    def __enter__(self) -> "_ScenarioProject":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
        self.close()


@dataclass(slots=True, frozen=True)
class _InteractionBenchmarkSamples:
    setup_ms: list[float]
    warmup_ms: list[float]
    pan_ms: list[float]
    zoom_ms: list[float]
    node_drag_control_ms: list[float]
    targeted_profiling_samples: dict[str, list[float]]
    warmup_samples: int
    performance_mode: str
    resolved_performance_mode: str
    scenario: str
    media_surface_count: int

    def combined_ms(self) -> list[float]:
        return [pan + zoom for pan, zoom in zip(self.pan_ms, self.zoom_ms, strict=True)]

    def phase_timings_payload(self) -> dict[str, Any]:
        return {
            "canvas_setup_ms": {
                "samples": self.setup_ms,
                "summary": _metric_summary_ms(self.setup_ms),
            },
            "canvas_warmup_ms": {
                "samples": self.warmup_ms,
                "summary": _metric_summary_ms(self.warmup_ms),
            },
            "pan_interaction_ms": {
                "samples": self.pan_ms,
                "summary": _metric_summary_ms(self.pan_ms),
            },
            "zoom_interaction_ms": {
                "samples": self.zoom_ms,
                "summary": _metric_summary_ms(self.zoom_ms),
            },
            "node_drag_control_ms": {
                "samples": self.node_drag_control_ms,
                "summary": _metric_summary_ms(self.node_drag_control_ms),
            },
            **_targeted_profiling_payload(
                self.targeted_profiling_samples,
                suffixes=_TARGETED_TIMING_SUFFIXES,
            ),
        }

    def targeted_profiling_counts_payload(self) -> dict[str, Any]:
        return _targeted_profiling_payload(
            self.targeted_profiling_samples,
            suffixes=_TARGETED_COUNT_SUFFIXES,
        )

    def benchmark_payload(self) -> dict[str, Any]:
        return {
            "kind": "graph_canvas_qml",
            "render_path": _graph_canvas_qml_path().relative_to(_repo_root_path()).as_posix(),
            "viewport": {
                "width": _CANVAS_BENCHMARK_WIDTH,
                "height": _CANVAS_BENCHMARK_HEIGHT,
            },
            "theme_id": _CANVAS_THEME_ID,
            "graph_theme_id": _CANVAS_GRAPH_THEME_ID,
            "measurement_driver": (
                "Single warmed GraphCanvas host using begin/note/finish viewport interaction + "
                "ViewportBridge.centerOn/set_zoom and GraphNodeHost.dragOffsetChanged with "
                "QQuickWindow.grabWindow()"
            ),
            "uses_actual_canvas_render_path": True,
            "steady_state_canvas_host_reused": True,
            "warmup_samples": self.warmup_samples,
            "performance_mode": self.performance_mode,
            "resolved_graphics_performance_mode": self.resolved_performance_mode,
            "scenario": self.scenario,
            "media_surface_count": self.media_surface_count,
        }

    def to_payload(self) -> dict[str, Any]:
        return {
            "setup_ms": self.setup_ms,
            "warmup_ms": self.warmup_ms,
            "pan_ms": self.pan_ms,
            "zoom_ms": self.zoom_ms,
            "combined_ms": self.combined_ms(),
            "node_drag_control_ms": self.node_drag_control_ms,
            "phase_timings_ms": self.phase_timings_payload(),
            "profiling_counts": self.targeted_profiling_counts_payload(),
            "benchmark": self.benchmark_payload(),
        }


_BASELINE_VARIANCE_THRESHOLDS = {
    "load_p95_ms": {
        "max_cv": 0.25,
        "max_range_ms": 500.0,
    },
    "pan_p95_ms": {
        "max_cv": 0.20,
        "max_range_ms": 8.0,
    },
    "zoom_p95_ms": {
        "max_cv": 0.20,
        "max_range_ms": 8.0,
    },
    "pan_zoom_p95_ms": {
        "max_cv": 0.20,
        "max_range_ms": 8.0,
    },
    "node_drag_control_p95_ms": {
        "max_cv": 0.20,
        "max_range_ms": 8.0,
    },
}

_CANVAS_BENCHMARK_WIDTH = 1280
_CANVAS_BENCHMARK_HEIGHT = 720
_CANVAS_THEME_ID = "stitch_dark"
_CANVAS_GRAPH_THEME_ID = "graph_stitch_dark"
_PASSIVE_MEDIA_TYPE_PREFIX = "passive.media."


def _configure_qtquick_backend() -> None:
    force_value = os.environ.get("EA_NODE_EDITOR_FORCE_SOFTWARE_QML", "").strip().lower()
    force_env = force_value in {"1", "true", "yes", "on"}
    platform_name = os.environ.get("QT_QPA_PLATFORM", "").strip().lower()
    if not (force_env or platform_name in {"offscreen", "minimal"}):
        return
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QSG_RHI_BACKEND", "software")
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)


_configure_qtquick_backend()


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (percentile / 100.0)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    fraction = rank - lower_index
    return float(lower_value + (upper_value - lower_value) * fraction)


def _metric_summary_ms(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "p50": 0.0, "p95": 0.0}
    return {
        "min": float(min(samples)),
        "max": float(max(samples)),
        "mean": float(statistics.fmean(samples)),
        "p50": _percentile(samples, 50.0),
        "p95": _percentile(samples, 95.0),
    }


def _targeted_profiling_metric_key(phase: str, suffix: str) -> str:
    return f"{phase}_{suffix}"


def _targeted_profiling_payload(
    samples_by_metric: dict[str, list[float]],
    *,
    suffixes: tuple[str, ...],
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for phase in _TARGETED_PROFILING_PHASES:
        for suffix in suffixes:
            metric_key = _targeted_profiling_metric_key(phase, suffix)
            metric_samples = [float(value) for value in samples_by_metric.get(metric_key, [])]
            payload[metric_key] = {
                "samples": metric_samples,
                "summary": _metric_summary_ms(metric_samples),
            }
    return payload


def _initialize_targeted_profiling_samples() -> dict[str, list[float]]:
    metric_keys = tuple(
        _targeted_profiling_metric_key(phase, suffix)
        for phase in _TARGETED_PROFILING_PHASES
        for suffix in (*_TARGETED_TIMING_SUFFIXES, *_TARGETED_COUNT_SUFFIXES)
    )
    return {metric_key: [] for metric_key in metric_keys}


def _append_targeted_profiling_sample(
    targeted_samples: dict[str, list[float]],
    *,
    phase: str,
    snapshot: dict[str, float],
) -> None:
    for suffix, value in snapshot.items():
        metric_key = _targeted_profiling_metric_key(phase, suffix)
        if metric_key not in targeted_samples:
            targeted_samples[metric_key] = []
        targeted_samples[metric_key].append(float(value))


def _coefficient_of_variation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0.0:
        return 0.0
    return float(statistics.pstdev(values) / mean)


def _series_variance_eval(values: list[float], threshold: dict[str, float], *, enough_runs: bool) -> dict[str, Any]:
    cv = _coefficient_of_variation(values)
    value_range = max(values) - min(values) if values else 0.0
    passed = (cv <= threshold["max_cv"] and value_range <= threshold["max_range_ms"]) if enough_runs else True
    return {
        "pass": passed,
        "cv": cv,
        "range_ms": value_range,
        "requires_min_runs": 2,
        "details": (
            f"cv={cv:.4f} (<= {threshold['max_cv']:.2f}), "
            f"range={value_range:.3f} ms (<= {threshold['max_range_ms']:.1f} ms)"
        ),
    }


def _resolve_baseline_mode(requested_mode: str, qt_qpa_platform: str) -> str:
    mode = requested_mode.strip().lower()
    if mode in {"interactive", "offscreen"}:
        return mode
    if mode != "auto":
        return "offscreen"
    normalized_platform = qt_qpa_platform.strip().lower()
    if normalized_platform in {"", "offscreen"}:
        return "offscreen"
    return "interactive"


def _normalize_benchmark_scenario(value: Any, default: str = _DEFAULT_BENCHMARK_SCENARIO) -> str:
    normalized = str(value).strip().lower()
    if normalized in _BENCHMARK_SCENARIOS:
        return normalized
    resolved_default = str(default).strip().lower()
    if resolved_default in _BENCHMARK_SCENARIOS:
        return resolved_default
    return _DEFAULT_BENCHMARK_SCENARIO


def _collect_environment_snapshot() -> dict[str, Any]:
    uname = platform.uname()
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "qt_qpa_platform": os.environ.get("QT_QPA_PLATFORM", ""),
        "qt_quick_backend": os.environ.get("QT_QUICK_BACKEND", ""),
        "qsg_rhi_backend": os.environ.get("QSG_RHI_BACKEND", ""),
        "cpu_count": os.cpu_count(),
        "hostname": uname.node,
        "system": uname.system,
        "release": uname.release,
        "machine": uname.machine,
        "processor": uname.processor,
    }


class _BenchmarkMainWindowBridge(QObject):
    def __init__(self, *, performance_mode: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._graphics_performance_mode = normalize_graphics_performance_mode(performance_mode)

    @pyqtProperty(bool, constant=True)
    def graphics_minimap_expanded(self) -> bool:
        return True

    @pyqtProperty(bool, constant=True)
    def graphics_show_grid(self) -> bool:
        return True

    @pyqtProperty(bool, constant=True)
    def graphics_show_minimap(self) -> bool:
        return True

    @pyqtProperty(bool, constant=True)
    def graphics_node_shadow(self) -> bool:
        return True

    @pyqtProperty(int, constant=True)
    def graphics_shadow_strength(self) -> int:
        return 70

    @pyqtProperty(int, constant=True)
    def graphics_shadow_softness(self) -> int:
        return 50

    @pyqtProperty(int, constant=True)
    def graphics_shadow_offset(self) -> int:
        return 4

    @pyqtProperty(str, constant=True)
    def graphics_performance_mode(self) -> str:
        return self._graphics_performance_mode

    @pyqtProperty(bool, constant=True)
    def snap_to_grid_enabled(self) -> bool:
        return False

    @pyqtProperty(float, constant=True)
    def snap_grid_size(self) -> float:
        return 20.0

    @pyqtSlot(str, "QVariant", result="QVariantMap")
    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]:
        return describe_pdf_preview(source, page_number)


def generate_synthetic_project(config: SyntheticGraphConfig) -> ProjectData:
    if config.node_count < 3:
        raise ValueError("node_count must be at least 3")
    if config.edge_count < config.node_count - 1:
        raise ValueError("edge_count must be at least node_count - 1 to keep baseline chain connectivity")

    project = ProjectData(project_id="proj_perf_h", name="track_h_perf")
    workspace_id = "ws_perf_h"
    workspace = WorkspaceData(workspace_id=workspace_id, name="Perf Workspace")
    workspace.views["view_perf_h"] = ViewState(
        view_id="view_perf_h",
        name="V1",
        zoom=1.0,
        pan_x=0.0,
        pan_y=0.0,
    )
    workspace.active_view_id = "view_perf_h"

    node_ids: list[str] = []
    max_cols = 40
    spacing_x = 220.0
    spacing_y = 140.0
    for index in range(config.node_count):
        node_id = f"node_{index:04d}"
        node_ids.append(node_id)
        if index == 0:
            type_id = "core.start"
            title = "Start"
        elif index == config.node_count - 1:
            type_id = "core.end"
            title = "End"
        else:
            type_id = "core.logger"
            title = f"Logger {index}"

        col = index % max_cols
        row = index // max_cols
        workspace.nodes[node_id] = NodeInstance(
            node_id=node_id,
            type_id=type_id,
            title=title,
            x=col * spacing_x,
            y=row * spacing_y,
            properties={},
            exposed_ports={},
        )

    edge_connections: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for index in range(config.node_count - 1):
        connection = (node_ids[index], "exec_out", node_ids[index + 1], "exec_in")
        edge_connections.append(connection)
        seen.add(connection)

    source_candidates = node_ids[:-1]
    target_candidates = node_ids[1:]
    generator = random.Random(config.seed)

    while len(edge_connections) < config.edge_count:
        source_id = generator.choice(source_candidates)
        target_id = generator.choice(target_candidates)
        if source_id == target_id:
            continue
        connection = (source_id, "exec_out", target_id, "exec_in")
        if connection in seen:
            continue
        edge_connections.append(connection)
        seen.add(connection)

    for index, (source_id, source_port, target_id, target_port) in enumerate(edge_connections):
        edge_id = f"edge_{index:05d}"
        workspace.edges[edge_id] = EdgeInstance(
            edge_id=edge_id,
            source_node_id=source_id,
            source_port_key=source_port,
            target_node_id=target_id,
            target_port_key=target_port,
        )

    project.workspaces[workspace_id] = workspace
    project.active_workspace_id = workspace_id
    project.metadata["workspace_order"] = [workspace_id]
    return project


def _minimum_exec_nodes_for_edge_count(edge_count: int) -> int:
    required = 3
    while required * (required - 1) < edge_count:
        required += 1
    return required


def _write_fixture_image(
    path: Path,
    *,
    width: int,
    height: int,
    fill: str,
    accent: str,
    label: str,
) -> None:
    image = QImage(max(1, width), max(1, height), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(fill))

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.fillRect(0, 0, image.width(), image.height(), QColor(fill))
    painter.fillRect(0, int(image.height() * 0.74), image.width(), int(image.height() * 0.26), QColor(accent))
    painter.setPen(QColor("#F4F8FC"))
    font = painter.font()
    font.setPixelSize(max(18, int(min(image.width(), image.height()) * 0.08)))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(
        QRectF(32.0, 24.0, float(image.width() - 64), float(image.height() - 48)),
        int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
        label,
    )
    painter.end()

    if not image.save(str(path)):
        raise RuntimeError(f"Failed to save fixture image: {path}")


def _write_fixture_pdf(path: Path, *, page_count: int = 3) -> None:
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QPageLayout.Orientation.Portrait)
    writer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Unit.Millimeter)
    painter = QPainter(writer)
    for page_index in range(page_count):
        if page_index > 0:
            writer.newPage()
        painter.setPen(QColor("#31414F"))
        font = painter.font()
        font.setPixelSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(72.0, 96.0, 420.0, 64.0),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
            f"Heavy Media Benchmark Page {page_index + 1}",
        )
        font.setPixelSize(12)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(
            QRectF(72.0, 176.0, 420.0, 140.0),
            int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
            "Generated local PDF fixture reused across passive media nodes for offscreen benchmark runs.",
        )
    painter.end()


def _create_heavy_media_fixtures(temp_dir: Path) -> dict[str, Any]:
    image_specs = (
        ("briefing-board.png", 800, 450, "#234C6D", "#2F89FF", "Site Briefing"),
        ("wiring-overview.png", 640, 480, "#5A3E2B", "#C98339", "Wiring Overview"),
        ("inspection-capture.png", 720, 540, "#3F4F38", "#5FB174", "Inspection Capture"),
    )
    image_paths: list[Path] = []
    for filename, width, height, fill, accent, label in image_specs:
        image_path = temp_dir / filename
        _write_fixture_image(
            image_path,
            width=width,
            height=height,
            fill=fill,
            accent=accent,
            label=label,
        )
        image_paths.append(image_path)

    pdf_path = temp_dir / "heavy-media-reference.pdf"
    _write_fixture_pdf(pdf_path, page_count=3)

    return {
        "image_paths": image_paths,
        "pdf_path": pdf_path,
        "pdf_page_count": 3,
    }


def _build_node_blueprints(
    *,
    execution_nodes: int,
    image_nodes: int,
    pdf_nodes: int,
    fixtures: dict[str, Any],
) -> list[dict[str, Any]]:
    blueprints: list[dict[str, Any]] = [
        {
            "type_id": "core.start",
            "title": "Start",
            "properties": {},
            "execution": True,
        }
    ]
    execution_titles = [f"Logger {index}" for index in range(1, max(1, execution_nodes - 1))]
    media_blueprints: list[dict[str, Any]] = []
    image_paths: list[Path] = list(fixtures["image_paths"])
    pdf_path = Path(fixtures["pdf_path"])
    pdf_page_count = int(fixtures["pdf_page_count"])

    for index in range(image_nodes):
        image_path = image_paths[index % len(image_paths)]
        fit_mode = ("contain", "cover", "original")[index % 3]
        media_blueprints.append(
            {
                "type_id": "passive.media.image_panel",
                "title": f"Image Panel {index + 1}",
                "properties": {
                    "source_path": str(image_path),
                    "caption": f"Generated image fixture {index + 1}",
                    "fit_mode": fit_mode,
                },
                "execution": False,
            }
        )
    for index in range(pdf_nodes):
        media_blueprints.append(
            {
                "type_id": "passive.media.pdf_panel",
                "title": f"PDF Panel {index + 1}",
                "properties": {
                    "source_path": str(pdf_path),
                    "page_number": (index % pdf_page_count) + 1,
                    "caption": f"Generated PDF fixture page {(index % pdf_page_count) + 1}",
                },
                "execution": False,
            }
        )

    body_exec_blueprints = [
        {
            "type_id": "core.logger",
            "title": title,
            "properties": {},
            "execution": True,
        }
        for title in execution_titles
    ]

    media_index = 0
    exec_index = 0
    while media_index < len(media_blueprints) or exec_index < len(body_exec_blueprints):
        if media_index < len(media_blueprints):
            blueprints.append(media_blueprints[media_index])
            media_index += 1
        if exec_index < len(body_exec_blueprints):
            blueprints.append(body_exec_blueprints[exec_index])
            exec_index += 1
        if media_index < len(media_blueprints) and len(media_blueprints) - media_index > len(body_exec_blueprints) - exec_index:
            blueprints.append(media_blueprints[media_index])
            media_index += 1

    blueprints.append(
        {
            "type_id": "core.end",
            "title": "End",
            "properties": {},
            "execution": True,
        }
    )
    return blueprints


def _build_synthetic_node_blueprints(total_nodes: int) -> list[dict[str, Any]]:
    blueprints: list[dict[str, Any]] = []
    for index in range(total_nodes):
        if index == 0:
            type_id = "core.start"
            title = "Start"
        elif index == total_nodes - 1:
            type_id = "core.end"
            title = "End"
        else:
            type_id = "core.logger"
            title = f"Logger {index}"
        blueprints.append(
            {
                "type_id": type_id,
                "title": title,
                "properties": {},
                "execution": True,
            }
        )
    return blueprints


def _project_from_blueprints(
    *,
    config: SyntheticGraphConfig,
    node_blueprints: list[dict[str, Any]],
    max_cols: int,
    spacing_x: float,
    spacing_y: float,
) -> tuple[ProjectData, list[str]]:
    project = ProjectData(project_id="proj_perf_h", name="track_h_perf")
    workspace_id = "ws_perf_h"
    workspace = WorkspaceData(workspace_id=workspace_id, name="Perf Workspace")
    workspace.views["view_perf_h"] = ViewState(
        view_id="view_perf_h",
        name="V1",
        zoom=1.0,
        pan_x=0.0,
        pan_y=0.0,
    )
    workspace.active_view_id = "view_perf_h"

    execution_node_ids: list[str] = []
    for index, blueprint in enumerate(node_blueprints):
        node_id = f"node_{index:04d}"
        col = index % max_cols
        row = index // max_cols
        workspace.nodes[node_id] = NodeInstance(
            node_id=node_id,
            type_id=str(blueprint["type_id"]),
            title=str(blueprint["title"]),
            x=col * spacing_x,
            y=row * spacing_y,
            properties=dict(blueprint.get("properties", {})),
            exposed_ports={},
        )
        if bool(blueprint.get("execution", False)):
            execution_node_ids.append(node_id)

    edge_connections: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for index in range(len(execution_node_ids) - 1):
        connection = (
            execution_node_ids[index],
            "exec_out",
            execution_node_ids[index + 1],
            "exec_in",
        )
        edge_connections.append(connection)
        seen.add(connection)

    source_candidates = execution_node_ids[:-1]
    target_candidates = execution_node_ids[1:]
    generator = random.Random(config.seed)
    while len(edge_connections) < config.edge_count:
        source_id = generator.choice(source_candidates)
        target_id = generator.choice(target_candidates)
        if source_id == target_id:
            continue
        connection = (source_id, "exec_out", target_id, "exec_in")
        if connection in seen:
            continue
        edge_connections.append(connection)
        seen.add(connection)

    for index, (source_id, source_port, target_id, target_port) in enumerate(edge_connections):
        edge_id = f"edge_{index:05d}"
        workspace.edges[edge_id] = EdgeInstance(
            edge_id=edge_id,
            source_node_id=source_id,
            source_port_key=source_port,
            target_node_id=target_id,
            target_port_key=target_port,
        )

    project.workspaces[workspace_id] = workspace
    project.active_workspace_id = workspace_id
    project.metadata["workspace_order"] = [workspace_id]
    return project, execution_node_ids


def _build_heavy_media_project(config: SyntheticGraphConfig) -> _ScenarioProject:
    if config.node_count < 5:
        raise ValueError("heavy_media scenario requires node_count >= 5")
    app = QApplication.instance() or QApplication([])
    _ = app

    minimum_exec_nodes = _minimum_exec_nodes_for_edge_count(config.edge_count)
    if minimum_exec_nodes > config.node_count - 2:
        raise ValueError(
            "heavy_media scenario requires enough node budget for execution backbone plus image/PDF panels"
        )

    target_media_nodes = min(
        config.node_count - minimum_exec_nodes,
        6,
    )
    target_media_nodes = max(2, target_media_nodes)
    if target_media_nodes >= config.node_count:
        target_media_nodes = config.node_count - minimum_exec_nodes
    if target_media_nodes < 2:
        raise ValueError("heavy_media scenario requires at least one image panel and one PDF panel")

    image_nodes = math.ceil(target_media_nodes / 2)
    pdf_nodes = target_media_nodes - image_nodes
    if pdf_nodes <= 0:
        pdf_nodes = 1
        image_nodes = target_media_nodes - 1
    execution_nodes = config.node_count - target_media_nodes

    temp_dir = tempfile.TemporaryDirectory(prefix="track_h_heavy_media_")
    fixture_dir = Path(temp_dir.name)
    fixtures = _create_heavy_media_fixtures(fixture_dir)
    node_blueprints = _build_node_blueprints(
        execution_nodes=execution_nodes,
        image_nodes=image_nodes,
        pdf_nodes=pdf_nodes,
        fixtures=fixtures,
    )
    project, execution_node_ids = _project_from_blueprints(
        config=config,
        node_blueprints=node_blueprints,
        max_cols=6,
        spacing_x=360.0,
        spacing_y=320.0,
    )

    return _ScenarioProject(
        project=project,
        temp_dir=temp_dir,
        scenario_details={
            "description": (
                "Generated local PNG/PDF fixtures reused across passive media nodes inside the real "
                "GraphCanvas.qml benchmark path."
            ),
            "fixture_strategy": "generated_local_media_reuse",
            "node_mix": {
                "execution_nodes": len(execution_node_ids),
                "image_panel_nodes": image_nodes,
                "pdf_panel_nodes": pdf_nodes,
            },
            "generated_fixture_count": {
                "images": len(fixtures["image_paths"]),
                "pdfs": 1,
            },
            "expected_media_surface_count": image_nodes + pdf_nodes,
        },
    )


def _build_scenario_project(config: BenchmarkConfig) -> _ScenarioProject:
    scenario = _normalize_benchmark_scenario(config.scenario)
    if scenario == "heavy_media":
        return _build_heavy_media_project(config.synthetic_graph)

    project = generate_synthetic_project(config.synthetic_graph)
    return _ScenarioProject(
        project=project,
        scenario_details={
            "description": "Synthetic execution-chain graph using core start/logger/end nodes only.",
            "fixture_strategy": "none",
            "node_mix": {
                "execution_nodes": config.synthetic_graph.node_count,
                "image_panel_nodes": 0,
                "pdf_panel_nodes": 0,
            },
            "generated_fixture_count": {
                "images": 0,
                "pdfs": 0,
            },
            "expected_media_surface_count": 0,
        },
    )


def _graph_canvas_qml_path() -> Path:
    return _package_root_path() / "ui_qml" / "components" / "GraphCanvas.qml"


def _package_root_path() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_root_path() -> Path:
    return _package_root_path().parent


def _qml_component_error_text(component: QQmlComponent) -> str:
    return "\n".join(error.toString() for error in component.errors())


def _iter_quick_item_tree(root: QQuickItem | None) -> list[QQuickItem]:
    if root is None:
        return []
    items: list[QQuickItem] = []
    stack: list[QQuickItem] = [root]
    while stack:
        item = stack.pop()
        items.append(item)
        stack.extend(child for child in item.childItems() if isinstance(child, QQuickItem))
    return items


class _GraphCanvasBenchmarkHost:
    def __init__(
        self,
        *,
        app: QApplication,
        doc: dict[str, Any],
        workspace_id: str,
        performance_mode: str,
    ) -> None:
        self.app = app
        serializer = JsonProjectSerializer(build_default_registry())
        project = serializer.from_document(doc)
        self.model = GraphModel(project)
        self.scene, self.view = _bind_scene_for_workspace(
            app=app,
            model=self.model,
            workspace_id=workspace_id,
        )
        self.view.set_viewport_size(float(_CANVAS_BENCHMARK_WIDTH), float(_CANVAS_BENCHMARK_HEIGHT))

        self.engine = QQmlEngine()
        self.engine.addImageProvider(LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider())
        self.engine.addImageProvider(LOCAL_PDF_PREVIEW_PROVIDER_ID, LocalPdfPreviewImageProvider())
        self.theme_bridge = ThemeBridge(self.engine, theme_id=_CANVAS_THEME_ID)
        self.graph_theme_bridge = GraphThemeBridge(self.engine, theme_id=_CANVAS_GRAPH_THEME_ID)
        self.main_window_bridge = _BenchmarkMainWindowBridge(performance_mode=performance_mode)
        self.canvas_state_bridge = GraphCanvasStateBridge(
            shell_window=self.main_window_bridge,  # type: ignore[arg-type]
            scene_bridge=self.scene,
            view_bridge=self.view,
        )
        self.canvas_command_bridge = GraphCanvasCommandBridge(
            shell_window=self.main_window_bridge,  # type: ignore[arg-type]
            scene_bridge=self.scene,
            view_bridge=self.view,
        )
        root_context = self.engine.rootContext()
        root_context.setContextProperty("themeBridge", self.theme_bridge)
        root_context.setContextProperty("graphThemeBridge", self.graph_theme_bridge)

        qml_path = _graph_canvas_qml_path()
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(qml_path)))
        if self.component.status() != QQmlComponent.Status.Ready:
            raise RuntimeError(f"Failed to load GraphCanvas.qml:\n{_qml_component_error_text(self.component)}")

        self.window = QQuickWindow()
        self.window.resize(_CANVAS_BENCHMARK_WIDTH, _CANVAS_BENCHMARK_HEIGHT)
        initial_properties = {
            "canvasStateBridge": self.canvas_state_bridge,
            "canvasCommandBridge": self.canvas_command_bridge,
            "width": float(_CANVAS_BENCHMARK_WIDTH),
            "height": float(_CANVAS_BENCHMARK_HEIGHT),
        }
        if hasattr(self.component, "createWithInitialProperties"):
            canvas = self.component.createWithInitialProperties(initial_properties)
        else:
            canvas = self.component.create()
            if canvas is not None:
                for key, value in initial_properties.items():
                    canvas.setProperty(key, value)
        if canvas is None:
            raise RuntimeError(
                f"Failed to instantiate GraphCanvas.qml:\n{_qml_component_error_text(self.component)}"
            )
        if not isinstance(canvas, QQuickItem):
            raise TypeError("GraphCanvas.qml did not create a QQuickItem root")
        self.canvas = canvas
        self.canvas.setParentItem(self.window.contentItem())
        self.window.show()
        self.render_frame()

    def resolved_graphics_performance_mode(self) -> str:
        if getattr(self, "canvas", None) is None:
            return ""
        return str(self.canvas.property("resolvedGraphicsPerformanceMode") or "")

    def begin_viewport_interaction(self) -> None:
        if getattr(self, "canvas", None) is None:
            return
        self.canvas.beginViewportInteraction()
        self.app.processEvents()

    def note_viewport_interaction(self) -> None:
        if getattr(self, "canvas", None) is None:
            return
        self.canvas.noteViewportInteraction()
        self.app.processEvents()

    def finish_viewport_interaction(self) -> None:
        if getattr(self, "canvas", None) is None:
            return
        self.canvas.finishViewportInteractionSoon()
        self.app.processEvents()

    def wait_for_viewport_interaction_idle(self, *, timeout_ms: int = 1000) -> None:
        if getattr(self, "canvas", None) is None:
            return
        deadline = time.perf_counter() + (float(timeout_ms) / 1000.0)
        while True:
            self.app.processEvents()
            if not bool(self.canvas.property("interactionActive")):
                self.app.processEvents()
                return
            if time.perf_counter() >= deadline:
                raise RuntimeError("Timed out waiting for GraphCanvas viewport interaction to settle")
            time.sleep(0.005)

    def wait_for_media_surfaces_ready(self, *, expected_count: int, timeout_ms: int = 6000) -> None:
        if expected_count <= 0 or getattr(self, "canvas", None) is None:
            return
        deadline = time.perf_counter() + (float(timeout_ms) / 1000.0)
        while True:
            self.app.processEvents()
            self.window.update()
            self.window.grabWindow()
            media_surfaces = [
                item for item in _iter_quick_item_tree(self.canvas) if str(item.objectName() or "") == "graphNodeMediaSurface"
            ]
            ready_count = sum(str(surface.property("previewState") or "") == "ready" for surface in media_surfaces)
            if len(media_surfaces) >= expected_count and ready_count >= expected_count:
                self.app.processEvents()
                return
            if time.perf_counter() >= deadline:
                states = [str(surface.property("previewState") or "") for surface in media_surfaces]
                raise RuntimeError(
                    "Timed out waiting for heavy-media surfaces to reach ready state "
                    f"(expected={expected_count}, found={len(media_surfaces)}, ready={ready_count}, states={states})"
                )
            time.sleep(0.01)

    def render_frame(self, *, timeout_ms: int = 2000) -> None:
        deadline = time.perf_counter() + (float(timeout_ms) / 1000.0)
        while True:
            self.app.processEvents()
            self.window.update()
            image = self.window.grabWindow()
            if not image.isNull() and image.width() > 0 and image.height() > 0:
                self.app.processEvents()
                return
            if time.perf_counter() >= deadline:
                raise RuntimeError("Timed out waiting for GraphCanvas.qml to render a frame")
            time.sleep(0.005)

    def visible_scene_rect(self) -> QRectF:
        return self.view.visible_scene_rect()

    def node_cards(self) -> list[QQuickItem]:
        if getattr(self, "canvas", None) is None:
            return []
        return [
            item
            for item in _iter_quick_item_tree(self.canvas)
            if str(item.objectName() or "") == "graphNodeCard"
        ]

    def collect_targeted_profiling_snapshot(self) -> dict[str, float]:
        if getattr(self, "canvas", None) is None:
            return {
                "edge_snapshot_build_ms": 0.0,
                "grid_paint_ms": 0.0,
                "visible_node_card_count": 0.0,
                "active_node_surface_count": 0.0,
                "visible_edge_label_count": 0.0,
                "visible_edge_count": 0.0,
            }

        visible_rect = self.visible_scene_rect()
        items = _iter_quick_item_tree(self.canvas)
        background_layer: QQuickItem | None = None
        edge_layer: QQuickItem | None = None
        visible_node_card_count = 0
        active_node_surface_count = 0
        visible_edge_label_count = 0

        for item in items:
            object_name = str(item.objectName() or "")
            if object_name == "graphCanvasBackground":
                background_layer = item
                continue
            if object_name == "graphCanvasEdgeLayer":
                edge_layer = item
                continue
            if object_name == "graphEdgeFlowLabelItem":
                if bool(item.property("visible")):
                    visible_edge_label_count += 1
                continue

            if object_name not in {"graphNodeCard", "graphNodeSurfaceLoader"}:
                continue

            node_data = item.property("nodeData") or {}
            node_rect = _node_payload_scene_rect(
                node_data,
                fallback_width=item.width(),
                fallback_height=item.height(),
            )
            if not visible_rect.intersects(node_rect):
                continue

            if object_name == "graphNodeCard":
                visible_node_card_count += 1
                continue

            if bool(item.property("renderActive")) and bool(item.property("surfaceLoaded")):
                active_node_surface_count += 1

        edge_snapshot_build_ms = 0.0
        visible_edge_count = 0.0
        if edge_layer is not None:
            edge_snapshot_build_ms = float(edge_layer.property("profileLastSnapshotBuildMs") or 0.0)
            visible_edge_count = float(edge_layer.property("profileLastVisibleEdgeCount") or 0.0)

        grid_paint_ms = 0.0
        if background_layer is not None:
            grid_paint_ms = float(background_layer.property("profileLastGridPaintMs") or 0.0)

        return {
            "edge_snapshot_build_ms": edge_snapshot_build_ms,
            "grid_paint_ms": grid_paint_ms,
            "visible_node_card_count": float(visible_node_card_count),
            "active_node_surface_count": float(active_node_surface_count),
            "visible_edge_label_count": float(visible_edge_label_count),
            "visible_edge_count": visible_edge_count,
        }

    def media_node_scene_rect(self) -> QRectF:
        media_scene_rect = QRectF()
        found_media = False
        for node_card in self.node_cards():
            node_data = node_card.property("nodeData") or {}
            if not _node_payload_is_media(node_data):
                continue
            node_rect = _node_payload_scene_rect(
                node_data,
                fallback_width=node_card.width(),
                fallback_height=node_card.height(),
            )
            media_scene_rect = node_rect if not found_media else media_scene_rect.united(node_rect)
            found_media = True
        return media_scene_rect if found_media else QRectF()

    def frame_scene_rect(self, scene_rect: QRectF) -> bool:
        normalized = QRectF(scene_rect).normalized()
        if not normalized.isValid() or normalized.isEmpty():
            return False
        framed = bool(self.view.frame_scene_rect(normalized))
        self.app.processEvents()
        self.render_frame()
        return framed

    def prepare_media_ready_view(self) -> bool:
        media_scene_rect = self.media_node_scene_rect()
        if self.frame_scene_rect(media_scene_rect):
            return True
        workspace = self.model.project.workspaces[self.model.project.active_workspace_id]
        left, right, top, bottom = _workspace_bounds(workspace)
        return self.frame_scene_rect(QRectF(left, top, right - left, bottom - top))

    def control_node_card(self) -> QQuickItem:
        fallback: QQuickItem | None = None
        visible_rect = self.visible_scene_rect()
        for node_card in self.node_cards():
            if fallback is None:
                fallback = node_card
            node_data = node_card.property("nodeData") or {}
            node_x = float(node_data.get("x", 0.0))
            node_y = float(node_data.get("y", 0.0))
            node_width = max(1.0, float(node_data.get("width", node_card.width())))
            node_height = max(1.0, float(node_data.get("height", node_card.height())))
            if visible_rect.intersects(QRectF(node_x, node_y, node_width, node_height)):
                return node_card
        if fallback is None:
            raise RuntimeError("Failed to locate a graphNodeCard for node-drag control sampling")
        return fallback

    def close(self) -> None:
        if getattr(self, "canvas", None) is not None:
            self.canvas.setParentItem(None)
            self.canvas.deleteLater()
            self.canvas = None
        if getattr(self, "window", None) is not None:
            self.window.close()
            self.window.deleteLater()
            self.window = None
        if getattr(self, "scene", None) is not None:
            self.scene.deleteLater()
            self.scene = None
        if getattr(self, "view", None) is not None:
            self.view.deleteLater()
            self.view = None
        if getattr(self, "engine", None) is not None:
            self.engine.deleteLater()
            self.engine = None
        if getattr(self, "main_window_bridge", None) is not None:
            self.main_window_bridge.deleteLater()
            self.main_window_bridge = None
        self.app.processEvents()

    def __enter__(self) -> "_GraphCanvasBenchmarkHost":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:  # noqa: ANN001
        self.close()


def _bind_scene_for_workspace(
    *,
    app: QApplication,
    model: GraphModel,
    workspace_id: str,
) -> tuple[GraphSceneBridge, ViewportBridge]:
    registry = build_default_registry()
    scene = GraphSceneBridge()
    view = ViewportBridge()
    view.set_viewport_size(1280.0, 720.0)
    scene.set_workspace(model, registry, workspace_id)
    app.processEvents()
    return scene, view


def _workspace_bounds(workspace: WorkspaceData) -> tuple[float, float, float, float]:
    if not workspace.nodes:
        return -5000.0, 5000.0, -5000.0, 5000.0
    xs = [float(node.x) for node in workspace.nodes.values()]
    ys = [float(node.y) for node in workspace.nodes.values()]
    margin_x = 800.0
    margin_y = 500.0
    return (
        min(xs) - margin_x,
        max(xs) + margin_x,
        min(ys) - margin_y,
        max(ys) + margin_y,
    )


def _node_payload_is_media(node_payload: Any) -> bool:
    if not isinstance(node_payload, dict):
        return False
    surface_family = str(node_payload.get("surface_family", "")).strip().lower()
    if surface_family == "media":
        return True
    type_id = str(node_payload.get("type_id", "")).strip().lower()
    return type_id.startswith(_PASSIVE_MEDIA_TYPE_PREFIX)


def _node_payload_scene_rect(node_payload: Any, *, fallback_width: float, fallback_height: float) -> QRectF:
    payload = node_payload if isinstance(node_payload, dict) else {}
    node_x = float(payload.get("x", 0.0))
    node_y = float(payload.get("y", 0.0))
    node_width = max(1.0, float(payload.get("width", fallback_width)))
    node_height = max(1.0, float(payload.get("height", fallback_height)))
    return QRectF(node_x, node_y, node_width, node_height)


def benchmark_load_times_ms(*, doc: dict[str, Any], workspace_id: str, iterations: int) -> list[float]:
    app = QApplication.instance() or QApplication([])
    serializer = JsonProjectSerializer(build_default_registry())
    samples: list[float] = []

    for _ in range(iterations):
        started = time.perf_counter()
        project = serializer.from_document(doc)
        model = GraphModel(project)
        scene, view = _bind_scene_for_workspace(app=app, model=model, workspace_id=workspace_id)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        samples.append(elapsed_ms)
        view.deleteLater()
        scene.deleteLater()
        app.processEvents()

    return samples


def _pan_zoom_target(
    *,
    current_center_x: float,
    current_center_y: float,
    current_zoom: float,
    left: float,
    right: float,
    top: float,
    bottom: float,
    random_gen: random.Random,
    index: int,
    zoom_min: float,
    zoom_max: float,
) -> tuple[float, float, float]:
    pan_x = max(
        left,
        min(right, current_center_x + random_gen.uniform(-180.0, 180.0)),
    )
    pan_y = max(
        top,
        min(bottom, current_center_y + random_gen.uniform(-120.0, 120.0)),
    )
    zoom_step = 1.05 if index % 2 == 0 else (1.0 / 1.05)
    zoom = max(zoom_min, min(zoom_max, current_zoom * zoom_step))
    return pan_x, pan_y, zoom


def _measure_pan_zoom_step(
    canvas_host: _GraphCanvasBenchmarkHost,
    *,
    pan_to_x: float,
    pan_to_y: float,
    zoom_to: float,
) -> tuple[_MeasuredInteractionStep, _MeasuredInteractionStep]:
    canvas_host.begin_viewport_interaction()
    started = time.perf_counter()
    canvas_host.view.centerOn(pan_to_x, pan_to_y)
    canvas_host.note_viewport_interaction()
    canvas_host.render_frame()
    pan_elapsed_ms = (time.perf_counter() - started) * 1000.0
    pan_step = _MeasuredInteractionStep(
        elapsed_ms=pan_elapsed_ms,
        profiling_snapshot=canvas_host.collect_targeted_profiling_snapshot(),
    )

    started = time.perf_counter()
    canvas_host.view.set_zoom(zoom_to)
    canvas_host.note_viewport_interaction()
    canvas_host.render_frame()
    zoom_elapsed_ms = (time.perf_counter() - started) * 1000.0
    zoom_step = _MeasuredInteractionStep(
        elapsed_ms=zoom_elapsed_ms,
        profiling_snapshot=canvas_host.collect_targeted_profiling_snapshot(),
    )
    canvas_host.finish_viewport_interaction()
    canvas_host.wait_for_viewport_interaction_idle()
    return pan_step, zoom_step


def _node_drag_delta(sample_index: int) -> tuple[float, float]:
    sequence = (
        (16.0, 10.0),
        (-14.0, 8.0),
        (12.0, -9.0),
        (-18.0, -11.0),
    )
    return sequence[sample_index % len(sequence)]


def _measure_node_drag_control_step(canvas_host: _GraphCanvasBenchmarkHost, *, sample_index: int) -> float:
    node_card = canvas_host.control_node_card()
    node_data = node_card.property("nodeData") or {}
    node_id = str(node_data.get("node_id", "")).strip()
    if not node_id:
        raise RuntimeError("Failed to resolve node id for node-drag control sampling")

    drag_offset_signal = getattr(node_card, "dragOffsetChanged", None)
    drag_canceled_signal = getattr(node_card, "dragCanceled", None)
    if drag_offset_signal is None or drag_canceled_signal is None:
        raise RuntimeError("GraphNodeHost drag signals are unavailable for control sampling")

    delta_x, delta_y = _node_drag_delta(sample_index)
    started = time.perf_counter()
    drag_offset_signal.emit(node_id, delta_x, delta_y)
    canvas_host.app.processEvents()
    canvas_host.render_frame()
    elapsed_ms = (time.perf_counter() - started) * 1000.0

    drag_canceled_signal.emit(node_id)
    canvas_host.app.processEvents()
    canvas_host.render_frame()
    return elapsed_ms


def benchmark_pan_zoom_ms(
    *,
    doc: dict[str, Any],
    workspace_id: str,
    samples: int,
    warmup_samples: int,
    seed: int,
    zoom_min: float,
    zoom_max: float,
    performance_mode: str,
    scenario: str,
    expected_media_surface_count: int = 0,
) -> dict[str, Any]:
    if samples <= 0:
        raise ValueError("samples must be > 0")
    if warmup_samples < 0:
        raise ValueError("warmup_samples must be >= 0")
    app = QApplication.instance() or QApplication([])
    pan_samples_ms: list[float] = []
    zoom_samples_ms: list[float] = []
    node_drag_control_samples_ms: list[float] = []
    setup_samples_ms: list[float] = []
    warmup_phase_samples_ms: list[float] = []
    targeted_profiling_samples = _initialize_targeted_profiling_samples()
    resolved_performance_mode = ""
    random_gen = random.Random(seed)
    left = right = top = bottom = 0.0
    current_center_x = 0.0
    current_center_y = 0.0
    current_zoom = 1.0

    canvas_host: _GraphCanvasBenchmarkHost | None = None
    try:
        setup_started = time.perf_counter()
        canvas_host = _GraphCanvasBenchmarkHost(
            app=app,
            doc=doc,
            workspace_id=workspace_id,
            performance_mode=performance_mode,
        )
        if expected_media_surface_count > 0:
            canvas_host.prepare_media_ready_view()
        canvas_host.wait_for_media_surfaces_ready(expected_count=expected_media_surface_count)
        setup_samples_ms.append((time.perf_counter() - setup_started) * 1000.0)

        workspace = canvas_host.model.project.workspaces[workspace_id]
        left, right, top, bottom = _workspace_bounds(workspace)
        resolved_performance_mode = canvas_host.resolved_graphics_performance_mode()
        current_center_x = float(canvas_host.view.center_x)
        current_center_y = float(canvas_host.view.center_y)
        current_zoom = float(canvas_host.view.zoom)

        for index in range(warmup_samples):
            pan_x, pan_y, zoom = _pan_zoom_target(
                current_center_x=current_center_x,
                current_center_y=current_center_y,
                current_zoom=current_zoom,
                left=left,
                right=right,
                top=top,
                bottom=bottom,
                random_gen=random_gen,
                index=index,
                zoom_min=zoom_min,
                zoom_max=zoom_max,
            )
            started = time.perf_counter()
            _measure_pan_zoom_step(
                canvas_host,
                pan_to_x=pan_x,
                pan_to_y=pan_y,
                zoom_to=zoom,
            )
            _measure_node_drag_control_step(canvas_host, sample_index=index)
            warmup_phase_samples_ms.append((time.perf_counter() - started) * 1000.0)
            current_center_x = pan_x
            current_center_y = pan_y
            current_zoom = zoom

        for index in range(samples):
            node_drag_control_samples_ms.append(
                _measure_node_drag_control_step(canvas_host, sample_index=warmup_samples + index)
            )

        for index in range(samples):
            pan_x, pan_y, zoom = _pan_zoom_target(
                current_center_x=current_center_x,
                current_center_y=current_center_y,
                current_zoom=current_zoom,
                left=left,
                right=right,
                top=top,
                bottom=bottom,
                random_gen=random_gen,
                index=warmup_samples + index,
                zoom_min=zoom_min,
                zoom_max=zoom_max,
            )
            pan_step, zoom_step = _measure_pan_zoom_step(
                canvas_host,
                pan_to_x=pan_x,
                pan_to_y=pan_y,
                zoom_to=zoom,
            )
            pan_samples_ms.append(pan_step.elapsed_ms)
            zoom_samples_ms.append(zoom_step.elapsed_ms)
            _append_targeted_profiling_sample(
                targeted_profiling_samples,
                phase="pan",
                snapshot=pan_step.profiling_snapshot,
            )
            _append_targeted_profiling_sample(
                targeted_profiling_samples,
                phase="zoom",
                snapshot=zoom_step.profiling_snapshot,
            )
            current_center_x = pan_x
            current_center_y = pan_y
            current_zoom = zoom
    finally:
        if canvas_host is not None:
            canvas_host.close()

    return _InteractionBenchmarkSamples(
        setup_ms=setup_samples_ms,
        warmup_ms=warmup_phase_samples_ms,
        pan_ms=pan_samples_ms,
        zoom_ms=zoom_samples_ms,
        node_drag_control_ms=node_drag_control_samples_ms,
        targeted_profiling_samples=targeted_profiling_samples,
        warmup_samples=warmup_samples,
        performance_mode=performance_mode,
        resolved_performance_mode=resolved_performance_mode,
        scenario=scenario,
        media_surface_count=expected_media_surface_count,
    ).to_payload()


def _run_single_benchmark(config: BenchmarkConfig) -> dict[str, Any]:
    app = QApplication.instance() or QApplication([])
    _ = app
    performance_mode = normalize_graphics_performance_mode(config.performance_mode)
    scenario = _normalize_benchmark_scenario(config.scenario)

    with _build_scenario_project(config) as scenario_project:
        project = scenario_project.project
        serializer = JsonProjectSerializer(build_default_registry())
        doc = serializer.to_document(project)
        workspace_id = project.active_workspace_id

        load_samples = benchmark_load_times_ms(
            doc=doc,
            workspace_id=workspace_id,
            iterations=config.load_iterations,
        )
        interaction_samples = benchmark_pan_zoom_ms(
            doc=doc,
            workspace_id=workspace_id,
            samples=config.interaction_samples,
            warmup_samples=config.interaction_warmup_samples,
            seed=config.synthetic_graph.seed,
            zoom_min=config.interaction_zoom_min,
            zoom_max=config.interaction_zoom_max,
            performance_mode=performance_mode,
            scenario=scenario,
            expected_media_surface_count=int(scenario_project.scenario_details["expected_media_surface_count"]),
        )

    pan_summary = _metric_summary_ms(interaction_samples["pan_ms"])
    zoom_summary = _metric_summary_ms(interaction_samples["zoom_ms"])
    combined_summary = _metric_summary_ms(interaction_samples["combined_ms"])
    node_drag_control_summary = _metric_summary_ms(interaction_samples["node_drag_control_ms"])
    load_summary = _metric_summary_ms(load_samples)
    interaction_frame_p95 = max(pan_summary["p95"], zoom_summary["p95"])
    phase_timings_ms = {
        "project_graph_load_ms": {
            "samples": load_samples,
            "summary": load_summary,
        },
        **interaction_samples["phase_timings_ms"],
    }

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": _collect_environment_snapshot(),
        "config": {
            "synthetic_graph": asdict(config.synthetic_graph),
            "load_iterations": config.load_iterations,
            "interaction_samples": config.interaction_samples,
            "interaction_warmup_samples": config.interaction_warmup_samples,
            "interaction_zoom_min": config.interaction_zoom_min,
            "interaction_zoom_max": config.interaction_zoom_max,
            "performance_mode": performance_mode,
            "scenario": scenario,
            "scenario_details": scenario_project.scenario_details,
        },
        "interaction_benchmark": interaction_samples["benchmark"],
        "phase_timings_ms": phase_timings_ms,
        "profiling_counts": interaction_samples["profiling_counts"],
        "metrics": {
            "project_graph_load_ms": {
                "samples": load_samples,
                "summary": load_summary,
            },
            "pan_interaction_ms": {
                "samples": interaction_samples["pan_ms"],
                "summary": pan_summary,
            },
            "zoom_interaction_ms": {
                "samples": interaction_samples["zoom_ms"],
                "summary": zoom_summary,
            },
            "pan_zoom_combined_ms": {
                "samples": interaction_samples["combined_ms"],
                "summary": combined_summary,
            },
            "node_drag_control_ms": {
                "samples": interaction_samples["node_drag_control_ms"],
                "summary": node_drag_control_summary,
            },
        },
        "requirements_eval": {
            "REQ-PERF-001": {
                "pass": config.synthetic_graph.node_count >= 1000 and config.synthetic_graph.edge_count >= 5000,
                "details": f"Generated graph size {config.synthetic_graph.node_count} nodes / {config.synthetic_graph.edge_count} edges",
            },
            "REQ-PERF-002": {
                "pass": interaction_frame_p95 <= 33.0,
                "details": (
                    f"Real GraphCanvas pan p95={pan_summary['p95']:.3f} ms, "
                    f"zoom p95={zoom_summary['p95']:.3f} ms, "
                    f"node-drag control p95={node_drag_control_summary['p95']:.3f} ms "
                    f"(frame p95 target <= 33 ms)"
                ),
            },
            "REQ-PERF-003": {
                "pass": load_summary["p95"] < 3000.0,
                "details": f"Project+graph load p95={load_summary['p95']:.3f} ms (target < 3000 ms)",
            },
        },
        "limitations": [
            "Pan/zoom and node-drag control timings reuse one warmed GraphCanvas.qml host in a QQuickWindow and include QQuickWindow.grabWindow() readback overhead so frame completion is deterministic.",
            "Project+graph load timing still measures serializer/model/bridge setup and does not instantiate GraphCanvas.qml.",
            "Runs use Qt offscreen platform (QT_QPA_PLATFORM=offscreen), so GPU/compositor behavior differs from interactive desktop rendering.",
            "Absolute timings are machine- and load-dependent; compare trends on the same hardware for regressions.",
        ],
    }


def _baseline_series_run(
    run_report: dict[str, Any],
    *,
    run_index: int,
    baseline_mode: str,
    baseline_tag: str,
) -> dict[str, Any]:
    metrics = run_report["metrics"]
    return {
        "run_id": f"run_{run_index:02d}",
        "generated_at_utc": run_report["generated_at_utc"],
        "mode": baseline_mode,
        "tag": baseline_tag,
        "performance_mode": str(run_report["config"]["performance_mode"]),
        "scenario": str(run_report["config"]["scenario"]),
        "environment": run_report["environment"],
        "metrics": {
            "load_p95_ms": float(metrics["project_graph_load_ms"]["summary"]["p95"]),
            "pan_p95_ms": float(metrics["pan_interaction_ms"]["summary"]["p95"]),
            "zoom_p95_ms": float(metrics["zoom_interaction_ms"]["summary"]["p95"]),
            "pan_zoom_p95_ms": float(metrics["pan_zoom_combined_ms"]["summary"]["p95"]),
            "node_drag_control_p95_ms": float(metrics["node_drag_control_ms"]["summary"]["p95"]),
        },
    }


def _baseline_metric_series(series_runs: list[dict[str, Any]]) -> dict[str, list[float]]:
    return {
        "load_p95_ms": [float(run["metrics"]["load_p95_ms"]) for run in series_runs],
        "pan_p95_ms": [float(run["metrics"]["pan_p95_ms"]) for run in series_runs],
        "zoom_p95_ms": [float(run["metrics"]["zoom_p95_ms"]) for run in series_runs],
        "pan_zoom_p95_ms": [float(run["metrics"]["pan_zoom_p95_ms"]) for run in series_runs],
        "node_drag_control_p95_ms": [float(run["metrics"]["node_drag_control_p95_ms"]) for run in series_runs],
    }


def _baseline_variance_eval(metric_series: dict[str, list[float]], *, enough_runs: bool) -> dict[str, Any]:
    return {
        metric_key: _series_variance_eval(
            values,
            _BASELINE_VARIANCE_THRESHOLDS[metric_key],
            enough_runs=enough_runs,
        )
        for metric_key, values in metric_series.items()
    }


def _baseline_series_payload(
    latest_report: dict[str, Any],
    *,
    series_runs: list[dict[str, Any]],
    baseline_runs: int,
    baseline_mode: str,
    baseline_tag: str,
) -> dict[str, Any]:
    metric_series = _baseline_metric_series(series_runs)
    return {
        "mode": baseline_mode,
        "tag": baseline_tag,
        "performance_mode": str(latest_report["config"]["performance_mode"]),
        "scenario": str(latest_report["config"]["scenario"]),
        "run_count": baseline_runs,
        "runs": series_runs,
        "metric_series": metric_series,
        "variance_thresholds": _BASELINE_VARIANCE_THRESHOLDS,
        "variance_eval": _baseline_variance_eval(metric_series, enough_runs=baseline_runs >= 2),
        "triage_policy": [
            "If variance check fails, first rerun 3x on the same machine with no background workloads.",
            "If variance remains high, classify by hardware tier (CPU/GPU/RAM/display) and keep separate baselines.",
            "Investigate regressions only when thresholds fail on at least two consecutive runs in the same hardware tier.",
        ],
        "notes": (
            "Variance checks are informative when run_count >= 2. "
            "Single-run captures still provide point-in-time regression evidence."
        ),
    }


def run_benchmark(
    config: BenchmarkConfig,
    *,
    baseline_runs: int = 1,
    baseline_mode: str = "offscreen",
    baseline_tag: str = "local",
) -> dict[str, Any]:
    if baseline_runs <= 0:
        raise ValueError("baseline_runs must be > 0")

    full_runs: list[dict[str, Any]] = []
    series_runs: list[dict[str, Any]] = []
    qt_qpa_platform = os.environ.get("QT_QPA_PLATFORM", "").strip().lower()
    for run_index in range(1, baseline_runs + 1):
        if baseline_runs > 1 and qt_qpa_platform == "windows":
            run_report = _run_single_benchmark_subprocess(
                config,
                baseline_mode=baseline_mode,
                baseline_tag=baseline_tag,
            )
        else:
            run_report = _run_single_benchmark(config)
        full_runs.append(run_report)
        series_runs.append(
            _baseline_series_run(
                run_report,
                run_index=run_index,
                baseline_mode=baseline_mode,
                baseline_tag=baseline_tag,
            )
        )

    latest_report = dict(full_runs[-1])
    latest_report["baseline_series"] = _baseline_series_payload(
        latest_report,
        series_runs=series_runs,
        baseline_runs=baseline_runs,
        baseline_mode=baseline_mode,
        baseline_tag=baseline_tag,
    )
    return latest_report


def _run_single_benchmark_subprocess(
    config: BenchmarkConfig,
    *,
    baseline_mode: str,
    baseline_tag: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="track_h_baseline_subprocess_") as temp_dir:
        report_dir = Path(temp_dir)
        command = [
            sys.executable,
            "-m",
            "ea_node_editor.telemetry.performance_harness",
            "--nodes",
            str(config.synthetic_graph.node_count),
            "--edges",
            str(config.synthetic_graph.edge_count),
            "--seed",
            str(config.synthetic_graph.seed),
            "--load-iterations",
            str(config.load_iterations),
            "--interaction-samples",
            str(config.interaction_samples),
            "--interaction-warmup-samples",
            str(config.interaction_warmup_samples),
            "--performance-mode",
            str(config.performance_mode),
            "--scenario",
            str(config.scenario),
            "--baseline-runs",
            "1",
            "--baseline-mode",
            str(baseline_mode),
            "--baseline-tag",
            str(baseline_tag),
            "--report-dir",
            str(report_dir),
        ]
        qt_qpa_platform = os.environ.get("QT_QPA_PLATFORM", "").strip()
        if qt_qpa_platform:
            command.extend(["--qt-platform", qt_qpa_platform])
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Benchmark subprocess failed "
                f"(code={completed.returncode})\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        json_path = report_dir / "track_h_benchmark_report.json"
        if not json_path.exists():
            raise RuntimeError(
                "Benchmark subprocess did not produce track_h_benchmark_report.json\n"
                f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return json.loads(json_path.read_text(encoding="utf-8"))


def _write_markdown_report(report: dict[str, Any], path: Path) -> None:
    metrics = report["metrics"]
    load = metrics["project_graph_load_ms"]["summary"]
    pan = metrics["pan_interaction_ms"]["summary"]
    zoom = metrics["zoom_interaction_ms"]["summary"]
    combined = metrics["pan_zoom_combined_ms"]["summary"]
    node_drag_control = metrics["node_drag_control_ms"]["summary"]
    phase_timings = report.get("phase_timings_ms", {})
    profiling_counts = report.get("profiling_counts", {})
    baseline_series = report.get("baseline_series", {})
    interaction_benchmark = report.get("interaction_benchmark", {})

    lines: list[str] = []
    lines.append("# Track H Benchmark Report")
    lines.append("")
    lines.append(f"- Generated (UTC): `{report['generated_at_utc']}`")
    lines.append("- Command:")
    lines.append("  `venv\\Scripts\\python -m ea_node_editor.telemetry.performance_harness`")
    lines.append(f"- Platform: `{report['environment']['platform']}`")
    lines.append(f"- Python: `{report['environment']['python_version']}`")
    lines.append(f"- Qt platform: `{report['environment']['qt_qpa_platform']}`")
    lines.append("")
    lines.append("## Config")
    lines.append("")
    cfg = report["config"]
    graph_cfg = cfg["synthetic_graph"]
    lines.append(f"- Synthetic graph: `{graph_cfg['node_count']}` nodes / `{graph_cfg['edge_count']}` edges")
    lines.append(f"- Seed: `{graph_cfg['seed']}`")
    lines.append(f"- Load iterations: `{cfg['load_iterations']}`")
    lines.append(f"- Warmup samples: `{cfg.get('interaction_warmup_samples', 0)}`")
    lines.append(f"- Pan/zoom samples: `{cfg['interaction_samples']}`")
    lines.append(f"- Performance mode: `{cfg['performance_mode']}`")
    lines.append(f"- Scenario: `{cfg['scenario']}`")
    scenario_details = cfg.get("scenario_details", {})
    node_mix = scenario_details.get("node_mix", {})
    if node_mix:
        lines.append(
            "- Node mix: "
            f"`{node_mix.get('execution_nodes', 0)}` execution / "
            f"`{node_mix.get('image_panel_nodes', 0)}` image panels / "
            f"`{node_mix.get('pdf_panel_nodes', 0)}` PDF panels"
        )
    fixture_counts = scenario_details.get("generated_fixture_count", {})
    if fixture_counts:
        lines.append(
            "- Generated fixtures: "
            f"`{fixture_counts.get('images', 0)}` images / "
            f"`{fixture_counts.get('pdfs', 0)}` PDFs"
        )
    scenario_description = str(scenario_details.get("description", "")).strip()
    if scenario_description:
        lines.append(f"- Scenario detail: {scenario_description}")
    lines.append("")
    if interaction_benchmark:
        viewport = interaction_benchmark.get("viewport", {})
        lines.append("## Interaction Benchmark")
        lines.append("")
        lines.append(f"- Kind: `{interaction_benchmark.get('kind', '')}`")
        lines.append(f"- Render path: `{interaction_benchmark.get('render_path', '')}`")
        lines.append(
            f"- Driver: `{interaction_benchmark.get('measurement_driver', '')}`"
        )
        lines.append(
            f"- Viewport: `{viewport.get('width', 0)}` x `{viewport.get('height', 0)}`"
        )
        lines.append(
            f"- Theme pair: `{interaction_benchmark.get('theme_id', '')}` / `{interaction_benchmark.get('graph_theme_id', '')}`"
        )
        lines.append(f"- Selected performance mode: `{interaction_benchmark.get('performance_mode', '')}`")
        lines.append(
            f"- Resolved canvas mode: `{interaction_benchmark.get('resolved_graphics_performance_mode', '')}`"
        )
        lines.append(f"- Scenario: `{interaction_benchmark.get('scenario', '')}`")
        lines.append(f"- Media surface count: `{interaction_benchmark.get('media_surface_count', 0)}`")
        lines.append(
            f"- Real canvas path: `{bool(interaction_benchmark.get('uses_actual_canvas_render_path', False))}`"
        )
        lines.append(
            f"- Reused steady-state host: `{bool(interaction_benchmark.get('steady_state_canvas_host_reused', False))}`"
        )
        lines.append("")
    if phase_timings:
        lines.append("## Phase Timings (ms)")
        lines.append("")
        lines.append("| Phase | p50 | p95 | Mean | Min | Max | Samples |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for phase_key in (
            "project_graph_load_ms",
            "canvas_setup_ms",
            "canvas_warmup_ms",
            "pan_interaction_ms",
            "zoom_interaction_ms",
            "node_drag_control_ms",
            "pan_edge_snapshot_build_ms",
            "zoom_edge_snapshot_build_ms",
            "pan_grid_paint_ms",
            "zoom_grid_paint_ms",
        ):
            phase_entry = phase_timings.get(phase_key, {})
            summary = phase_entry.get("summary", {})
            phase_samples = phase_entry.get("samples", [])
            lines.append(
                "| "
                f"{phase_key} | "
                f"{float(summary.get('p50', 0.0)):.3f} | "
                f"{float(summary.get('p95', 0.0)):.3f} | "
                f"{float(summary.get('mean', 0.0)):.3f} | "
                f"{float(summary.get('min', 0.0)):.3f} | "
                f"{float(summary.get('max', 0.0)):.3f} | "
                f"{len(phase_samples)} |"
            )
        lines.append("")
    if profiling_counts:
        lines.append("## Targeted Profiling (Counts)")
        lines.append("")
        lines.append("| Metric | p50 | p95 | Mean | Min | Max | Samples |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for metric_key in (
            "pan_visible_node_card_count",
            "zoom_visible_node_card_count",
            "pan_active_node_surface_count",
            "zoom_active_node_surface_count",
            "pan_visible_edge_label_count",
            "zoom_visible_edge_label_count",
            "pan_visible_edge_count",
            "zoom_visible_edge_count",
        ):
            metric_entry = profiling_counts.get(metric_key, {})
            summary = metric_entry.get("summary", {})
            metric_samples = metric_entry.get("samples", [])
            lines.append(
                "| "
                f"{metric_key} | "
                f"{float(summary.get('p50', 0.0)):.3f} | "
                f"{float(summary.get('p95', 0.0)):.3f} | "
                f"{float(summary.get('mean', 0.0)):.3f} | "
                f"{float(summary.get('min', 0.0)):.3f} | "
                f"{float(summary.get('max', 0.0)):.3f} | "
                f"{len(metric_samples)} |"
            )
        lines.append("")
    lines.append("## Metrics (ms)")
    lines.append("")
    lines.append("| Metric | p50 | p95 | Mean | Min | Max |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.append(
        f"| Project + graph load | {load['p50']:.3f} | {load['p95']:.3f} | {load['mean']:.3f} | {load['min']:.3f} | {load['max']:.3f} |"
    )
    lines.append(
        f"| Pan interaction | {pan['p50']:.3f} | {pan['p95']:.3f} | {pan['mean']:.3f} | {pan['min']:.3f} | {pan['max']:.3f} |"
    )
    lines.append(
        f"| Zoom interaction | {zoom['p50']:.3f} | {zoom['p95']:.3f} | {zoom['mean']:.3f} | {zoom['min']:.3f} | {zoom['max']:.3f} |"
    )
    lines.append(
        f"| Pan + zoom (combined) | {combined['p50']:.3f} | {combined['p95']:.3f} | {combined['mean']:.3f} | {combined['min']:.3f} | {combined['max']:.3f} |"
    )
    lines.append(
        f"| Node-drag control | {node_drag_control['p50']:.3f} | {node_drag_control['p95']:.3f} | {node_drag_control['mean']:.3f} | {node_drag_control['min']:.3f} | {node_drag_control['max']:.3f} |"
    )
    lines.append("")
    lines.append("## Requirement Check")
    lines.append("")
    lines.append("| Requirement | Result | Details |")
    lines.append("|---|---|---|")
    for requirement_id, entry in report["requirements_eval"].items():
        result = "PASS" if entry["pass"] else "FAIL"
        lines.append(f"| {requirement_id} | {result} | {entry['details']} |")
    lines.append("")
    if baseline_series:
        lines.append("## Baseline Series")
        lines.append("")
        lines.append(f"- Mode: `{baseline_series.get('mode', 'offscreen')}`")
        lines.append(f"- Tag: `{baseline_series.get('tag', 'local')}`")
        lines.append(f"- Performance mode: `{baseline_series.get('performance_mode', 'full_fidelity')}`")
        lines.append(f"- Scenario: `{baseline_series.get('scenario', _DEFAULT_BENCHMARK_SCENARIO)}`")
        lines.append(f"- Run count: `{baseline_series.get('run_count', 0)}`")
        lines.append("")
        lines.append("| Run | Mode | Load p95 (ms) | Pan p95 (ms) | Zoom p95 (ms) | Pan+Zoom p95 (ms) | Drag p95 (ms) | Qt Platform | Machine |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---|---|")
        for run in baseline_series.get("runs", []):
            env = run.get("environment", {})
            run_metrics = run.get("metrics", {})
            lines.append(
                "| "
                f"{run.get('run_id', '')} | "
                f"{run.get('mode', '')} | "
                f"{float(run_metrics.get('load_p95_ms', 0.0)):.3f} | "
                f"{float(run_metrics.get('pan_p95_ms', 0.0)):.3f} | "
                f"{float(run_metrics.get('zoom_p95_ms', 0.0)):.3f} | "
                f"{float(run_metrics.get('pan_zoom_p95_ms', 0.0)):.3f} | "
                f"{float(run_metrics.get('node_drag_control_p95_ms', 0.0)):.3f} | "
                f"{env.get('qt_qpa_platform', '')} | "
                f"{env.get('machine', '')} |"
            )
        lines.append("")
        lines.append("### Variance Policy")
        lines.append("")
        thresholds = baseline_series.get("variance_thresholds", {})
        variance_eval = baseline_series.get("variance_eval", {})
        lines.append("| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |")
        lines.append("|---|---:|---:|---:|---:|---|")
        for metric_key in (
            "load_p95_ms",
            "pan_p95_ms",
            "zoom_p95_ms",
            "pan_zoom_p95_ms",
            "node_drag_control_p95_ms",
        ):
            threshold = thresholds.get(metric_key, {})
            observed = variance_eval.get(metric_key, {})
            result = "PASS" if observed.get("pass", False) else "FAIL"
            lines.append(
                "| "
                f"{metric_key} | "
                f"{float(threshold.get('max_cv', 0.0)):.2f} | "
                f"{float(threshold.get('max_range_ms', 0.0)):.1f} | "
                f"{float(observed.get('cv', 0.0)):.4f} | "
                f"{float(observed.get('range_ms', 0.0)):.3f} | "
                f"{result} |"
            )
        lines.append("")
        lines.append("### Triage")
        lines.append("")
        for item in baseline_series.get("triage_policy", []):
            lines.append(f"- {item}")
        note = str(baseline_series.get("notes", "")).strip()
        if note:
            lines.append("")
            lines.append(f"- Note: {note}")
        lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track H performance harness for COREX Node Editor.")
    parser.add_argument("--nodes", type=int, default=1000, help="Synthetic node count.")
    parser.add_argument("--edges", type=int, default=5000, help="Synthetic edge count.")
    parser.add_argument("--seed", type=int, default=1337, help="Deterministic random seed.")
    parser.add_argument("--load-iterations", type=int, default=5, help="Project/graph load iterations.")
    parser.add_argument("--interaction-samples", type=int, default=200, help="Pan/zoom sample count.")
    parser.add_argument(
        "--interaction-warmup-samples",
        type=int,
        default=3,
        help="Unmeasured warmup interaction cycles to run on the real canvas host before steady-state sampling.",
    )
    parser.add_argument(
        "--performance-mode",
        choices=("full_fidelity", "max_performance"),
        default="full_fidelity",
        help="Graphics performance mode applied to the benchmark canvas.",
    )
    parser.add_argument(
        "--scenario",
        choices=_BENCHMARK_SCENARIOS,
        default=_DEFAULT_BENCHMARK_SCENARIO,
        help="Benchmark scene composition to load into GraphCanvas.qml.",
    )
    parser.add_argument(
        "--baseline-runs",
        type=int,
        default=1,
        help="Number of repeated baseline runs for variance analysis.",
    )
    parser.add_argument(
        "--baseline-mode",
        choices=("auto", "offscreen", "interactive"),
        default="auto",
        help="Label for run mode; auto resolves from active Qt platform.",
    )
    parser.add_argument(
        "--baseline-tag",
        type=str,
        default="local",
        help="Free-form tag for grouping baseline runs (e.g., pilot_hw_a).",
    )
    parser.add_argument(
        "--qt-platform",
        type=str,
        default="",
        help="Optional override for QT_QPA_PLATFORM before creating QApplication.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("docs/specs/perf"),
        help="Output folder for benchmark reports.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.qt_platform:
        os.environ["QT_QPA_PLATFORM"] = args.qt_platform
    resolved_mode = _resolve_baseline_mode(args.baseline_mode, os.environ.get("QT_QPA_PLATFORM", ""))
    config = BenchmarkConfig(
        synthetic_graph=SyntheticGraphConfig(
            node_count=args.nodes,
            edge_count=args.edges,
            seed=args.seed,
        ),
        load_iterations=args.load_iterations,
        interaction_samples=args.interaction_samples,
        interaction_warmup_samples=args.interaction_warmup_samples,
        performance_mode=args.performance_mode,
        scenario=args.scenario,
    )
    report = run_benchmark(
        config,
        baseline_runs=args.baseline_runs,
        baseline_mode=resolved_mode,
        baseline_tag=args.baseline_tag,
    )

    report_dir: Path = args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "track_h_benchmark_report.json"
    md_path = report_dir / "TRACK_H_BENCHMARK_REPORT.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown_report(report, md_path)

    load = report["metrics"]["project_graph_load_ms"]["summary"]
    pan_zoom = report["metrics"]["pan_zoom_combined_ms"]["summary"]
    node_drag_control = report["metrics"]["node_drag_control_ms"]["summary"]
    baseline = report.get("baseline_series", {})
    print(f"Benchmark report written: {md_path}")
    print(f"Benchmark data written:   {json_path}")
    if baseline:
        print(
            "baseline_mode="
            f"{baseline.get('mode', 'offscreen')} baseline_runs={baseline.get('run_count', 1)}"
        )
    print(f"performance_mode={report['config']['performance_mode']}")
    print(f"scenario={report['config']['scenario']}")
    print(f"load_p50_ms={load['p50']:.3f}")
    print(f"load_p95_ms={load['p95']:.3f}")
    print(f"pan_zoom_p50_ms={pan_zoom['p50']:.3f}")
    print(f"pan_zoom_p95_ms={pan_zoom['p95']:.3f}")
    print(f"node_drag_control_p95_ms={node_drag_control['p95']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
