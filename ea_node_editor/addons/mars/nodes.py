# Purpose: Define guided batch, time-history, and advanced MARS job nodes.
# Map: feature_routes/mars_solver_addon.md
# Tests: tests/test_mars_nodes.py

from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.addons.mars.metadata import MARS_CATEGORY
from ea_node_editor.addons.mars.runtime import publish_mars_artifacts, run_mars_batch
from ea_node_editor.nodes.builtins.integrations_common import (
    pick_optional_path,
    pick_path,
    require_existing_file,
)
from ea_node_editor.nodes.decorators import plugin_descriptor
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import (
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
    PropertyConditionSpec,
    ReadinessRequirementSpec,
)
from ea_node_editor.runtime_contracts.data_tree import resolve_single_run_inputs

MARS_BATCH_SOLVE_NODE_TYPE_ID = "mars.batch_solve"
MARS_TIME_HISTORY_NODE_TYPE_ID = "mars.time_history"
MARS_RUN_JOB_NODE_TYPE_ID = "mars.run_job"

_MARS_ICON = "icons/mars_icon_64.png"
_MARS_INPUT_FILTER = (
    "MARS and Ansys inputs (*.mcf *.pch *.csv *.txt *.rst);;"
    "CSV files (*.csv);;Ansys result files (*.rst);;All files (*)"
)
_MARS_JOB_FILTER = "MARS jobs (*.json);;JSON files (*.json);;All files (*)"
_INPUT_LABELS = {
    "modal_coordinates": "Modal Coordinates",
    "modal_stress": "Modal Stress",
    "modal_deformation": "Modal Deformation",
    "modal_force_moment": "Modal Force / Moment",
    "steady_state_stress": "Steady-State Stress",
    "temperature_field": "Temperature Field",
    "material_profile": "Material Profile",
    "modal_rst": "Modal RST",
}
_INPUT_DESCRIPTIONS = {
    "modal_coordinates": "Path to modal coordinates used to reconstruct physical responses.",
    "modal_stress": "Path to modal stress coefficients for response recovery.",
    "modal_deformation": "Path to modal deformation coefficients for response recovery.",
    "modal_force_moment": "Path to modal force and moment coefficients for response recovery.",
    "steady_state_stress": "Optional path to steady-state stress values added to the modal response.",
    "temperature_field": "Optional path to the temperature field used for material evaluation.",
    "material_profile": "Optional path to temperature-dependent material properties.",
    "modal_rst": "Optional Ansys modal result file used as a guided MARS input.",
}
_PREPARED_INPUT_KEYS = tuple(key for key in _INPUT_LABELS if key != "modal_rst")
_BATCH_OUTPUTS = (
    ("von_mises", "Von Mises", True),
    ("max_principal", "Maximum Principal", False),
    ("min_principal", "Minimum Principal", False),
    ("deformation", "Deformation", False),
    ("velocity", "Velocity", False),
    ("acceleration", "Acceleration", False),
    ("force_moment", "Force / Moment", False),
    ("damage", "Fatigue Damage", False),
)
_TIME_HISTORY_OUTPUTS = tuple(
    key for key, _label, _default in _BATCH_OUTPUTS if key != "damage"
)
_PRIMARY_OUTPUT_PORTS = {
    key: key
    for key in (
        "von_mises",
        "max_principal",
        "min_principal",
        "deformation",
        "velocity",
        "acceleration",
        "damage",
        "force",
        "moment",
    )
}
_PRIMARY_OUTPUT_DESCRIPTIONS = {
    "von_mises": "Managed path to the recovered von Mises stress result.",
    "max_principal": "Managed path to the recovered maximum principal stress result.",
    "min_principal": "Managed path to the recovered minimum principal stress result.",
    "deformation": "Managed path to the recovered deformation result.",
    "velocity": "Managed path to the recovered velocity result.",
    "acceleration": "Managed path to the recovered acceleration result.",
    "damage": "Managed path to the calculated fatigue damage result.",
    "force": "Managed path to the recovered force result.",
    "moment": "Managed path to the recovered moment result.",
}


def _input_ports() -> tuple[PortSpec, ...]:
    return tuple(
        PortSpec(
            key,
            "in",
            "data",
            'COREX.DataTypes.Path',
            label,
            required=key == "modal_coordinates",
            uses_property_default=True,
            data_access="tree",
            description=_INPUT_DESCRIPTIONS[key],
        )
        for key, label in _INPUT_LABELS.items()
    )


def _input_properties() -> tuple[PropertySpec, ...]:
    return tuple(
        PropertySpec(
            key,
            "path",
            "",
            label,
            inline_editor="path" if key == "modal_coordinates" else "",
            inspector_editor="path",
            group="Inputs",
            file_filter=_MARS_INPUT_FILTER,
        )
        for key, label in _INPUT_LABELS.items()
    )


def _execution_properties() -> tuple[PropertySpec, ...]:
    return (
        PropertySpec(
            "timeout_seconds",
            "float",
            3600.0,
            "Timeout (seconds)",
            inspector_editor="text",
            group="Runtime",
        ),
        PropertySpec(
            "termination_grace_seconds",
            "float",
            2.0,
            "Termination Grace (seconds)",
            inspector_editor="text",
            group="Runtime",
        ),
    )


def _common_output_ports() -> tuple[PortSpec, ...]:
    return (
        PortSpec(
            "manifest",
            "out",
            "data",
            'COREX.DataTypes.Path',
            "Result Manifest",
            exposed=True,
            description="Managed path to the MARS result manifest.",
        ),
        PortSpec(
            "files",
            "out",
            "data",
            'COREX.DataTypes.Any',
            "Result Files",
            exposed=True,
            description="Collection of managed result artifacts published by MARS.",
        ),
    )


def _number_property(ctx: ExecutionContext, key: str) -> float:
    value = ctx.properties.get(key)
    if isinstance(value, bool):
        raise ValueError(f"{key} must be a number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a number.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{key} must be a finite number.")
    return number


def _optional_number_property(ctx: ExecutionContext, key: str) -> float | None:
    value = ctx.properties.get(key)
    if value in (None, ""):
        return None
    return _number_property(ctx, key)


def _fatigue_properties() -> tuple[PropertySpec, ...]:
    return (
        PropertySpec("fatigue_A", "str", "", "Fatigue A", group="Fatigue"),
        PropertySpec("fatigue_m", "str", "", "Fatigue m", group="Fatigue"),
    )


def _plasticity_properties() -> tuple[PropertySpec, ...]:
    return (
        PropertySpec(
            "plasticity_enabled",
            "bool",
            False,
            "Enable Plasticity",
            inspector_editor="toggle",
            group="Plasticity",
        ),
        PropertySpec(
            "plasticity_method",
            "enum",
            "neuber",
            "Method",
            enum_values=("neuber", "glinka", "ibg"),
            inspector_editor="enum",
            group="Plasticity",
        ),
        PropertySpec(
            "plasticity_max_iterations",
            "int",
            60,
            "Maximum Iterations",
            group="Plasticity",
        ),
        PropertySpec(
            "plasticity_tolerance",
            "float",
            1e-10,
            "Tolerance",
            group="Plasticity",
        ),
        PropertySpec(
            "plasticity_default_temperature",
            "str",
            "",
            "Default Temperature",
            group="Plasticity",
        ),
        PropertySpec(
            "plasticity_temperature_column",
            "str",
            "",
            "Temperature Column",
            group="Plasticity",
        ),
        PropertySpec(
            "plasticity_poisson_ratio",
            "str",
            "",
            "Poisson Ratio",
            group="Plasticity",
        ),
        PropertySpec(
            "plasticity_extrapolation_mode",
            "enum",
            "linear",
            "Extrapolation",
            enum_values=("linear", "plateau"),
            inspector_editor="enum",
            group="Plasticity",
        ),
    )


def _resolve_guided_inputs(ctx: ExecutionContext, *, node_name: str) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for key in _PREPARED_INPUT_KEYS:
        path = pick_optional_path(ctx, input_key=key, property_key=key)
        if path is None:
            continue
        require_existing_file(path, node_name=f"{node_name} {key}")
        inputs[key] = str(path.resolve())

    rst_path = pick_optional_path(ctx, input_key="modal_rst", property_key="modal_rst")
    if rst_path is not None:
        require_existing_file(rst_path, node_name=f"{node_name} modal_rst")
        scope_name = str(ctx.properties.get("rst_scope_name", "")).strip()
        shell_layer = str(ctx.properties.get("rst_shell_layer", "top")).strip().lower()
        inputs["modal_rst"] = {
            "path": str(rst_path.resolve()),
            "scope_name": scope_name or "All result-support nodes",
            "shell_layer": shell_layer or None,
        }

    return inputs


def _guided_settings(ctx: ExecutionContext, outputs: tuple[str, ...]) -> dict[str, Any]:
    skip_first = ctx.properties.get("skip_first_modes", 0)
    skip_last = ctx.properties.get("skip_last_modes", 0)
    if (
        isinstance(skip_first, bool)
        or not isinstance(skip_first, int)
        or skip_first < 0
    ):
        raise ValueError("Skip First Modes must be a non-negative integer.")
    if isinstance(skip_last, bool) or not isinstance(skip_last, int) or skip_last < 0:
        raise ValueError("Skip Last Modes must be a non-negative integer.")
    settings: dict[str, Any] = {
        "skip_first_modes": skip_first,
        "skip_last_modes": skip_last,
        "include_steady_state": bool(ctx.properties.get("include_steady_state", False)),
    }
    if "damage" in outputs:
        fatigue_A = _optional_number_property(ctx, "fatigue_A")
        fatigue_m = _optional_number_property(ctx, "fatigue_m")
        settings["fatigue"] = {"A": fatigue_A, "m": fatigue_m}
    if bool(ctx.properties.get("plasticity_enabled", False)):
        max_iterations = ctx.properties.get("plasticity_max_iterations", 60)
        if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or max_iterations <= 0:
            raise ValueError("Plasticity Maximum Iterations must be a positive integer.")
        settings["plasticity"] = {
            "enabled": True,
            "method": str(ctx.properties.get("plasticity_method", "neuber")),
            "max_iterations": max_iterations,
            "tolerance": _number_property(ctx, "plasticity_tolerance"),
            "default_temperature": _optional_number_property(
                ctx, "plasticity_default_temperature"
            ),
            "temperature_column": str(
                ctx.properties.get("plasticity_temperature_column", "")
            ).strip()
            or None,
            "poisson_ratio": _optional_number_property(
                ctx, "plasticity_poisson_ratio"
            ),
            "extrapolation_mode": str(
                ctx.properties.get("plasticity_extrapolation_mode", "linear")
            ),
        }
    return settings


def _write_guided_job(
    path: Path,
    *,
    mode: str,
    inputs: Mapping[str, Any],
    outputs: tuple[str, ...],
    settings: Mapping[str, Any],
    output_directory: Path,
    node_id: int | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "mode": mode,
        "inputs": dict(inputs),
        "outputs": list(outputs),
        "settings": dict(settings),
        "output_directory": str(output_directory.resolve()),
    }
    if node_id is not None:
        payload["node_id"] = node_id
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run_and_publish(
    ctx: ExecutionContext,
    *,
    job_path: Path,
    output_directory: Path,
):
    outcome = run_mars_batch(
        ctx,
        job_path=job_path,
        output_directory=output_directory,
        timeout_seconds=_number_property(ctx, "timeout_seconds"),
        termination_grace_seconds=_number_property(ctx, "termination_grace_seconds"),
    )
    published = publish_mars_artifacts(
        ctx,
        output_directory=output_directory,
        outcome=outcome,
        include_results_directory=False,
    )
    return outcome, published


class MarsBatchSolveNodePlugin:
    def spec(self) -> NodeTypeSpec:
        primary_ports = tuple(
            PortSpec(
                port,
                "out",
                "data",
                'COREX.DataTypes.Path',
                port.replace("_", " ").title(),
                exposed=True,
                description=_PRIMARY_OUTPUT_DESCRIPTIONS[port],
            )
            for port in _PRIMARY_OUTPUT_PORTS.values()
        )
        return NodeTypeSpec(
            type_id=MARS_BATCH_SOLVE_NODE_TYPE_ID,
            display_name="MARS Batch Solve",
            category_path=(MARS_CATEGORY,),
            icon=_MARS_ICON,
            description="Builds and runs a MARS all-node envelope job with managed results.",
            keywords=("mars", "batch", "envelope"),
            ports=(
                *_input_ports(),
                *primary_ports,
                *_common_output_ports(),
            ),
            properties=(
                *_input_properties(),
                PropertySpec(
                    "rst_scope_name",
                    "str",
                    "All result-support nodes",
                    "RST Scope Name",
                    inspector_editor="text",
                    group="RST",
                ),
                PropertySpec(
                    "rst_shell_layer",
                    "enum",
                    "top",
                    "RST Shell Layer",
                    enum_values=("top", "bottom", "mid"),
                    inspector_editor="enum",
                    group="RST",
                ),
                *(
                    PropertySpec(
                        f"output_{key}",
                        "bool",
                        default,
                        label,
                        inspector_editor="toggle",
                        group="Results",
                    )
                    for key, label, default in _BATCH_OUTPUTS
                ),
                PropertySpec(
                    "skip_first_modes", "int", 0, "Skip First Modes", group="Modes"
                ),
                PropertySpec(
                    "skip_last_modes", "int", 0, "Skip Last Modes", group="Modes"
                ),
                PropertySpec(
                    "include_steady_state",
                    "bool",
                    False,
                    "Include Steady-State Stress",
                    inspector_editor="toggle",
                    group="Modes",
                ),
                *_fatigue_properties(),
                *_plasticity_properties(),
                *_execution_properties(),
            ),
            readiness_requirements=(
                ReadinessRequirementSpec(
                    any_of_properties=("fatigue_A",),
                    when_properties=(
                        PropertyConditionSpec(
                            property_key="output_damage",
                            values=(True,),
                        ),
                    ),
                ),
                ReadinessRequirementSpec(
                    any_of_properties=("fatigue_m",),
                    when_properties=(
                        PropertyConditionSpec(
                            property_key="output_damage",
                            values=(True,),
                        ),
                    ),
                ),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        ctx.inputs = resolve_single_run_inputs(ctx.inputs, node_name="MARS Batch Solve")
        outputs = tuple(
            key
            for key, _label, _default in _BATCH_OUTPUTS
            if bool(ctx.properties.get(f"output_{key}", False))
        )
        if not outputs:
            raise ValueError("MARS Batch Solve requires at least one selected output.")
        if "force_moment" in outputs and len(outputs) != 1:
            raise ValueError(
                "Force / Moment cannot be combined with other MARS outputs."
            )
        inputs = _resolve_guided_inputs(ctx, node_name="MARS Batch Solve")
        settings = _guided_settings(ctx, outputs)

        with tempfile.TemporaryDirectory(prefix="corex-mars-batch-") as scratch:
            scratch_path = Path(scratch)
            output_directory = scratch_path / "results"
            job_path = scratch_path / "mars_job.json"
            _write_guided_job(
                job_path,
                mode="batch",
                inputs=inputs,
                outputs=outputs,
                settings=settings,
                output_directory=output_directory,
            )
            outcome, published = _run_and_publish(
                ctx,
                job_path=job_path,
                output_directory=output_directory,
            )

        node_outputs: dict[str, Any] = {
            "manifest": published.manifest,
            "files": published.files,
        }
        for primary_key, ref in published.primary_files.items():
            port = _PRIMARY_OUTPUT_PORTS.get(primary_key)
            if port:
                node_outputs[port] = ref
        return NodeResult(outputs=node_outputs, warnings=outcome.warnings)


class MarsTimeHistoryNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id=MARS_TIME_HISTORY_NODE_TYPE_ID,
            display_name="MARS Time History",
            category_path=(MARS_CATEGORY,),
            icon=_MARS_ICON,
            description="Builds and runs one MARS node time-history job and returns its CSV.",
            keywords=("mars", "time history", "response"),
            ports=(
                *_input_ports(),
                PortSpec(
                    "history_csv",
                    "out",
                    "data",
                    'COREX.DataTypes.Path',
                    "Time History CSV",
                    exposed=True,
                    description="Managed CSV containing the recovered response history for the selected node.",
                ),
                *_common_output_ports(),
            ),
            properties=(
                *_input_properties(),
                PropertySpec(
                    "rst_scope_name",
                    "str",
                    "All result-support nodes",
                    "RST Scope Name",
                    inspector_editor="text",
                    group="RST",
                ),
                PropertySpec(
                    "rst_shell_layer",
                    "enum",
                    "top",
                    "RST Shell Layer",
                    enum_values=("top", "bottom", "mid"),
                    inspector_editor="enum",
                    group="RST",
                ),
                PropertySpec(
                    "node_id",
                    "int",
                    1,
                    "Node ID",
                    inline_editor="text",
                    group="Modes",
                ),
                PropertySpec(
                    "output",
                    "enum",
                    "von_mises",
                    "Result",
                    enum_values=_TIME_HISTORY_OUTPUTS,
                    inline_editor="enum",
                    inspector_editor="enum",
                    group="Results",
                ),
                PropertySpec(
                    "skip_first_modes", "int", 0, "Skip First Modes", group="Modes"
                ),
                PropertySpec(
                    "skip_last_modes", "int", 0, "Skip Last Modes", group="Modes"
                ),
                PropertySpec(
                    "include_steady_state",
                    "bool",
                    False,
                    "Include Steady-State Stress",
                    inspector_editor="toggle",
                    group="Modes",
                ),
                *_plasticity_properties(),
                *_execution_properties(),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        ctx.inputs = resolve_single_run_inputs(ctx.inputs, node_name="MARS Time History")
        node_id = ctx.properties.get("node_id")
        if isinstance(node_id, bool) or not isinstance(node_id, int):
            raise ValueError("MARS Time History requires an integer Node ID.")
        output = str(ctx.properties.get("output", "")).strip()
        if output not in _TIME_HISTORY_OUTPUTS:
            raise ValueError(f"Unsupported MARS time-history output: {output!r}.")
        outputs = (output,)
        inputs = _resolve_guided_inputs(ctx, node_name="MARS Time History")
        settings = _guided_settings(ctx, outputs)

        with tempfile.TemporaryDirectory(prefix="corex-mars-history-") as scratch:
            scratch_path = Path(scratch)
            output_directory = scratch_path / "results"
            job_path = scratch_path / "mars_job.json"
            _write_guided_job(
                job_path,
                mode="time_history",
                inputs=inputs,
                outputs=outputs,
                settings=settings,
                output_directory=output_directory,
                node_id=node_id,
            )
            outcome, published = _run_and_publish(
                ctx,
                job_path=job_path,
                output_directory=output_directory,
            )

        history_csv = published.primary_files.get("history_csv")
        if history_csv is None:
            raise RuntimeError("MARSBatch did not identify the time-history CSV.")
        return NodeResult(
            outputs={
                "history_csv": history_csv,
                "manifest": published.manifest,
                "files": published.files,
            },
            warnings=outcome.warnings,
        )


class MarsRunJobNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id=MARS_RUN_JOB_NODE_TYPE_ID,
            display_name="MARS Run Job",
            category_path=(MARS_CATEGORY,),
            icon=_MARS_ICON,
            description=(
                "Runs an existing MARS schema-v1 JSON job while containing all outputs "
                "inside COREX-managed storage."
            ),
            keywords=("mars", "job", "json"),
            ports=(
                PortSpec(
                    "job",
                    "in",
                    "data",
                    'COREX.DataTypes.Path',
                    "MARS Job",
                    required=True,
                    uses_property_default=True,
                    data_access="tree",
                    description="Path to an existing MARS schema-v1 JSON job.",
                ),
                *(
                    PortSpec(
                        port,
                        "out",
                        "data",
                        'COREX.DataTypes.Path',
                        port.replace("_", " ").title(),
                        exposed=True,
                        description=_PRIMARY_OUTPUT_DESCRIPTIONS[port],
                    )
                    for port in _PRIMARY_OUTPUT_PORTS.values()
                ),
                *_common_output_ports(),
            ),
            properties=(
                PropertySpec(
                    "job",
                    "path",
                    "",
                    "MARS Job",
                    inline_editor="path",
                    inspector_editor="path",
                    group="Inputs",
                    file_filter=_MARS_JOB_FILTER,
                ),
                *_execution_properties(),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        ctx.inputs = resolve_single_run_inputs(ctx.inputs, node_name="MARS Run Job")
        job_path = pick_path(
            ctx,
            input_key="job",
            property_key="job",
            node_name="MARS Run Job",
        )
        require_existing_file(job_path, node_name="MARS Run Job")
        with tempfile.TemporaryDirectory(prefix="corex-mars-job-") as scratch:
            output_directory = Path(scratch) / "results"
            outcome, published = _run_and_publish(
                ctx,
                job_path=job_path.resolve(),
                output_directory=output_directory,
            )
        node_outputs: dict[str, Any] = {
            "manifest": published.manifest,
            "files": published.files,
        }
        for primary_key, ref in published.primary_files.items():
            port = _PRIMARY_OUTPUT_PORTS.get(primary_key)
            if port:
                node_outputs[port] = ref
        return NodeResult(outputs=node_outputs, warnings=outcome.warnings)


MARS_NODE_DESCRIPTORS = (
    plugin_descriptor(MarsBatchSolveNodePlugin),
    plugin_descriptor(MarsTimeHistoryNodePlugin),
    plugin_descriptor(MarsRunJobNodePlugin),
)

__all__ = [
    "MARS_BATCH_SOLVE_NODE_TYPE_ID",
    "MARS_NODE_DESCRIPTORS",
    "MARS_RUN_JOB_NODE_TYPE_ID",
    "MARS_TIME_HISTORY_NODE_TYPE_ID",
    "MarsBatchSolveNodePlugin",
    "MarsRunJobNodePlugin",
    "MarsTimeHistoryNodePlugin",
]
