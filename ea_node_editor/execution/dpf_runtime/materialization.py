from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

from ea_node_editor.execution.dpf_runtime.base import DpfRuntimeBase
from ea_node_editor.execution.dpf_runtime.contracts import (
    DEFAULT_VTM_FILENAME,
    DEFAULT_VTU_BASENAME,
    DPF_VIEWER_DATASET_HANDLE_KIND,
    DpfMaterializationResult,
)
from ea_node_editor.nodes.types import RuntimeArtifactRef, RuntimeHandleRef
from ea_node_editor.persistence.artifact_store import ProjectArtifactStore


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
        temporary_root_parent: str | Path | None = None,
    ) -> dict[str, RuntimeArtifactRef]:
        fields_ref, fields_container = self._resolve_fields_container_handle_and_object(value)
        _, resolved_model = self._resolve_model_handle_and_object(model)
        resolved_mesh = self._resolve_mesh_object(mesh, model=resolved_model)
        normalized_key = self._normalize_artifact_key(artifact_key)
        normalized_formats = self._normalize_export_formats(export_formats)
        if not normalized_formats:
            raise ValueError("export_formats must contain at least one supported format")

        staging_root = artifact_store.ensure_staging_root(temporary_root_parent=temporary_root_parent)
        artifact_refs: dict[str, RuntimeArtifactRef] = {}
        for export_format in normalized_formats:
            artifact_id = self._artifact_id(normalized_key, export_format)
            slot = self._artifact_slot(normalized_key, export_format)
            relative_path = self._artifact_relative_path(normalized_key, export_format)
            output_path = staging_root.joinpath(*PurePosixPath(relative_path).parts)
            self._clear_output_path(output_path)
            entry_metadata = {
                "format": export_format,
                "artifact_key": normalized_key,
                "source_handle_id": fields_ref.handle_id,
            }

            if export_format == "csv":
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_csv_export(fields_container, output_path)
                entry_metadata["entry_file"] = output_path.name
            elif export_format == "png":
                output_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_png_export(fields_container, resolved_mesh, output_path)
                entry_metadata["entry_file"] = output_path.name
            elif export_format == "vtu":
                output_path.mkdir(parents=True, exist_ok=True)
                entry_metadata["files"] = self._write_vtu_bundle(fields_container, resolved_mesh, output_path)
            else:
                output_path.mkdir(parents=True, exist_ok=True)
                bundle_files = self._write_vtu_bundle(fields_container, resolved_mesh, output_path)
                bundle_files.extend(self._write_vtm_bundle(output_path))
                entry_metadata["entry_file"] = DEFAULT_VTM_FILENAME
                entry_metadata["files"] = sorted(bundle_files)

            artifact_store.register_staged_entry(
                artifact_id,
                relative_path=relative_path,
                slot=slot,
                extra=entry_metadata,
            )
            artifact_refs[export_format] = RuntimeArtifactRef.staged(
                artifact_id,
                metadata={
                    "format": export_format,
                    "artifact_key": normalized_key,
                    "relative_path": relative_path,
                    **({"entry_file": entry_metadata["entry_file"]} if "entry_file" in entry_metadata else {}),
                },
            )

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
        temporary_root_parent: str | Path | None = None,
        run_id: str = "",
        owner_scope: str = "",
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
                temporary_root_parent=temporary_root_parent,
            )

        return DpfMaterializationResult(
            output_profile=normalized_profile,
            dataset_ref=dataset_ref,
            artifacts=artifacts,
            summary=summary,
        )

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

    def _write_png_export(self, fields_container: Any, mesh: Any, output_path: Path) -> None:
        pyvista = self._pyvista_module()
        dataset = self._build_viewer_dataset(fields_container, mesh)
        preview_dataset = self._preview_dataset(dataset)
        plotter = pyvista.Plotter(off_screen=True)
        try:
            array_name = self._preferred_array_name(preview_dataset)
            plotter.add_mesh(preview_dataset, scalars=array_name)
            plotter.view_isometric()
            plotter.show(screenshot=str(output_path), auto_close=False)
        finally:
            plotter.close()

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
