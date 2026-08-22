from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.execution.viewer_camera_state import apply_camera_state
from ea_node_editor.execution.viewer_pyvista_style import scalar_bar_args_for_viewport
from ea_node_editor.execution.dpf_runtime.base import DpfRuntimeBase
from ea_node_editor.execution.dpf_runtime.contracts import (
    DEFAULT_VTM_FILENAME,
    DEFAULT_VTU_BASENAME,
    DPF_VIEWER_DATASET_HANDLE_KIND,
    DpfMaterializationResult,
    DpfTableExportResult,
)
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_VIEWER_DATASET_DATA_TYPE,
)
from ea_node_editor.nodes.output_artifacts import register_staged_artifact
from ea_node_editor.nodes.runtime_refs import RuntimeArtifactRef, RuntimeHandleRef
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore
from ea_node_editor.runtime_contracts import PATH_DATA_TYPE_ID


class DpfRuntimeMaterializationMixin(DpfRuntimeBase):
    def export_viewer_transport_bundle(
        self,
        value: Any,
        *,
        model: Any,
        bundle_root: str | Path,
        mesh: Any | None = None,
        workspace_id: str = "",
        session_id: str = "",
        transport_revision: int = 0,
    ) -> dict[str, Any]:
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        _, resolved_model = self._resolve_model_handle_and_object(model)
        resolved_mesh = self._resolve_mesh_object(mesh, model=resolved_model)

        root_path = Path(bundle_root).expanduser().resolve()
        self._clear_output_path(root_path)
        root_path.mkdir(parents=True, exist_ok=True)

        dataset_dir = root_path / "dataset"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        vtu_files = self._write_vtu_bundle(fields_container, resolved_mesh, dataset_dir)
        vtm_files = self._write_vtm_bundle(dataset_dir)
        listed_files = sorted(
            [f"dataset/{name}" for name in vtu_files]
            + [f"dataset/{name}" for name in vtm_files]
        )
        entry_file = f"dataset/{DEFAULT_VTM_FILENAME}"
        entry_path = root_path / entry_file
        manifest_path = root_path / "transport_manifest.json"
        metadata = {
            **self._build_fields_container_metadata(
                fields_container,
                result_name=str(fields_ref.metadata.get("result_name", "")).strip(),
                model=resolved_model,
            ),
            **self._build_mesh_metadata(resolved_mesh),
            "source_handle_id": fields_ref.handle_id,
        }
        manifest_payload = {
            "schema": "ea.dpf.viewer_transport_bundle.v1",
            "workspace_id": str(workspace_id).strip(),
            "session_id": str(session_id).strip(),
            "transport_revision": int(transport_revision),
            "entry_file": entry_file,
            "files": listed_files,
            "metadata": metadata,
        }
        manifest_path.write_text(
            json.dumps(manifest_payload, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return {
            "kind": "dpf_transport_bundle",
            "version": 1,
            "schema": "ea.dpf.viewer_transport_bundle.v1",
            "manifest_path": str(manifest_path),
            "bundle_root": str(root_path),
            "entry_file": entry_file,
            "entry_path": str(entry_path),
            "files": listed_files,
            "metadata": metadata,
        }

    def export_field_artifacts(
        self,
        value: Any,
        *,
        model: Any,
        artifact_store: ProjectArtifactStore,
        artifact_key: str,
        export_formats: Iterable[str],
        mesh: Any | None = None,
        camera_state: Mapping[str, Any] | None = None,
        temporary_root_parent: str | Path | None = None,
        node_workspace_id: str = "",
        node_workspace_name: str = "",
        node_id: str = "",
        node_title: str = "",
        node_type: str = "",
    ) -> dict[str, RuntimeArtifactRef]:
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        _, resolved_model = self._resolve_model_handle_and_object(model)
        resolved_mesh = self._resolve_mesh_object(mesh, model=resolved_model)
        normalized_key = self._normalize_artifact_key(artifact_key)
        normalized_formats = self._normalize_export_formats(export_formats)
        if not normalized_formats:
            raise ValueError("export_formats must contain at least one supported format")

        artifact_store.ensure_staging_root(temporary_root_parent=temporary_root_parent)
        artifact_refs: dict[str, RuntimeArtifactRef] = {}
        attempted_ids: list[str] = []
        attempted_paths: list[str] = []
        try:
            for export_format in normalized_formats:
                artifact_id = self._artifact_id(normalized_key, export_format)
                slot = self._artifact_slot(normalized_key, export_format)
                filename = "field.csv" if export_format == "csv" else "preview.png" if export_format == "png" else export_format
                artifact_paths = artifact_store.node_artifact_paths(
                    artifact_id=artifact_id,
                    workspace_id=node_workspace_id,
                    workspace_name=node_workspace_name,
                    node_id=node_id or "dpf",
                    node_title=node_title or "DPF Export",
                    node_type=node_type or "DPF Export",
                    io_dir="out",
                    subdirectory=f"dpf/{normalized_key}",
                    filename=filename,
                )
                relative_path = artifact_paths.staged_relative_path
                attempted_paths.append(relative_path)
                attempted_ids.append(artifact_id)
                artifact_store.discard_staged_entries((artifact_id,))
                artifact_store.discard_staged_paths((relative_path,))
                output_path = artifact_store.staged_target_path(relative_path)
                entry_metadata = {
                    "artifact_key": normalized_key,
                    "source_handle_id": fields_ref.handle_id,
                    **artifact_paths.metadata,
                }

                if export_format == "csv":
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    self._write_csv_export(fields_container, output_path)
                    entry_metadata["entry_file"] = output_path.name
                elif export_format == "png":
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    self._write_png_export(
                        fields_container,
                        resolved_mesh,
                        output_path,
                        camera_state=camera_state,
                    )
                    entry_metadata["entry_file"] = output_path.name
                elif export_format == "vtu":
                    output_path.mkdir(parents=True, exist_ok=True)
                    entry_metadata["file_count"] = len(
                        self._write_vtu_bundle(
                            fields_container,
                            resolved_mesh,
                            output_path,
                        )
                    )
                else:
                    output_path.mkdir(parents=True, exist_ok=True)
                    bundle_files = self._write_vtu_bundle(fields_container, resolved_mesh, output_path)
                    bundle_files.extend(self._write_vtm_bundle(output_path))
                    entry_metadata["entry_file"] = DEFAULT_VTM_FILENAME
                    entry_metadata["file_count"] = len(bundle_files)

                artifact_type = self._worker_services.data_types.require(PATH_DATA_TYPE_ID)
                artifact_refs[export_format] = register_staged_artifact(
                    store=artifact_store,
                    artifact_id=artifact_id,
                    payload_path=output_path,
                    relative_path=relative_path,
                    slot=slot,
                    data_type_id=artifact_type.type_id,
                    schema_version=artifact_type.payload_schema_version,
                    format=export_format,
                    provenance="corex.ansys_dpf.materialization",
                    entry_metadata=entry_metadata,
                    metadata={
                        "artifact_key": normalized_key,
                        **({"entry_file": entry_metadata["entry_file"]} if "entry_file" in entry_metadata else {}),
                    },
                )
        except BaseException:
            try:
                artifact_store.discard_staged_entries(attempted_ids)
            except BaseException:
                pass
            try:
                artifact_store.discard_staged_paths(attempted_paths)
            except BaseException:
                pass
            raise

        return artifact_refs

    def materialize_viewer_dataset(
        self,
        value: Any,
        *,
        model: Any,
        output_profile: str,
        mesh: Any | None = None,
        artifact_store: ProjectArtifactStore | None = None,
        artifact_key: str = "",
        export_formats: Iterable[str] = (),
        camera_state: Mapping[str, Any] | None = None,
        temporary_root_parent: str | Path | None = None,
        run_id: str = "",
        owner_scope: str = "",
        node_workspace_id: str = "",
        node_workspace_name: str = "",
        node_id: str = "",
        node_title: str = "",
        node_type: str = "",
    ) -> DpfMaterializationResult:
        normalized_profile = self._normalize_output_profile(output_profile)
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        _, resolved_model = self._resolve_model_handle_and_object(model)
        resolved_mesh = self._resolve_mesh_object(mesh, model=resolved_model)

        if normalized_profile == "memory" and tuple(export_formats):
            raise ValueError("export_formats are only valid for stored or both output profiles")
        if normalized_profile in {"stored", "both"} and artifact_store is None:
            raise ValueError("artifact_store is required for stored or both output profiles")

        summary = {
            **self._build_fields_container_metadata(
                fields_container,
                result_name=str(fields_ref.metadata.get("result_name", "")).strip(),
                model=resolved_model,
            ),
            **self._build_mesh_metadata(resolved_mesh),
            "source_handle_id": fields_ref.handle_id,
            "output_profile": normalized_profile,
        }

        dataset_ref: RuntimeHandleRef | None = None
        if normalized_profile in {"memory", "both"}:
            dataset = self._build_viewer_dataset(fields_container, resolved_mesh)
            summary["dataset_type"] = self._dataset_kind(dataset)
            summary["array_names"] = self._dataset_array_names(dataset)
            dataset_ref = self._worker_services.register_handle(
                dataset,
                data_type_id=DPF_VIEWER_DATASET_DATA_TYPE,
                kind=DPF_VIEWER_DATASET_HANDLE_KIND,
                owner_scope=self._resolve_handle_owner_scope(run_id=run_id, owner_scope=owner_scope),
                metadata=summary,
            )

        artifacts: dict[str, RuntimeArtifactRef] = {}
        if normalized_profile in {"stored", "both"}:
            artifacts = self.export_field_artifacts(
                value,
                model=model,
                artifact_store=artifact_store if artifact_store is not None else ProjectArtifactStore(project_path=None),
                artifact_key=artifact_key,
                export_formats=export_formats,
                mesh=mesh,
                camera_state=camera_state,
                temporary_root_parent=temporary_root_parent,
                node_workspace_id=node_workspace_id,
                node_workspace_name=node_workspace_name,
                node_id=node_id,
                node_title=node_title,
                node_type=node_type,
            )

        return DpfMaterializationResult(
            output_profile=normalized_profile,
            dataset_ref=dataset_ref,
            artifacts=artifacts,
            summary=summary,
        )

    def export_field_table(
        self,
        value: Any,
        *,
        model: Any,
        artifact_store: ProjectArtifactStore | None = None,
        artifact_key: str = "",
        include_coordinates: bool = True,
        output_profile: str = "stored",
        temporary_root_parent: str | Path | None = None,
        node_workspace_id: str = "",
        node_workspace_name: str = "",
        node_id: str = "",
        node_title: str = "",
        node_type: str = "",
    ) -> DpfTableExportResult:
        normalized_profile = self._normalize_output_profile(output_profile)
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        _, resolved_model = self._resolve_model_handle_and_object(model)
        rows, columns = self._build_field_table_rows(
            fields_container,
            resolved_model,
            include_coordinates=include_coordinates,
        )

        csv_artifact: RuntimeArtifactRef | None = None
        if normalized_profile in {"stored", "both"}:
            if artifact_store is None:
                raise ValueError("artifact_store is required for stored or both output profiles")
            normalized_key = self._normalize_artifact_key(artifact_key or "table")
            artifact_id = self._artifact_id(normalized_key, "csv")
            slot = self._artifact_slot(normalized_key, "csv")
            artifact_store.ensure_staging_root(temporary_root_parent=temporary_root_parent)
            artifact_paths = artifact_store.node_artifact_paths(
                artifact_id=artifact_id,
                workspace_id=node_workspace_id,
                workspace_name=node_workspace_name,
                node_id=node_id or "dpf",
                node_title=node_title or "DPF Table Export",
                node_type=node_type or "DPF Table Export",
                io_dir="out",
                subdirectory=f"dpf/{normalized_key}",
                filename="table.csv",
            )
            relative_path = artifact_paths.staged_relative_path
            try:
                artifact_store.discard_staged_entries((artifact_id,))
                artifact_store.discard_staged_paths((relative_path,))
                expected_path = artifact_store.staged_target_path(relative_path)
                expected_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_table_csv(expected_path, rows, columns)
                entry_metadata = {
                    "artifact_key": normalized_key,
                    "source_handle_id": fields_ref.handle_id,
                    "entry_file": expected_path.name,
                    "row_count": len(rows),
                    **artifact_paths.metadata,
                }
                artifact_type = self._worker_services.data_types.require(PATH_DATA_TYPE_ID)
                csv_artifact = register_staged_artifact(
                    store=artifact_store,
                    artifact_id=artifact_id,
                    payload_path=expected_path,
                    relative_path=relative_path,
                    slot=slot,
                    data_type_id=artifact_type.type_id,
                    schema_version=artifact_type.payload_schema_version,
                    format="csv",
                    provenance="corex.ansys_dpf.materialization",
                    entry_metadata=entry_metadata,
                    metadata={
                        "artifact_key": normalized_key,
                        "entry_file": expected_path.name,
                        "row_count": len(rows),
                    },
                )
            except BaseException:
                try:
                    artifact_store.discard_staged_entries((artifact_id,))
                except BaseException:
                    pass
                try:
                    artifact_store.discard_staged_paths((relative_path,))
                except BaseException:
                    pass
                raise

        return DpfTableExportResult(rows=rows, columns=columns, csv_artifact=csv_artifact)

    def _build_field_table_rows(
        self,
        fields_container: Any,
        resolved_model: Any,
        *,
        include_coordinates: bool,
    ) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
        import numpy as np

        if len(fields_container) == 0:
            raise ValueError("export_field_table requires a non-empty fields container")

        location = self._fields_container_location(fields_container)
        component_count = max(int(getattr(fields_container[0], "component_count", 1)), 1)
        set_ids = self._fields_container_set_ids(fields_container)
        if len(set_ids) != len(fields_container):
            set_ids = tuple(range(1, len(fields_container) + 1))
        try:
            frequencies = list(resolved_model.metadata.time_freq_support.time_frequencies.data)
        except Exception:
            frequencies = []

        emit_coordinates = include_coordinates and location == "Nodal"
        coordinate_lookup: dict[int, tuple[float, float, float]] = {}
        if emit_coordinates:
            coordinates_field = resolved_model.metadata.meshed_region.nodes.coordinates_field
            node_ids = np.asarray(coordinates_field.scoping.ids, dtype=int)
            coordinates = np.asarray(coordinates_field.data, dtype=float).reshape(-1, 3)
            coordinate_lookup = {
                int(node_id): (float(row[0]), float(row[1]), float(row[2]))
                for node_id, row in zip(node_ids, coordinates)
            }

        value_columns = ("value",) if component_count == 1 else tuple(
            f"comp_{component}" for component in range(1, component_count + 1)
        ) + ("magnitude",)
        columns = (
            ("entity_id",)
            + (("x", "y", "z") if emit_coordinates else ())
            + ("set_id", "time_value")
            + value_columns
        )

        rows: list[dict[str, Any]] = []
        for index in range(len(fields_container)):
            field_value = fields_container[index]
            entity_ids = np.asarray(field_value.scoping.ids, dtype=int)
            data = np.asarray(field_value.data, dtype=float)
            if entity_ids.size == 0 or data.size != entity_ids.size * component_count:
                raise ValueError(
                    "export_field_table requires one row of values per scoped entity; "
                    f"got {data.size} values for {entity_ids.size} entities at location "
                    f"{location or 'unknown'!r}. Convert ElementalNodal results to Nodal or "
                    "Elemental first."
                )
            data = data.reshape(len(entity_ids), -1)
            set_id = int(set_ids[index])
            frequency_index = set_id - 1
            time_value = (
                float(frequencies[frequency_index])
                if 0 <= frequency_index < len(frequencies)
                else None
            )
            for entity_index, entity_id in enumerate(entity_ids):
                row: dict[str, Any] = {"entity_id": int(entity_id)}
                if emit_coordinates:
                    x, y, z = coordinate_lookup.get(int(entity_id), (None, None, None))
                    row.update({"x": x, "y": y, "z": z})
                row["set_id"] = set_id
                row["time_value"] = time_value
                values = data[entity_index]
                if component_count == 1:
                    row["value"] = float(values[0])
                else:
                    for component in range(component_count):
                        row[f"comp_{component + 1}"] = float(values[component])
                    row["magnitude"] = float(np.linalg.norm(values))
                rows.append(row)
        return tuple(rows), columns

    @staticmethod
    def _write_table_csv(
        output_path: Path,
        rows: tuple[dict[str, Any], ...],
        columns: tuple[str, ...],
    ) -> None:
        import csv

        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: ("" if row.get(key) is None else row.get(key)) for key in columns})

    @staticmethod
    def _clear_output_path(path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            return
        path.unlink(missing_ok=True)

    def _write_csv_export(self, fields_container: Any, output_path: Path) -> None:
        dpf = self._dpf_module()
        operator = dpf.operators.serialization.field_to_csv()
        operator.inputs.file_path(str(output_path))
        operator.inputs.field_or_fields_container(fields_container)
        operator.run()

    def _write_png_export(
        self,
        fields_container: Any,
        mesh: Any,
        output_path: Path,
        *,
        camera_state: Mapping[str, Any] | None = None,
    ) -> None:
        pyvista = self._pyvista_module()
        dataset = self._build_viewer_dataset(fields_container, mesh)
        preview_dataset = self._preview_dataset(dataset)
        plotter = pyvista.Plotter(off_screen=True)
        try:
            array_name = self._preferred_array_name(preview_dataset)
            viewport_width, viewport_height = self._plotter_window_size(plotter)
            plotter.add_mesh(
                preview_dataset,
                scalars=array_name,
                scalar_bar_args=(
                    scalar_bar_args_for_viewport(viewport_width, viewport_height)
                    if array_name
                    else None
                ),
            )
            if not apply_camera_state(plotter, camera_state or {}):
                plotter.view_isometric()
            plotter.show(screenshot=str(output_path), auto_close=False)
        finally:
            plotter.close()

    @staticmethod
    def _plotter_window_size(plotter: Any) -> tuple[int, int]:
        window_size = getattr(plotter, "window_size", None)
        if isinstance(window_size, (list, tuple)) and len(window_size) >= 2:
            try:
                width = int(window_size[0])
                height = int(window_size[1])
            except (TypeError, ValueError):
                width = 0
                height = 0
            if width > 0 and height > 0:
                return width, height
        return 1024, 768

    def _write_vtu_bundle(self, fields_container: Any, mesh: Any, output_dir: Path) -> list[str]:
        dpf = self._dpf_module()
        operator = dpf.operators.serialization.vtu_export()
        operator.inputs.directory(str(output_dir))
        operator.inputs.base_name(DEFAULT_VTU_BASENAME)
        operator.inputs.mesh(mesh)
        operator.inputs.fields1(fields_container)
        operator.outputs.path()
        return sorted(path.name for path in output_dir.glob("*.vtu"))

    def _write_vtm_bundle(self, output_dir: Path) -> list[str]:
        pyvista = self._pyvista_module()
        vtu_files = sorted(output_dir.glob("*.vtu"))
        multiblock = pyvista.MultiBlock([pyvista.read(path) for path in vtu_files])
        target_path = output_dir / DEFAULT_VTM_FILENAME
        multiblock.save(target_path)
        return [target_path.name]

    def _build_viewer_dataset(self, fields_container: Any, mesh: Any) -> Any:
        pyvista = self._pyvista_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            if len(fields_container) == 1:
                vtk_path = temp_root / "dataset.vtk"
                dpf = self._dpf_module()
                operator = dpf.operators.serialization.vtk_export()
                operator.inputs.file_path(str(vtk_path))
                operator.inputs.mesh(mesh)
                operator.inputs.fields1(fields_container)
                operator.run()
                return pyvista.read(vtk_path)

            self._write_vtu_bundle(fields_container, mesh, temp_root)
            return pyvista.MultiBlock([pyvista.read(path) for path in sorted(temp_root.glob("*.vtu"))])


__all__ = [
    "DpfRuntimeMaterializationMixin",
]
