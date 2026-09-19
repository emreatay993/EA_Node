# Purpose: Compare isolated navigation commands against frozen, parent-only evaluation labels.
# Map: subsystems/verification_testing_docs_hygiene.md
# Tests: tests/test_nav_assist_evaluation.py
"""Evaluate the complete frozen corpus, or explicitly opt into a development run.

Example: python -m scripts.evaluate_nav_assist --corpus tests/fixtures/nav_assist_evaluation.json
         --output artifacts/nav_assist/qualification.json --include-trace

Only the parent reads labels. Every arm/case starts a new interpreter; its stdin
contains only the query, repository root and arm. No client or inventory is shared.
"""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import subprocess
import sys
from time import perf_counter

from scripts import nav, nav_assist
from scripts.nav_assist_inventory import ExactMatch, _safe_path, build_inventory
from scripts.nav_assist_selection import evidence_record, owner_probability, safe_value

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_SHA256 = "ba480dbd158e0c5926ea569145b2d45426d5dc71cddfdb408e6528a4f9245e97"
FROZEN_COUNTS = {"backend": 6, "ui": 6, "multiple_owners": 4, "exact": 2, "no_match": 2}
ARMS = ("baseline", "pilot")
MAX_WORKER_BYTES = 8_000_000
IDENTITY_PATHS = (
    "scripts/evaluate_nav_assist.py", "scripts/nav.py", "scripts/nav_assist.py",
    "scripts/nav_assist_client.py", "scripts/nav_assist_inventory.py",
    "scripts/nav_assist_selection.py", "scripts/generate_agent_route_index.py",
    "scripts/generate_qml_navigation_index.py", "scripts/generate_source_test_file_index.py",
    "docs/agent_route_index.json", "docs/qml_navigation_index.json", "docs/source_test_file_index.md",
)
# Fixed code, never interpolated query text. -I ignores PYTHONPATH/user site while
# retaining TYPESAFE_API_KEY in the inherited environment. No shell is involved.
WORKER_CODE = (
    "import sys; sys.path.insert(0, sys.argv[1]); "
    "from scripts.evaluate_nav_assist import worker_main; raise SystemExit(worker_main())"
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _relative_path(value) -> bool:
    return (isinstance(value, str) and bool(value) and "\\" not in value and ":" not in value
            and not PurePosixPath(value).is_absolute() and ".." not in PurePosixPath(value).parts
            and str(PurePosixPath(value)) == value)


def load_corpus(path: Path, *, development: bool = False) -> dict:
    """Validate structure and, for qualification, the exact frozen bytes."""
    path = Path(path).resolve()
    raw = path.read_bytes()
    data = json.loads(raw)
    # Check every decoded leaf, including unknown metadata and object keys, before
    # dropping fields or letting JSON escaping disguise credential characters.
    if not safe_value(data):
        raise ValueError("unsafe_corpus")
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("corpus_schema")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("corpus_cases")
    seen = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("corpus_case")
        identity, group, query = (case.get(key) for key in ("id", "group", "query"))
        if (not isinstance(identity, str) or not identity or identity in seen
                or not isinstance(group, str) or not group or not isinstance(query, str)
                or not query.strip() or len(query) > nav_assist.MAX_QUERY_CHARS):
            raise ValueError("corpus_identity_or_query")
        seen.add(identity)
        for key in ("source_groups", "test_groups"):
            groups = case.get(key)
            if not isinstance(groups, list) or len(groups) > 3:
                raise ValueError("corpus_groups")
            if bool(groups) == (group == "no_match"):
                raise ValueError("corpus_actionable_groups")
            if any(not isinstance(options, list) or not options
                   or len(options) != len(set(option for option in options if isinstance(option, str)))
                   or not all(_relative_path(option) for option in options) for options in groups):
                raise ValueError("corpus_group_paths")
    counts = dict(Counter(case["group"] for case in cases))
    digest = sha256(raw)
    if not development and (digest != FROZEN_SHA256 or counts != FROZEN_COUNTS or len(cases) != 20):
        raise ValueError("qualification_requires_unchanged_frozen_20_case_corpus")
    return {"path": str(path), "sha256": digest, "development": development,
            "counts": counts, "cases": cases}


def exact_preflight(query: str, inventory) -> ExactMatch:
    """Mirror run's whole-query guard; URI fragments inside prose stay semantic."""
    query = query.strip()
    whole = query.strip("`\"'")
    if (not any(char.isspace() for char in whole) or Path(whole).is_absolute()
            or whole in inventory.candidates):
        return inventory.resolve_exact(query)
    return ExactMatch("not_exact")


class _NoModel:
    def evaluate(self, state, questions):
        raise RuntimeError("baseline_attempted_model_call")


def run_baseline(query: str, root: Path) -> dict:
    """Use identical exact results or the incumbent's bounded default find output.

    Live evidence is attached only to paths actually emitted by nav.find. It does
    not use the pilot's retrieval/selection for prose or expand hidden route paths.
    """
    inventory = build_inventory(root)
    if exact_preflight(query, inventory).status != "not_exact":
        return nav_assist.run(query, root=root, inventory=inventory, client=_NoModel())
    output = io.StringIO()
    args = argparse.Namespace(query=query, limit=5, expand=False, json=True)
    with contextlib.redirect_stdout(output):
        nav.cmd_find(args, root)
    incumbent = json.loads(output.getvalue())
    owners = incumbent["owners"]
    sources = list(dict.fromkeys(item["path"] for item in owners if item.get("path")))[:3]
    tests = list(dict.fromkeys(item["focused_test"] for item in owners if item.get("focused_test")))[:3]
    result = nav_assist._base(query)
    result.update(status="ok" if sources or tests else "unresolved" if owners else "no_match", mode="incumbent")
    for key, paths in (("sources", sources), ("tests", tests)):
        for path in paths:
            if path in inventory.candidates:
                evidence = inventory.evidence(path, query=query, max_lines=24, max_chars=2600)
                record = evidence_record(evidence, query)
                if not safe_value(record):
                    raise ValueError("unsafe_baseline_evidence")
                result[key].append(record)
            else:
                # Keep an invalid emitted path as a failure, never silently drop it.
                result[key].append({"path": path, "sha256": None, "excerpt": []})
    result["diagnostics"] = {"baseline": "nav.find default owner capsules; limit=5; expand=False",
                             "inventory_sha256": sha256("\n".join(
                                 path + ":" + item.content_sha256
                                 for path, item in inventory.candidates.items()).encode())}
    result["trace"] = {"inventory": list(inventory.candidates),
                       "stages": {"incumbent": {"candidates": sources + tests, "scores": {}}}}
    return result


def worker_payload(query: str, root: Path, arm: str) -> dict:
    """Worker boundary deliberately accepts no case, groups, corpus or gold data."""
    result = (nav_assist.run(query, root=root, include_trace=True)
              if arm == "pilot" else run_baseline(query, root))
    rendered = nav_assist.render_json(result)
    return {"pack": json.loads(rendered), "rendered_chars": len(rendered),
            "selected_paths": {key: [item["path"] for item in result[key]] for key in ("sources", "tests")},
            "diagnostics": result.get("diagnostics", {}), "trace": result.get("trace")}


def worker_main() -> int:
    try:
        request = json.loads(sys.stdin.read(16_384))
        if (set(request) != {"query", "root", "arm"} or request["arm"] not in ARMS
                or not isinstance(request["query"], str) or not isinstance(request["root"], str)):
            raise ValueError("worker_input")
        # Suppress accidental library prints as well as raw exception text.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            response = worker_payload(request["query"], Path(request["root"]), request["arm"])
        print(json.dumps(response, ensure_ascii=True, separators=(",", ":")))
        return 0
    except Exception:
        print('{"worker_error":"worker_failed"}')
        return 1


def run_isolated(query: str, root: Path, arm: str, *, timeout: float = 60.0) -> dict:
    """Measure process creation through process exit, including JSON formatting."""
    command = [sys.executable, "-I", "-c", WORKER_CODE, str(REPO_ROOT)]
    request = json.dumps({"query": query, "root": str(root), "arm": arm}, ensure_ascii=True)
    started = perf_counter()
    result = {"outcome": "error", "error_code": None, "pack": None, "trace": None,
              "selected_paths": {}, "diagnostics": {}, "rendered_chars": None}
    try:
        child = subprocess.run(command, input=request.encode(), stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, cwd=REPO_ROOT, timeout=timeout, check=False)
        if child.returncode:
            result["error_code"] = "worker_exit"
        elif len(child.stdout) > MAX_WORKER_BYTES:
            result["error_code"] = "worker_output_limit"
        else:
            envelope = json.loads(child.stdout)
            pack = envelope["pack"]
            length = len(json.dumps(pack, ensure_ascii=True, separators=(",", ":")))
            if (not isinstance(pack, dict) or length > nav_assist.MAX_JSON_CHARS
                    or "trace" in pack or envelope["rendered_chars"] != length
                    or not all(isinstance(pack.get(key), list) for key in ("sources", "tests"))):
                raise ValueError("invalid_worker_pack")
            result.update({key: envelope.get(key) for key in (
                "pack", "trace", "selected_paths", "diagnostics", "rendered_chars")})
            result["outcome"] = "completed"
    except subprocess.TimeoutExpired:
        result.update(outcome="timeout", error_code="command_timeout")
    except (OSError, ValueError, KeyError, TypeError):
        result["error_code"] = "worker_protocol_or_launch"
    finally:
        result["wall_seconds"] = round(perf_counter() - started, 6)
    return result


def validate_candidate(record: dict, root: Path) -> dict:
    """Check the displayed hash and every numbered line against current file bytes."""
    path = record.get("path") if isinstance(record, dict) else None
    result = {"path": path, "path_valid": False, "sha256_valid": False,
              "excerpt_valid": False, "valid": False, "current_sha256": None}
    if not _relative_path(path):
        return result
    try:
        live = _safe_path(root, path)
        if live is None:
            return result
        result["path_valid"] = True
        raw = live.read_bytes()
        result["current_sha256"] = sha256(raw)
        result["sha256_valid"] = record.get("sha256") == result["current_sha256"]
        lines = raw.decode("utf-8-sig").splitlines()
        excerpt = record.get("excerpt")
        numbers = []
        if not isinstance(excerpt, list) or not excerpt:
            return result
        for item in excerpt:
            if not isinstance(item, dict):
                return result
            number = item.get("line")
            if (type(number) is not int or not 1 <= number <= len(lines)
                    or not isinstance(item.get("text"), str) or lines[number - 1] != item["text"]):
                return result
            numbers.append(number)
        result["excerpt_valid"] = numbers == sorted(set(numbers))
        result["valid"] = all(result[key] for key in ("path_valid", "sha256_valid", "excerpt_valid"))
    except (OSError, UnicodeError, ValueError):
        pass
    return result


def group_coverage(groups: list[list[str]], predicted: list[str]) -> dict:
    predictions = set(predicted)
    matches = [sorted(predictions.intersection(options)) for options in groups]
    return {"expected_groups": groups, "predicted_paths": predicted, "matched_groups": matches,
            "covered_groups": sum(bool(match) for match in matches), "required_groups": len(groups),
            "complete": bool(groups) and all(matches)}


def _owner_category(score) -> bool:
    if not isinstance(score, dict) or not isinstance(score.get("probabilities"), dict):
        return False
    probabilities = score["probabilities"]
    if (set(probabilities) != {"0", "1", "2", "3"}
            or any(type(value) not in {int, float} or not 0 <= value <= 1
                   or not math.isfinite(value) for value in probabilities.values())):
        return False
    try:
        return owner_probability(score) > 0.5
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        return False


def candidate_loss(groups: list[list[str]], displayed: list[str], execution: dict, key: str) -> list[dict]:
    """Gold is consulted here, after the worker has exited, never for inference."""
    trace = execution.get("trace") or {}
    stages = trace.get("stages", {})
    initial = stages.get("initial", {})
    rich = stages.get("rich", {})
    pack = execution.get("pack") or {}
    selected = (execution.get("selected_paths") or {}).get(key, [])
    rows = []
    for group in groups:
        alternatives = []
        for path in group:
            if path in displayed:
                stage = "displayed"
            elif execution.get("outcome") != "completed":
                stage = "command_failure_or_not_run"
            elif pack.get("status") == "stale":
                stage = "stale_evidence"
            elif pack.get("status") == "unavailable":
                stage = "selection_unavailable"
            elif path in selected:
                stage = "rendered_output_cap"
            elif pack.get("mode") == "exact":
                stage = "exact_preflight_or_association"
            elif not trace:
                stage = "trace_unavailable"
            elif path not in trace.get("inventory", []):
                stage = "inventory"
            elif "incumbent" in stages:
                stage = "incumbent_navigation"
            elif pack.get("status") == "no_match":
                stage = "task_scope_rejection"
            elif path not in rich.get("candidates", []):
                stage = ("rich_evidence_selection" if path in initial.get("candidates", [])
                         else "local_retrieval_and_route_rescue")
            elif path not in rich.get("scores", {}):
                stage = "rich_scoring_incomplete"
            elif not _owner_category(rich["scores"][path]):
                stage = "relevance_category"
            else:
                stage = "final_three_candidate_cap"
            alternatives.append({"path": path, "stage": stage,
                                 "initial_candidate": path in initial.get("candidates", []),
                                 "rich_candidate": path in rich.get("candidates", [])})
        rows.append({"expected_group": group, "covered": bool(set(group).intersection(displayed)),
                     "alternatives": alternatives})
    return rows


def grade_case(case: dict, execution: dict, root: Path) -> dict:
    pack = execution.get("pack") or {}
    completed = execution.get("outcome") == "completed"
    grade = {"source_pass": False, "test_pass": False, "no_match_pass": None,
             "exact_bypass_pass": None, "evidence_valid": completed, "coverage": {},
             "validity": {}, "candidate_loss": {}}
    for key, gold_key, pass_key in (("sources", "source_groups", "source_pass"),
                                    ("tests", "test_groups", "test_pass")):
        records = pack.get(key, [])
        if not isinstance(records, list):
            records = []
            grade["evidence_valid"] = False
        # Only three visible entries can contribute; a protocol violation fails evidence.
        if len(records) > 3:
            grade["evidence_valid"] = False
        displayed = records[:3]
        paths = [item["path"] for item in displayed if isinstance(item, dict) and isinstance(item.get("path"), str)]
        validity = [validate_candidate(item, root) for item in displayed]
        grade["validity"][key] = validity
        valid_paths = [item["path"] for item in validity if item["valid"]]
        coverage = group_coverage(case[gold_key], paths)
        coverage["valid_evidence_complete"] = group_coverage(case[gold_key], valid_paths)["complete"]
        grade["coverage"][key] = coverage
        grade[pass_key] = completed and pack.get("status") == "ok" and coverage["valid_evidence_complete"]
        grade["evidence_valid"] &= all(item["valid"] for item in validity)
        grade["candidate_loss"][key] = candidate_loss(case[gold_key], paths, execution, key)
    if case["group"] == "no_match":
        grade["no_match_pass"] = (completed and pack.get("status") == "no_match"
                                  and not pack.get("sources") and not pack.get("tests"))
    if case["group"] == "exact":
        usage = pack.get("usage") or {}
        grade["exact_bypass_pass"] = (completed and pack.get("status") == "ok" and pack.get("mode") == "exact"
                                      and type(usage.get("attempted_requests")) is int
                                      and usage["attempted_requests"] == 0
                                      and usage.get("requests") == 0 and pack.get("model") is None)
    return grade


def nearest_rank_p95(values: list[float]) -> float | None:
    if not values:
        return None
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("invalid_latency")
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]


def summarize(corpus: dict, rows: list[dict], *, identities_stable: bool, corpus_unchanged: bool) -> dict:
    expected_ids = [case["id"] for case in corpus["cases"]]
    whole = len(rows) == len(expected_ids) and {row["id"] for row in rows} == set(expected_ids)
    summaries = {}
    for arm in ARMS:
        results = [row[arm] for row in rows]
        actionable = [row[arm] for row in rows if row["group"] != "no_match"]
        negatives = [row[arm] for row in rows if row["group"] == "no_match"]
        exact = [row[arm] for row in rows if row["group"] == "exact"]
        walls = [result["wall_seconds"] for result in results if result.get("wall_seconds") is not None]
        usage = Counter()
        unknown_usage = 0
        failed_requests = 0
        for result in results:
            pack_usage = (result.get("pack") or {}).get("usage")
            if not isinstance(pack_usage, dict):
                unknown_usage += 1
                continue
            for key in ("requests", "attempted_requests", "input_tokens", "output_tokens"):
                value = pack_usage.get(key)
                if type(value) is int and value >= 0:
                    usage[key] += value
            failed_requests += max(0, pack_usage.get("attempted_requests", 0) - pack_usage.get("requests", 0))
        summaries[arm] = {
            "source_passes": sum(result["grade"]["source_pass"] for result in actionable),
            "test_passes": sum(result["grade"]["test_pass"] for result in actionable),
            "actionable_denominator": len(actionable),
            "no_match_passes": sum(result["grade"]["no_match_pass"] is True for result in negatives),
            "no_match_denominator": len(negatives),
            "exact_bypass_passes": sum(result["grade"]["exact_bypass_pass"] is True for result in exact),
            "exact_denominator": len(exact),
            "all_evidence_valid": all(result["grade"]["evidence_valid"] for result in results),
            "completed_commands": sum(result["outcome"] == "completed" for result in results),
            "command_failures": sum(result["outcome"] in {"error", "timeout"} for result in results),
            "not_run": sum(result["outcome"] == "not_run" for result in results),
            "p95_wall_seconds": nearest_rank_p95(walls), "latency_samples": len(walls),
            "usage": dict(usage), "unknown_usage_cases": unknown_usage,
            "failed_requests_with_unknown_tokens": failed_requests,
            "models": sorted({result["pack"]["model"] for result in results
                              if result.get("pack") and result["pack"].get("model")}),
        }
    pilot = summaries["pilot"]
    inventory_identities = sorted({result.get("diagnostics", {}).get("inventory_sha256")
                                   for row in rows for result in (row[arm] for arm in ARMS)
                                   if (result.get("diagnostics") or {}).get("inventory_sha256")})
    gates = {
        "whole_frozen_corpus": (whole and not corpus["development"] and corpus["sha256"] == FROZEN_SHA256
                                and corpus["counts"] == FROZEN_COUNTS and corpus_unchanged),
        "all_commands_completed": whole and all(value["completed_commands"] == 20 for value in summaries.values()),
        "source_17_of_18": pilot["actionable_denominator"] == 18 and pilot["source_passes"] >= 17,
        "tests_15_of_18": pilot["actionable_denominator"] == 18 and pilot["test_passes"] >= 15,
        "both_no_matches": pilot["no_match_denominator"] == 2 and pilot["no_match_passes"] == 2,
        "valid_paths_hashes_and_excerpts": pilot["all_evidence_valid"],
        "exact_zero_attempted_api": pilot["exact_denominator"] == 2 and pilot["exact_bypass_passes"] == 2,
        "uncached_p95_below_10_seconds": (pilot["latency_samples"] == 20
                                          and pilot["p95_wall_seconds"] is not None
                                          and pilot["p95_wall_seconds"] < 10.0),
        "source_identity_stable": identities_stable and len(inventory_identities) == 1,
    }
    complete = whole and all(value["not_run"] == 0 for value in summaries.values())
    return {"arms": summaries, "gates": gates, "qualified": all(gates.values()),
            "run_kind": "development" if corpus["development"] else "qualification",
            "complete_corpus": complete, "corpus_unchanged": corpus_unchanged,
            "case_count": len(rows), "corpus_case_count": len(expected_ids),
            "inventory_identities": inventory_identities}


def source_identity(root: Path) -> dict:
    manifest = {path: sha256((root / path).read_bytes()) if (root / path).is_file() else None
                for path in IDENTITY_PATHS}
    try:
        process = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, timeout=10)
        head = process.stdout.decode().strip() if process.returncode == 0 else None
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        head = None
    return {"git_head": head, "files": manifest,
            "sha256": sha256(json.dumps(manifest, sort_keys=True).encode())}


def evaluate(corpus: dict, *, root: Path = REPO_ROOT, timeout: float = 60.0,
             include_trace: bool = False, case_ids: list[str] | None = None) -> dict:
    """Run both arms sequentially and retain errors, timeouts and unrun cases."""
    root = Path(root).resolve()
    if not safe_value(corpus):
        raise ValueError("unsafe_corpus")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("invalid_timeout")
    if case_ids and not corpus["development"]:
        raise ValueError("subsets_require_development")
    known = {case["id"] for case in corpus["cases"]}
    if case_ids and not set(case_ids).issubset(known):
        raise ValueError("unknown_case_id")
    cases = [case for case in corpus["cases"] if not case_ids or case["id"] in case_ids]
    before = source_identity(root)
    rows = [{"id": case["id"], "group": case["group"], "query": case["query"],
             "expected": {key: case[key] for key in ("source_groups", "test_groups")},
             **{arm: {"outcome": "not_run", "error_code": None, "wall_seconds": None, "pack": None}
                for arm in ARMS}} for case in cases]
    interrupted = False
    try:
        for case, row in zip(cases, rows):
            for arm in ARMS:
                row[arm] = run_isolated(case["query"], root, arm, timeout=timeout)
    except KeyboardInterrupt:
        interrupted = True
    # No expected label reaches either child. Grade only after inference is over.
    for case, row in zip(cases, rows):
        for arm in ARMS:
            row[arm]["grade"] = grade_case(case, row[arm], root)
            pack = row[arm].get("pack") or {}
            row[arm]["model_observation"] = {
                "reported_model": pack.get("model"),
                "validated_response_model": pack.get("model") if (pack.get("usage") or {}).get("requests", 0) > 0 else None,
            }
            if not include_trace:
                row[arm].pop("trace", None)
    after = source_identity(root)
    try:
        unchanged = sha256(Path(corpus["path"]).read_bytes()) == corpus["sha256"]
    except OSError:
        unchanged = False
    report = {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
              "root": str(root), "corpus": {key: value for key, value in corpus.items() if key != "cases"},
              "source_identity_before": before, "source_identity_after": after,
              "protocol": {"fresh_process_per_arm_and_case": True, "shared_inventory": False,
                           "answer_cache": False, "latency": "process creation through exit including formatting",
                           "percentile": "nearest rank ceil(0.95 * n)", "timeout_seconds": timeout,
                           "graded_output": "render_json, 24000 characters, at most 3 sources and 3 tests",
                           "labels": "parent only; candidate-loss analysis after all inference",
                           "baseline": "identical whole-query exact preflight; otherwise nav.find default capsules"},
              "interrupted": interrupted, "cases": rows}
    report["summary"] = summarize(corpus, rows, identities_stable=before == after, corpus_unchanged=unchanged)
    if not safe_value(report):
        raise ValueError("unsafe_report")
    return report


def render_report(report: dict) -> str:
    """Reject sensitive raw leaves before any report bytes reach disk or stdout."""
    if not safe_value(report):
        raise ValueError("unsafe_report")
    return json.dumps(report, ensure_ascii=True, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new JSON report path; existing files are never overwritten")
    parser.add_argument("--development", action="store_true", help="non-qualifying development corpus/run")
    parser.add_argument("--case", dest="case_ids", action="append", help="case ID subset; only with --development")
    parser.add_argument("--include-trace", action="store_true", help="retain full local trace in addition to loss analysis")
    parser.add_argument("--timeout", type=float, default=60.0, help="maximum wall seconds per child (default: 60)")
    args = parser.parse_args(argv)
    try:
        if args.case_ids and not args.development:
            raise ValueError("subsets_require_development")
        output = args.output.resolve()
        if not safe_value({"output": str(output), "corpus": str(args.corpus), "case_ids": args.case_ids}):
            raise ValueError("unsafe_output_or_arguments")
        if output.suffix.lower() != ".json" or output.exists() or output == args.corpus.resolve():
            raise ValueError("output_must_be_new_json_file")
        corpus = load_corpus(args.corpus, development=args.development)
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise ValueError("invalid_timeout")
        # Reserve exclusively before spending API calls; no source/corpus overwrite.
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            report = evaluate(corpus, timeout=args.timeout, include_trace=args.include_trace, case_ids=args.case_ids)
            handle.write(render_report(report))
        print(json.dumps({"output": str(output), "summary": report["summary"]}, ensure_ascii=True))
        return 0 if report["summary"]["qualified"] or args.development and report["summary"]["complete_corpus"] else 1
    except (OSError, ValueError, TypeError):
        # Do not expose exception text, service bodies, environment or credentials.
        print("Evaluation setup/report failed; check corpus identity, options and a new writable JSON output path.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
