# Purpose: Check ownership benchmark source isolation and graph counter integrity.
# Map: subsystems/graph_domain.md
# Tests: tests/test_plot_graph_ownership_benchmarks.py
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import benchmark_graph_node_reconciliation as graph_benchmark
from scripts import benchmark_generic_plot as plot_benchmark

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script", ["benchmark_generic_plot.py", "benchmark_graph_node_reconciliation.py"])
def test_invalid_source_root_fails_instead_of_using_editable_install(tmp_path, script):
    output = tmp_path / "result.json"
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), "--source-root", str(tmp_path),
                             "--output", str(output)], cwd=tmp_path, text=True, capture_output=True, timeout=30)
    assert result.returncode != 0
    assert "Not a COREX source root" in result.stderr
    assert not output.exists()
    assert not output.with_suffix(".work").exists()


def test_graph_benchmark_selects_source_before_import_and_matches_fingerprints(tmp_path):
    reports = []
    for mode in ("instrumented", "timing"):
        output = tmp_path / f"{mode}.json"
        command = [sys.executable, str(ROOT / "scripts/benchmark_graph_node_reconciliation.py"),
                   "--source-root", str(ROOT), "--output", str(output), "--mode", mode,
                   "--nodes", "8", "--warmups", "0", "--iterations", "2"]
        result = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True, timeout=60)
        assert result.returncode == 0, result.stderr
        report = json.loads(output.read_text(encoding="utf-8"))
        assert report["source_origins"]
        assert all(Path(path).resolve().is_relative_to(ROOT) for path in report["source_origins"].values())
        assert report["configuration"]["local_edges"] == 3
        reports.append(report)
    counted, timed = reports
    assert counted["fixture_hash"] == timed["fixture_hash"]
    assert set(counted["results"]) == {f"8.{name}" for name in graph_benchmark.OPERATIONS}
    for key, measured in timed["results"].items():
        assert len(measured["samples_ms"]) == 2
        assert "counts" not in measured
        assert "samples_ms" not in counted["results"][key]
        assert measured["semantic"]["fingerprint"] == counted["results"][key]["semantic"]["fingerprint"]
    counts = counted["results"]["8.script_apply"]["counts"]
    assert counts["node_clones"] == counts["node_copies"] == 1
    assert counts["workspace_snapshots"] == counts["project_copies"] == counts["workspace_copies"] == 0
    assert counted["results"]["8.dynamic_remove"]["semantic"]["return_value"] == ["alpha", ["to_dynamic"]]


def test_graph_instrumentation_observes_whole_graph_copies_and_restores_profiler(tmp_path):
    registry, project = graph_benchmark.build_fixture(8, generation_root=tmp_path / "plugin_generations")
    prior = sys.getprofile()
    _, counts, events = graph_benchmark._instrument(lambda: copy.deepcopy(project))
    assert sys.getprofile() is prior
    assert counts["project_copies"] == 1
    assert counts["workspace_copies"] == 1
    assert counts["node_copies"] == 8
    assert counts["edge_copies"] == 3
    assert events["copy:deepcopy[ProjectData]"] == 1
    # Fixture reset is excluded from the operation's graph-copy counters.
    operation, inspect = graph_benchmark.prepare_operation(registry, project, "property")
    result, counts, _ = graph_benchmark._instrument(operation)
    assert counts["project_copies"] == counts["workspace_copies"] == counts["node_copies"] == 0
    assert inspect(result)["changed_nodes"]["dynamic"]["properties"]["mode"] == "after"


@pytest.mark.parametrize("benchmark", [plot_benchmark, graph_benchmark], ids=["plot", "graph"])
@pytest.mark.parametrize("namespace", ["ea_node_editor", "corex"])
@pytest.mark.parametrize("location", ["outside_checkout", "nested_checkout", "venv"])
def test_source_origin_validation_rejects_foreign_application_modules(
    tmp_path, monkeypatch, benchmark, namespace, location,
):
    from types import SimpleNamespace

    foreign_roots = {
        "outside_checkout": tmp_path,
        "nested_checkout": ROOT / "artifacts" / "plot_graph_refactor" / "baseline_source",
        "venv": ROOT / "venv" / "Lib" / "site-packages",
    }
    path = foreign_roots[location] / namespace / "_foreign_benchmark_probe.py"
    monkeypatch.setitem(
        sys.modules, f"{namespace}._foreign_benchmark_probe", SimpleNamespace(__file__=str(path)),
    )
    with pytest.raises(RuntimeError, match="escaped selected source"):
        benchmark._origins(ROOT)


@pytest.mark.parametrize("benchmark", [plot_benchmark, graph_benchmark], ids=["plot", "graph"])
@pytest.mark.parametrize("namespace", ["ea_node_editor", "corex"])
def test_source_origin_validation_accepts_modules_in_selected_package(monkeypatch, benchmark, namespace):
    from types import SimpleNamespace

    name = f"{namespace}._selected_benchmark_probe"
    path = ROOT / namespace / "_selected_benchmark_probe.py"
    monkeypatch.setitem(sys.modules, name, SimpleNamespace(__file__=str(path)))

    origins = benchmark._origins(ROOT)

    assert origins[name] == str(path.resolve())
    assert all(Path(path).is_relative_to(ROOT / name.split(".", 1)[0]) for name, path in origins.items())


def test_plot_benchmark_retains_provenance_read_bounds_and_full_exports(tmp_path):
    reports = []
    for mode in ("instrumented", "timing"):
        output = tmp_path / f"plot_{mode}.json"
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/benchmark_generic_plot.py"), "--source-root", str(ROOT),
             "--output", str(output), "--mode", mode, "--rows", "64", "--export-rows", "32",
             "--warmups", "0", "--iterations", "2", "--export-warmups", "0", "--export-iterations", "2"],
            cwd=tmp_path, text=True, capture_output=True, timeout=90,
        )
        assert result.returncode == 0, result.stderr
        reports.append(json.loads(output.read_text(encoding="utf-8")))
    counted, timed = reports
    assert counted["fixture_hash"] == timed["fixture_hash"]
    assert set(counted["configuration"]["scenario_node_types"].values()) == {"plot.bar", "plot.heatmap"}
    assert all(Path(path).resolve().is_relative_to(ROOT) for path in counted["source_origins"].values())
    for key, measured in timed["results"].items():
        assert len(measured["samples_ms"]) == 2
        assert measured["semantic"]["fingerprint"] == counted["results"][key]["semantic"]["fingerprint"]
    results = counted["results"]
    assert results["table"]["counts"]["loader.column_arrays"] == 1
    assert "columns" not in results["table"]["semantic"]["series"][0]["source_ref"]
    assert results["window"]["semantic"]["series"][0]["source_ref"]["columns"] == ["time", "signal", "other"]
    assert results["array"]["counts"]["loader.sample_array"] == 1
    assert "loader.slice_2d" not in results["array"]["counts"]
    assert results["slice"]["counts"]["loader.slice_2d"] == 1
    assert results["export_table"]["semantic"]["rows"] == results["export_array"]["semantic"]["rows"] == 32
    assert results["export_table"]["semantic"]["columns"] == ["time", "signal", "other"]
    assert len(results["export_array"]["semantic"]["columns"]) == 8


def test_plot_timing_rejects_inconsistent_semantics_and_aliases_only_known_identities():
    def prepare(index):
        return lambda: index, lambda value: {"fingerprint": str(value)}
    with pytest.raises(AssertionError, match="Nondeterministic"):
        plot_benchmark._measure(prepare, warmups=0, iterations=2)
    aliases = {"known-ref": "fixture:table", "file:///known.csv": "fixture:table:uri"}
    assert plot_benchmark._canonical({"ref_id": "known-ref", "source_uri": "file:///known.csv", "columns": ["other"],
                                      "unrecognized": "other-ref"}, aliases) == {
        "ref_id": "fixture:table", "source_uri": "fixture:table:uri", "columns": ["other"], "unrecognized": "other-ref",
    }
