# Purpose: Measure graph reconciliation through stable production entry points.
# Map: subsystems/graph_domain.md
# Tests: tests/test_plot_graph_ownership_benchmarks.py
"""Fresh-process graph benchmarks with fixture reset outside each timed call.

Run five baseline/candidate process pairs externally, alternating order. The
instrumented mode profiles call boundaries separately and never emits timings.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path


SCRIPT = '''@corex.node
@corex.input("payload", value_type=float)
@corex.output("result", value_type=float)
@corex.number("gain", default=1.0, section="Style")
def run(ctx, payload, gain):
    return {"result": payload * gain}
'''
CANDIDATE_SCRIPT = SCRIPT.replace('value_type=float)', 'value_type=corex.Any)', 1)
OPERATIONS = ("script_apply", "dynamic_insert", "dynamic_remove", "dynamic_rename", "property", "normalization")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _configure(source: Path, work: Path):
    if not (source / "ea_node_editor/__init__.py").is_file():
        raise ValueError(f"Not a COREX source root: {source}")
    if any(name in {"ea_node_editor", "corex"} or name.startswith(("ea_node_editor.", "corex.")) for name in sys.modules):
        raise RuntimeError("Source selection must precede application imports")
    sys.path.insert(0, str(source))
    for key in ("LOCALAPPDATA", "APPDATA", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "TEMP", "TMP"):
        directory = work / key.lower()
        directory.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(directory)
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    import ea_node_editor
    if Path(ea_node_editor.__file__).resolve().parent != source / "ea_node_editor":
        raise RuntimeError(f"Wrong source imported: {ea_node_editor.__file__}")


def _origins(source):
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


def build_fixture(node_count, *, generation_root=None):
    from ea_node_editor.graph.project_state import ProjectData
    from ea_node_editor.graph.records import EdgeInstance, NodeInstance
    from ea_node_editor.graph.workspace_state import ViewState, WorkspaceData
    from ea_node_editor.nodes.bootstrap import build_builtin_registry
    from ea_node_editor.nodes.node_specs import DynamicPortGroupSpec, NodeTypeSpec, PortSpec, PropertySpec
    from ea_node_editor.runtime_contracts import DOUBLE_DATA_TYPE_ID

    registry = build_builtin_registry(generation_root=generation_root).fork()

    def dynamic_ports(properties):
        return tuple(PortSpec(key, "in", "data", DOUBLE_DATA_TYPE_ID, required=False) for key in properties["input_names"])

    def next_key(properties):
        number = 1
        while f"input{number}" in properties["input_names"]:
            number += 1
        return f"input{number}"

    specs = (
        NodeTypeSpec("benchmark.source", "Source", ("Tests",), "",
                     (PortSpec("value", "out", "data", DOUBLE_DATA_TYPE_ID),), ()),
        NodeTypeSpec("benchmark.sink", "Sink", ("Tests",), "",
                     (PortSpec("value", "in", "data", DOUBLE_DATA_TYPE_ID, required=False),), ()),
        NodeTypeSpec("benchmark.dynamic", "Dynamic", ("Tests",), "", (),
                     (PropertySpec("input_names", "json", ["alpha", "beta"], "Inputs", inspector_visible=False),
                      PropertySpec("mode", "str", "before", "Mode")),
                     dynamic_port_groups=(DynamicPortGroupSpec("inputs", "input_names", "in", dynamic_ports,
                                                              next_key, rename_mode="key",
                                                              key_renamer=lambda _props, _key, value: value.strip()),)),
    )
    for spec in specs:
        registry.register_descriptor(spec, lambda: None)
    registry.freeze()
    nodes = {
        "source": NodeInstance("source", "benchmark.source", "Source", 0, 0),
        "sink": NodeInstance("sink", "benchmark.sink", "Sink", 0, 0),
        "script": NodeInstance("script", "code.python_script", "Script", 0, 0,
                               properties=registry.normalize_properties("code.python_script", {"script": SCRIPT}),
                               exposed_ports={"payload": False}, port_labels={"payload": "Input"},
                               port_modifiers={"payload": ("clean", "graft")}, principal_input_port_id="payload"),
        "dynamic": NodeInstance("dynamic", "benchmark.dynamic", "Dynamic", 0, 0,
                                properties=registry.default_properties("benchmark.dynamic"),
                                exposed_ports={"alpha": False}, port_labels={"alpha": "Old label"},
                                port_modifiers={"alpha": ("graft",)}, principal_input_port_id="alpha"),
    }
    for index in range(node_count - 4):
        key = f"unrelated_{index:04}"
        nodes[key] = NodeInstance(key, "benchmark.source", key, 0, 0)
    edges = {
        "to_script": EdgeInstance("to_script", "source", "value", "script", "payload"),
        "from_script": EdgeInstance("from_script", "script", "result", "sink", "value"),
        "to_dynamic": EdgeInstance("to_dynamic", "source", "value", "dynamic", "alpha"),
    }
    workspace = WorkspaceData(workspace_id="workspace", name="Benchmark", nodes=nodes, edges=edges,
                              views={"view": ViewState("view", "View")}, active_view_id="view")
    project = ProjectData(project_id="benchmark", name="Benchmark", active_workspace_id="workspace",
                          workspaces={"workspace": workspace})
    return registry, project


def prepare_operation(registry, seed, operation):
    from ea_node_editor.graph.model import GraphModel
    from ea_node_editor.graph.registry_normalization import normalize_project_for_registry
    # Reset is deliberately outside the returned measured callable.
    model = GraphModel(copy.deepcopy(seed))
    workspace = model.active_workspace
    mutation = model.validated_mutations(workspace.workspace_id, registry)
    calls = {
        "script_apply": lambda: mutation.apply_python_script("script", CANDIDATE_SCRIPT),
        "dynamic_insert": lambda: mutation.insert_dynamic_port("dynamic", "inputs", 1),
        "dynamic_remove": lambda: mutation.remove_dynamic_port("dynamic", "inputs", "alpha"),
        "dynamic_rename": lambda: mutation.rename_dynamic_port("dynamic", "inputs", "alpha", "renamed"),
        "property": lambda: mutation.set_node_property("dynamic", "mode", "after"),
        "normalization": lambda: normalize_project_for_registry(model.project, registry),
    }

    def inspect(result):
        payload = {"nodes": {key: asdict(node) for key, node in workspace.nodes.items()},
                   "edges": {key: asdict(edge) for key, edge in workspace.edges.items()},
                   "revision": workspace.mutation_revision, "return_value": result}
        return {"fingerprint": _digest(payload), "node_count": len(workspace.nodes),
                "edges": payload["edges"], "revision": workspace.mutation_revision,
                "return_value": result, "changed_nodes": {key: payload["nodes"][key] for key in ("script", "dynamic")}}
    return calls[operation], inspect


def _instrument(operation):
    raw = Counter()

    def profile(frame, event, _arg):
        if event == "call":
            module = frame.f_globals.get("__name__", "")
            if module.startswith(("ea_node_editor.graph.", "ea_node_editor.nodes.")):
                raw[f"{module}:{frame.f_code.co_qualname}"] += 1
            elif module == "copy" and frame.f_code.co_name in {"copy", "deepcopy"}:
                value_type = type(frame.f_locals.get("x"))
                if value_type.__module__.startswith("ea_node_editor.graph."):
                    raw[f"copy:{frame.f_code.co_name}[{value_type.__name__}]"] += 1

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        result = operation()
    finally:
        sys.setprofile(previous)
    groups = {
        "node_clones": ("ea_node_editor.graph.records:NodeInstance.clone",),
        "edge_clones": ("ea_node_editor.graph.records:EdgeInstance.clone",),
        "workspace_clones": ("ea_node_editor.graph.workspace_state:WorkspaceData.clone",),
        "project_clones": ("ea_node_editor.graph.project_state:ProjectData.clone",),
        "workspace_snapshots": ("ea_node_editor.graph.workspace_state:WorkspaceSnapshot.capture",),
        "node_copies": ("copy:copy[NodeInstance]", "copy:deepcopy[NodeInstance]"),
        "edge_copies": ("copy:copy[EdgeInstance]", "copy:deepcopy[EdgeInstance]"),
        "workspace_copies": ("copy:copy[WorkspaceData]", "copy:deepcopy[WorkspaceData]"),
        "project_copies": ("copy:copy[ProjectData]", "copy:deepcopy[ProjectData]"),
        "registry_resolutions": ("ea_node_editor.nodes.registry:NodeRegistry.resolve_spec",),
        "effective_port_materializations": ("ea_node_editor.graph.effective_ports:effective_ports",),
        "kernel_port_lookups": ("ea_node_editor.graph.invariant_kernel:GraphInvariantKernel._effective_ports_for",
                                "ea_node_editor.graph.invariant_kernel:GraphInvariantKernel.effective_ports_for"),
        "pruning_passes": ("ea_node_editor.graph.invariant_kernel:GraphInvariantKernel.prunable_edge_ids",),
        "downstream_passes": ("ea_node_editor.graph.invariant_kernel:GraphInvariantKernel.downstream_nodes",),
        "script_apply": ("ea_node_editor.graph.validated_mutation:ValidatedGraphMutation.apply_python_script",),
    }
    return result, {name: sum(raw[key] for key in keys) for name, keys in groups.items()}, dict(sorted(raw.items()))


def run(args):
    source, output = args.source_root.resolve(), args.output.resolve()
    work = (args.work_dir or output.with_suffix(".work")).resolve()
    _configure(source, work)
    results, fixture_hashes = {}, {}
    for node_count in args.nodes:
        registry, seed = build_fixture(node_count)
        fixture_hashes[str(node_count)] = _digest(asdict(seed))
        for name in args.scenarios:
            operation, inspect = prepare_operation(registry, seed, name)
            inspect(operation())  # Prime resolver/spec caches outside measured work.
            key = f"{node_count}.{name}"
            if args.mode == "instrumented":
                operation, inspect = prepare_operation(registry, seed, name)
                result, counts, raw = _instrument(operation)
                results[key] = {"semantic": inspect(result), "counts": counts, "raw_events": raw}
                continue
            samples, fingerprints = [], set()
            for index in range(args.warmups + args.iterations):
                operation, inspect = prepare_operation(registry, seed, name)
                started = time.perf_counter_ns()
                result = operation()
                elapsed = (time.perf_counter_ns() - started) / 1_000_000
                if index >= args.warmups:
                    samples.append(elapsed)
                summary = inspect(result)
                fingerprints.add(summary["fingerprint"])
            if len(fingerprints) != 1:
                raise AssertionError(f"Nondeterministic fixture results: {key}")
            results[key] = {"samples_ms": samples, "median_ms": statistics.median(samples),
                            "p95_ms": statistics.quantiles(samples, n=20, method="inclusive")[18] if len(samples) > 1 else samples[0],
                            "semantic": summary}
    report = {"schema_version": 1, "benchmark": "graph_node_reconciliation", "mode": args.mode,
              "source_root": str(source), "source_origins": _origins(source),
              "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "environment": {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
                              "machine": platform.machine()},
              "configuration": {"nodes": args.nodes, "local_edges": 3, "warmups": args.warmups,
                                "iterations": args.iterations, "scenarios": args.scenarios},
              "fixture_hashes": fixture_hashes, "fixture_hash": _digest(fixture_hashes), "results": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"output": str(output), "fixture_hash": report["fixture_hash"], "scenarios": list(results)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--mode", choices=("timing", "instrumented"), default="timing")
    parser.add_argument("--nodes", type=int, nargs="+", default=[100, 1200])
    parser.add_argument("--scenarios", nargs="+", choices=OPERATIONS, default=list(OPERATIONS))
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=50)
    args = parser.parse_args()
    if min(args.nodes) < 4 or args.iterations < 1 or args.warmups < 0:
        parser.error("At least four nodes, one iteration, and nonnegative warmups are required")
    run(args)


if __name__ == "__main__":
    main()
