# Purpose: Freeze comparable Generic Plot preparation and full-export measurements.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_graph_ownership_benchmarks.py
"""Run in fresh processes; alternate baseline/candidate processes externally.

Timing mode never installs counters. Instrumented mode executes each scenario
once, without reporting timing. Fixture generation, cache priming, context
construction, hashing and output inspection are outside the measured call.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _configure(source: Path, work: Path) -> None:
    if not (source / "ea_node_editor/__init__.py").is_file():
        raise ValueError(f"Not a COREX source root: {source}")
    if any(name in {"ea_node_editor", "corex"} or name.startswith(("ea_node_editor.", "corex.")) for name in sys.modules):
        raise RuntimeError("Source selection must precede application imports")
    sys.path.insert(0, str(source))
    for key in ("LOCALAPPDATA", "APPDATA", "MPLCONFIGDIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "TEMP", "TMP"):
        directory = work / key.lower()
        directory.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(directory)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["MPLBACKEND"] = "Agg"
    # Verify immediately, before any application implementation is imported.
    import ea_node_editor
    if Path(ea_node_editor.__file__).resolve().parent != source / "ea_node_editor":
        raise RuntimeError(f"Wrong source imported: {ea_node_editor.__file__}")


def _origins(source: Path) -> dict[str, str]:
    result = {}
    for name, module in tuple(sys.modules.items()):
        if name not in {"ea_node_editor", "corex"} and not name.startswith(("ea_node_editor.", "corex.")):
            continue
        location = getattr(module, "__file__", None)
        if location is not None:
            path = Path(location).resolve()
            package_root = source / name.split(".", 1)[0]
            if not path.is_relative_to(package_root):
                raise RuntimeError(f"Application import escaped selected source: {name}: {path}")
            result[name] = str(path)
    return result


def _context(**kwargs):
    from ea_node_editor.nodes.execution_context import ExecutionContext
    return ExecutionContext(run_id="benchmark", node_id="plot", workspace_id="workspace", inputs={},
                            properties={}, emit_log=lambda *_: None, **kwargs)


def _fixtures(work: Path, rows: int, export_rows: int):
    import numpy as np
    from ea_node_editor.addons.tabular_data import loader_cache_service as loaders
    from ea_node_editor.runtime_contracts import ArraySlice2DRef, TabularWindowRef

    sources = work / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    service = loaders.TabularLoaderCacheService(cache_dir=work / "loader_cache")
    loaders._shared_service = service  # Process-local dependency isolation, before any consumers run.
    refs = {}
    hashes = {}
    for name, count in (("prepare", rows), ("export", export_rows)):
        table = sources / f"{name}.csv"
        with table.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("time", "signal", "other"))
            writer.writerows((i, i % 97 - 48, i * 2) for i in range(count))
        array = sources / f"{name}.npy"
        np.save(array, np.arange(count * 8, dtype=np.float64).reshape(count, 8))
        for kind, path in (("table", table), ("array", array)):
            refs[f"{name}_{kind}"] = service.open_source(path)
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    offset = min(137, rows // 4)
    window_limit = min(50_000, rows - offset)
    window = TabularWindowRef(ref_id="fixture_window", table_data=refs["prepare_table"],
                             row_offset=offset, row_limit=window_limit, columns=("time", "signal", "other"))
    sliced = ArraySlice2DRef(ref_id="fixture_slice", array_data=refs["prepare_array"],
                            row_offset=offset, row_limit=window_limit, column_offset=1, column_limit=4)
    mapping = {"columns": ["time", "signal"], "x": "time", "y": ["signal"]}
    scenarios = {
        "memory": ("plot.bar", {"x": list(range(rows)), "y": [i % 97 - 48 for i in range(rows)]}, {}),
        "table": ("plot.bar", refs["prepare_table"], {"tabular_mapping": mapping}),
        "window": ("plot.bar", window, {"tabular_mapping": {**mapping, "row_limit": min(20_000, window_limit)}}),
        "array": ("plot.heatmap", refs["prepare_array"], {}),
        "slice": ("plot.heatmap", sliced, {}),
    }
    aliases = {}
    for name, ref in refs.items():
        aliases[ref.ref_id] = f"fixture:{name}"
        aliases[ref.source_uri] = f"fixture:{name}:uri"
    return service, refs, scenarios, hashes, aliases


def _canonical(value, aliases):
    if isinstance(value, dict):
        return {key: _canonical(item, aliases) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item, aliases) for item in value]
    if isinstance(value, str):
        return aliases.get(value, value)
    return value


def _instrument(operation, service):
    """Count actual loader method invocations, including generator creation once."""
    counts = Counter()
    reads = []
    names = ("ensure_table_ref", "ensure_array_ref", "schema", "window_columns", "column_arrays",
             "slice_2d", "sample_array", "arrow_batches", "to_numpy", "to_pandas", "to_polars")
    with ExitStack() as stack:
        for name in names:
            original = getattr(service, name)

            def counted(*args, _name=name, _original=original, **kwargs):
                counts[f"loader.{_name}"] += 1
                if _name in {"column_arrays", "sample_array", "slice_2d", "arrow_batches"}:
                    detail = {"method": _name, **kwargs}
                    if _name == "sample_array":
                        detail.update(rows=len(args[1]), columns=len(args[2]))
                    elif _name in {"slice_2d", "arrow_batches"}:
                        request = args[1]
                        detail.update({key: getattr(request, key) for key in
                                       ("row_offset", "row_limit", "column_offset", "column_limit", "batch_size", "columns")
                                       if hasattr(request, key)})
                    reads.append(detail)
                return _original(*args, **kwargs)

            stack.enter_context(patch.object(service, name, counted))
        result = operation()
    return result, dict(sorted(counts.items())), reads


def _measure(prepare, *, warmups: int, iterations: int):
    samples, fingerprints = [], set()
    for index in range(warmups + iterations):
        operation, inspect = prepare(index)
        started = time.perf_counter_ns()
        result = operation()
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        if index >= warmups:
            samples.append(elapsed)
        summary = inspect(result)  # Deliberately outside timed region.
        fingerprints.add(summary["fingerprint"])
    if len(fingerprints) != 1:
        raise AssertionError("Nondeterministic fixture results")
    return {"samples_ms": samples, "median_ms": statistics.median(samples),
            "p95_ms": statistics.quantiles(samples, n=20, method="inclusive")[18] if len(samples) > 1 else samples[0],
            "semantic": summary}


def run(args):
    source, output = args.source_root.resolve(), args.output.resolve()
    work = (args.work_dir or output.with_suffix(".work")).resolve()
    _configure(source, work)
    from ea_node_editor.execution.plot_backend import plot_render_request_to_payload
    from ea_node_editor.execution.runtime_snapshot import RuntimeSnapshot, RuntimeSnapshotContext
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from ea_node_editor.nodes.builtins.plot.generic import build_generic_plot_render_request
    from ea_node_editor.persistence.artifact_resolution import ProjectArtifactResolver
    from ea_node_editor.persistence.artifact_store import ProjectArtifactStore

    service, refs, scenarios, hashes, aliases = _fixtures(work, args.rows, args.export_rows)
    registry = build_default_registry()
    plugins = {type_id: registry.create(type_id) for type_id in ("plot.bar", "plot.heatmap")}

    def summarize_request(result):
        request, warnings = result
        payload = _canonical(plot_render_request_to_payload(request), aliases)
        return {"fingerprint": _digest([payload, warnings]), "warnings": list(warnings),
                "series": [{"points": max((len(item.get(key, ())) for key in ("x", "y", "values", "points")), default=0),
                            "decimation": item.get("decimation"),
                            "source_ref": _canonical(item.get("source_ref"), aliases)} for item in request.series]}

    preparations = {}
    for name, (type_id, value, properties) in scenarios.items():
        def prepare(_index, value=value, properties=properties, type_id=type_id):
            return (lambda: build_generic_plot_render_request(node_type_id=type_id, properties=properties,
                                                             series_input=value)), summarize_request
        preparations[name] = (prepare, args.warmups, args.iterations)

    for kind in ("table", "array"):
        def prepare_export(index, kind=kind):
            type_id = "plot.bar" if kind == "table" else "plot.heatmap"
            project = work / "exports" / kind / str(index) / "plot.cxproj"
            project.parent.mkdir(parents=True, exist_ok=True)
            snapshot = RuntimeSnapshot(schema_version=1, project_id="benchmark", metadata={})
            store = ProjectArtifactStore.from_project_metadata(project_path=project, project_metadata=snapshot.metadata)
            snapshot_context = RuntimeSnapshotContext.from_snapshot(snapshot, project_path=str(project), artifact_store=store)
            resolver = ProjectArtifactResolver(project_path=project, artifact_store=store)
            ctx = _context(project_path=str(project), runtime_snapshot=snapshot, runtime_snapshot_context=snapshot_context,
                           path_resolver=resolver.resolve_to_path, node_type_id=type_id)
            ctx.inputs = {"series": refs[f"export_{kind}"]}
            ctx.properties = {"archive_export_on_run": True, "backend": "matplotlib"}
            if kind == "table":
                ctx.properties["tabular_mapping"] = {"columns": ["time", "signal"], "x": "time", "y": ["signal"]}

            def inspect(result):
                data = resolver.resolve_to_path(result.outputs["data_export"].ref)
                static = resolver.resolve_to_path(result.outputs["static_export"].ref)
                with data.open(encoding="utf-8", newline="") as stream:
                    reader = csv.reader(stream)
                    header = next(reader)
                    row_count = sum(1 for _ in reader)
                if row_count != args.export_rows or not static.is_file():
                    raise AssertionError("Full-source paired export was not produced")
                metadata = result.outputs["exports"]["data_metadata"]
                return {"fingerprint": _digest([hashlib.sha256(data.read_bytes()).hexdigest(), metadata]),
                        "rows": row_count, "columns": header, "metadata": metadata}
            return lambda: plugins[type_id].execute(ctx), inspect
        preparations[f"export_{kind}"] = (prepare_export, args.export_warmups, args.export_iterations)

    selected = args.scenarios.split(",") if args.scenarios else list(preparations)
    unknown = set(selected) - preparations.keys()
    if unknown:
        raise ValueError(f"Unknown scenarios: {sorted(unknown)}")
    # Prime source/cache state and all invoked backends outside measurements.
    for name in selected:
        prepare, _, _ = preparations[name]
        operation, inspect = prepare(-1)
        inspect(operation())
    results = {}
    for name in selected:
        prepare, warmups, iterations = preparations[name]
        if args.mode == "timing":
            results[name] = _measure(prepare, warmups=warmups, iterations=iterations)
        else:
            operation, inspect = prepare(0)
            result, counts, reads = _instrument(operation, service)
            results[name] = {"semantic": inspect(result), "counts": counts, "raw_events": counts, "reads": reads}
    report = {
        "schema_version": 1, "benchmark": "generic_plot", "mode": args.mode,
        "source_root": str(source), "source_origins": _origins(source),
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment": {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
                        "machine": platform.machine(), "dependencies": {name: importlib.metadata.version(name)
                                                                       for name in ("numpy", "pyarrow", "matplotlib", "PyQt6")}},
        "configuration": {"rows": args.rows, "array_columns": 8, "export_rows": args.export_rows,
                          "scenario_node_types": {**{name: item[0] for name, item in scenarios.items()},
                                                  "export_table": "plot.bar", "export_array": "plot.heatmap"},
                          "warmups": args.warmups, "iterations": args.iterations,
                          "export_warmups": args.export_warmups, "export_iterations": args.export_iterations},
        "fixture_hashes": hashes, "fixture_hash": _digest(hashes), "fixture_identity_aliases": aliases,
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(output), "fixture_hash": report["fixture_hash"], "scenarios": selected}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--mode", choices=("timing", "instrumented"), default="timing")
    parser.add_argument("--scenarios", help="Comma-separated memory,table,window,array,slice,export_table,export_array")
    parser.add_argument("--rows", type=int, default=200_000)
    parser.add_argument("--export-rows", type=int, default=100_000)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--export-warmups", type=int, default=1)
    parser.add_argument("--export-iterations", type=int, default=10)
    args = parser.parse_args()
    if min(args.rows, args.export_rows, args.iterations, args.export_iterations) < 1 or min(args.warmups, args.export_warmups) < 0:
        parser.error("Row/iteration counts must be positive and warmups nonnegative")
    run(args)


if __name__ == "__main__":
    main()
