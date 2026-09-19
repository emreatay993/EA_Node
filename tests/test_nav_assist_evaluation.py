# Purpose: Prove frozen-corpus grading, command isolation and qualification without API calls.
# Map: subsystems/verification_testing_docs_hygiene.md
# Tests: tests/test_nav_assist_evaluation.py
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

from scripts import evaluate_nav_assist as evaluator
from scripts import nav_assist
from scripts.nav_assist_inventory import ExactMatch, build_inventory
from tests.test_nav_assist_inventory import InventoryFixture


def case(identity="sample", group="backend", sources=None, tests=None):
    return {"id": identity, "group": group, "query": "Inspect the synthetic owner behavior",
            "source_groups": sources if sources is not None else [["ea_node_editor/owner.py"]],
            "test_groups": tests if tests is not None else [["tests/test_owner.py"]]}


def corpus_for(cases, path="unused.json", *, development=True):
    return {"cases": cases, "path": str(path), "sha256": "development", "development": development,
            "counts": dict(evaluator.Counter(item["group"] for item in cases))}


class EvaluationTests(InventoryFixture):
    def setUp(self):
        super().setUp()
        # Any accidental model construction fails this suite without network access.
        self.client_block = patch.object(nav_assist, "TypeSafeClient", side_effect=AssertionError("offline test"))
        self.client_block.start()
        self.addCleanup(self.client_block.stop)
        self.source = "ea_node_editor/owner.py"
        self.other = "ea_node_editor/other.py"
        self.test = "tests/test_owner.py"
        self.write(self.source, "# Purpose: Own the synthetic behavior.\n# Tests: tests/test_owner.py\ndef unique_owner():\n    return 1\n")
        self.write(self.other, "def other_owner():\n    return 2\n")
        self.write(self.test, "from ea_node_editor.owner import unique_owner\ndef test_owner():\n    assert unique_owner() == 1\n")

    def evidence(self, path):
        raw = (self.root / path).read_bytes()
        return {"path": path, "sha256": evaluator.sha256(raw),
                "excerpt": [{"line": number, "text": text}
                            for number, text in enumerate(raw.decode().splitlines(), 1)]}

    def execution(self, *, sources=None, tests=None, status="ok", mode="semantic", outcome="completed"):
        pack = nav_assist._base("synthetic query")
        pack.update(status=status, mode=mode,
                    sources=[self.evidence(path) for path in (sources if sources is not None else [self.source])],
                    tests=[self.evidence(path) for path in (tests if tests is not None else [self.test])])
        return {"pack": pack, "outcome": outcome, "wall_seconds": 0.8, "trace": None,
                "diagnostics": {"inventory_sha256": "synthetic-stable-inventory"},
                "selected_paths": {key: [item["path"] for item in pack[key]] for key in ("sources", "tests")}}

    def test_all_owner_groups_required_with_alternative_exact_paths(self):
        expected = [[self.source, "ea_node_editor/equivalent.py"], [self.other]]
        incomplete = evaluator.group_coverage(expected, [self.source])
        self.assertFalse(incomplete["complete"])
        self.assertEqual(incomplete["covered_groups"], 1)
        self.assertTrue(evaluator.group_coverage(expected, [self.other, "ea_node_editor/equivalent.py"])["complete"])
        self.assertFalse(evaluator.group_coverage(expected, ["owner.py", self.other])["complete"])
        self.assertFalse(evaluator.group_coverage([], [self.source])["complete"])

    def test_multi_owner_source_and_test_groups_are_independently_required(self):
        expected = case(sources=[[self.source], [self.other]], tests=[[self.test], [self.other]])
        grade = evaluator.grade_case(expected, self.execution(sources=[self.source, self.other]), self.root)
        self.assertTrue(grade["source_pass"])
        self.assertFalse(grade["test_pass"])
        self.assertEqual(grade["coverage"]["tests"]["required_groups"], 2)

    def test_only_first_three_displayed_records_contribute(self):
        wrong = "ea_node_editor/not_owner.py"
        self.write(wrong, "pass\n")
        execution = self.execution(sources=[wrong, wrong, wrong, self.source])
        grade = evaluator.grade_case(case(), execution, self.root)
        self.assertFalse(grade["source_pass"])
        self.assertFalse(grade["evidence_valid"])

    def test_missing_corrupted_and_stale_numbered_evidence_cannot_pass(self):
        for mutate in (
            lambda item: item.pop("excerpt"),
            lambda item: item.update(excerpt=[]),
            lambda item: item["excerpt"][0].update(text="invented"),
            lambda item: item["excerpt"][0].update(line=99999),
            lambda item: item["excerpt"][0].update(line=True),
            lambda item: item.update(sha256="0" * 64),
            lambda item: item.update(excerpt=list(reversed(item["excerpt"]))),
            lambda item: item["excerpt"].append(item["excerpt"][0]),
        ):
            execution = self.execution()
            mutate(execution["pack"]["sources"][0])
            grade = evaluator.grade_case(case(), execution, self.root)
            self.assertFalse(grade["source_pass"])
            self.assertTrue(grade["coverage"]["sources"]["complete"])
            self.assertFalse(grade["evidence_valid"])
        self.assertTrue(evaluator.validate_candidate(self.evidence(self.source), self.root)["valid"])

    def test_missing_file_and_escape_paths_are_invalid(self):
        record = self.evidence(self.source)
        for path in ("../owner.py", "/outside.py", "C:/outside.py", "ea_node_editor/missing.py", "ea_node_editor\\owner.py"):
            record["path"] = path
            self.assertFalse(evaluator.validate_candidate(record, self.root)["valid"])

    def test_live_hash_and_lines_are_rechecked_after_inference(self):
        execution = self.execution()
        self.write(self.source, "def replacement():\n    return 7\n")
        grade = evaluator.grade_case(case(), execution, self.root)
        self.assertFalse(grade["source_pass"])
        self.assertFalse(grade["validity"]["sources"][0]["sha256_valid"])

    def test_no_match_needs_explicit_status_empty_lists_and_completed_command(self):
        expected = case(group="no_match", sources=[], tests=[])
        execution = self.execution(status="no_match", sources=[], tests=[])
        self.assertTrue(evaluator.grade_case(expected, execution, self.root)["no_match_pass"])
        for status in ("unresolved", "unavailable", "stale", "ok"):
            execution["pack"]["status"] = status
            self.assertFalse(evaluator.grade_case(expected, execution, self.root)["no_match_pass"])
        execution["pack"]["status"] = "no_match"
        execution["pack"]["sources"] = [self.evidence(self.source)]
        self.assertFalse(evaluator.grade_case(expected, execution, self.root)["no_match_pass"])
        execution["pack"]["sources"] = []
        execution["outcome"] = "timeout"
        self.assertFalse(evaluator.grade_case(expected, execution, self.root)["no_match_pass"])

    def test_exact_bypass_requires_zero_attempted_not_only_successful_requests(self):
        expected = case(group="exact")
        execution = self.execution(mode="exact")
        self.assertTrue(evaluator.grade_case(expected, execution, self.root)["exact_bypass_pass"])
        execution["pack"]["usage"]["attempted_requests"] = 1
        self.assertFalse(evaluator.grade_case(expected, execution, self.root)["exact_bypass_pass"])
        execution["pack"]["usage"].pop("attempted_requests")
        self.assertFalse(evaluator.grade_case(expected, execution, self.root)["exact_bypass_pass"])
        execution["pack"]["usage"]["attempted_requests"] = 0
        execution["pack"]["model"] = "unexpected model"
        self.assertFalse(evaluator.grade_case(expected, execution, self.root)["exact_bypass_pass"])

    def test_unavailable_fallback_paths_do_not_count_as_success(self):
        grade = evaluator.grade_case(case(), self.execution(status="unavailable"), self.root)
        self.assertTrue(grade["coverage"]["sources"]["complete"])
        self.assertFalse(grade["source_pass"])

    def test_baseline_whole_query_guard_preserves_saved_uri_prose(self):
        inventory = Mock(candidates={})
        inventory.resolve_exact.return_value = ExactMatch("resolved", (self.source,))
        prose = "Inspect saved:// and temp:// reference grammar"
        self.assertEqual(evaluator.exact_preflight(prose, inventory).status, "not_exact")
        inventory.resolve_exact.assert_not_called()
        for query in (self.source, "unique_owner", "`unique_owner`", str(self.root / "path with spaces.py")):
            self.assertEqual(evaluator.exact_preflight(query, inventory).status, "resolved")

    def test_baseline_and_pilot_exact_results_match_without_constructing_client(self):
        for query in (self.source, "unique_owner"):
            baseline = evaluator.run_baseline(query, self.root)
            pilot = nav_assist.run(query, root=self.root)
            for key in ("status", "mode", "sources", "tests", "usage", "model"):
                self.assertEqual(baseline[key], pilot[key])
            self.assertEqual(baseline["usage"]["attempted_requests"], 0)

    def test_baseline_prose_uses_only_incumbent_displayed_capsules(self):
        query = "Inspect saved:// owner reference grammar"
        def incumbent(args, root):
            self.assertEqual(args.query, query)
            self.assertFalse(args.expand)
            self.assertEqual(args.limit, 5)
            print(json.dumps({"owners": [{"path": self.source, "focused_test": self.test}]}))
        with patch.object(evaluator.nav, "cmd_find", side_effect=incumbent) as called, \
                patch.object(nav_assist, "run", side_effect=AssertionError("semantic pilot in baseline")):
            baseline = evaluator.run_baseline(query, self.root)
        self.assertEqual(called.call_count, 1)
        self.assertEqual([item["path"] for item in baseline["sources"]], [self.source])
        self.assertEqual([item["path"] for item in baseline["tests"]], [self.test])
        self.assertEqual(baseline["usage"]["attempted_requests"], 0)

    def test_baseline_does_not_convert_owner_only_advisory_to_no_match(self):
        with patch.object(evaluator.nav, "cmd_find", side_effect=lambda *args: print('{"owners":[{"owner_map":"a.md"}]}')):
            self.assertEqual(evaluator.run_baseline("Inspect synthetic behavior", self.root)["status"], "unresolved")

    def test_worker_grades_bounded_rendered_pack_not_full_raw_result(self):
        # Optional purpose text may be shortened; an exact line cannot be clipped.
        self.write(self.source, "# " + "x" * 30_000 + "\n")
        result = self.execution()["pack"]
        result["trace"] = {"inventory": [self.source], "stages": {}}
        with patch.object(nav_assist, "run", return_value=result):
            response = evaluator.worker_payload("synthetic query", self.root, "pilot")
        self.assertLessEqual(response["rendered_chars"], 24_000)
        self.assertNotIn("trace", response["pack"])
        self.assertFalse(response["pack"]["sources"])
        self.assertEqual(response["selected_paths"]["sources"], [self.source])
        response["outcome"] = "completed"
        grade = evaluator.grade_case(case(), response, self.root)
        self.assertFalse(grade["source_pass"])
        self.assertEqual(grade["candidate_loss"]["sources"][0]["alternatives"][0]["stage"], "rendered_output_cap")

    def test_isolated_child_receives_query_only_not_gold_and_no_shell(self):
        query = 'Inspect "quotes"; $(never_execute) saved://data'
        payload = {"pack": self.execution()["pack"], "selected_paths": {}, "trace": None, "diagnostics": {}}
        payload["rendered_chars"] = len(json.dumps(payload["pack"], ensure_ascii=True, separators=(",", ":")))
        child = subprocess.CompletedProcess([], 0, stdout=json.dumps(payload).encode())
        with patch.object(evaluator.subprocess, "run", return_value=child) as spawn, \
                patch.object(evaluator, "perf_counter", side_effect=[10.0, 12.75]):
            result = evaluator.run_isolated(query, self.root, "pilot", timeout=15)
        args, kwargs = spawn.call_args
        self.assertEqual(args[0][1:3], ["-I", "-c"])
        self.assertEqual(json.loads(kwargs["input"]), {"query": query, "root": str(self.root), "arm": "pilot"})
        self.assertNotIn(query, args[0])
        self.assertNotIn("env", kwargs)  # key inherited, never copied to the command/report
        self.assertFalse(kwargs.get("shell", False))
        self.assertEqual(kwargs["timeout"], 15)
        self.assertEqual(kwargs["stderr"], subprocess.DEVNULL)
        self.assertEqual(result["wall_seconds"], 2.75)
        self.assertEqual(result["outcome"], "completed")

    def test_real_isolated_process_runs_exact_without_api_or_shared_inventory(self):
        # Exact preflight runs before any client construction, even in this new interpreter.
        for arm in evaluator.ARMS:
            result = evaluator.run_isolated(self.source, self.root, arm, timeout=15)
            self.assertEqual(result["outcome"], "completed", result.get("error_code"))
            self.assertEqual(result["pack"]["mode"], "exact")
            self.assertEqual(result["pack"]["usage"]["attempted_requests"], 0)
            self.assertGreater(result["wall_seconds"], 0)

    def test_timeout_launch_error_invalid_output_and_child_failure_are_recorded_safely(self):
        for failure, expected in (
            (subprocess.TimeoutExpired("do not log key", 1, output=b"sensitive partial body"), "timeout"),
            (OSError("sensitive path key"), "error"),
            (subprocess.CompletedProcess([], 3, stdout=b"sensitive error stack"), "error"),
            (subprocess.CompletedProcess([], 0, stdout=b"sensitive invalid JSON"), "error"),
        ):
            with patch.object(evaluator.subprocess, "run") as spawn:
                if isinstance(failure, Exception):
                    spawn.side_effect = failure
                else:
                    spawn.return_value = failure
                result = evaluator.run_isolated("synthetic query", self.root, "pilot")
            self.assertEqual(result["outcome"], expected)
            self.assertIsNone(result["pack"])
            self.assertNotIn("sensitive", json.dumps(result))
            grade = evaluator.grade_case(case(), result, self.root)
            self.assertFalse(grade["source_pass"])
            self.assertFalse(grade["test_pass"])
            self.assertFalse(grade["evidence_valid"])

    def test_worker_exception_has_no_raw_exception_text(self):
        request = {"query": "synthetic query", "root": str(self.root), "arm": "pilot"}
        output = io.StringIO()
        with patch.object(evaluator.sys, "stdin", io.StringIO(json.dumps(request))), \
                patch.object(evaluator, "worker_payload", side_effect=RuntimeError("secret response")), \
                contextlib.redirect_stdout(output):
            code = evaluator.worker_main()
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue()), {"worker_error": "worker_failed"})

    def test_worker_rejects_gold_fields(self):
        request = {"query": "synthetic query", "root": str(self.root), "arm": "pilot", "source_groups": [[self.source]]}
        with patch.object(evaluator.sys, "stdin", io.StringIO(json.dumps(request))), \
                patch.object(evaluator, "worker_payload") as worker, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evaluator.worker_main(), 1)
        worker.assert_not_called()

    def test_candidate_loss_stages_follow_trace_not_gold_ranking(self):
        path = self.source
        execution = self.execution(sources=[])
        execution["trace"] = {"inventory": [path], "stages": {"initial": {"candidates": []}, "rich": {"candidates": [], "scores": {}}}}
        def stage():
            return evaluator.candidate_loss([[path]], [], execution, "sources")[0]["alternatives"][0]["stage"]
        self.assertEqual(stage(), "local_retrieval_and_route_rescue")
        execution["trace"]["stages"]["initial"]["candidates"] = [path]
        self.assertEqual(stage(), "rich_evidence_selection")
        execution["trace"]["stages"]["rich"]["candidates"] = [path]
        self.assertEqual(stage(), "rich_scoring_incomplete")
        execution["trace"]["stages"]["rich"]["scores"][path] = {"probabilities": {"0": 1, "1": 0, "2": 0, "3": 0}}
        self.assertEqual(stage(), "relevance_category")
        execution["trace"]["stages"]["rich"]["scores"][path]["probabilities"] = {"0": 0, "1": 0, "2": 0, "3": 1}
        self.assertEqual(stage(), "final_three_candidate_cap")
        execution["pack"]["status"] = "no_match"
        self.assertEqual(stage(), "task_scope_rejection")

    def test_candidate_loss_uses_combined_normalized_owner_probability(self):
        execution = self.execution(sources=[])
        execution["trace"] = {"inventory": [self.source], "stages": {
            "rich": {"candidates": [self.source], "scores": {}}}}
        for values, expected_stage in (
            ((.02, .40, .34, .24), "final_three_candidate_cap"),
            ((.24, .25, .25, .25), "final_three_candidate_cap"),
            ((.25, .26, .25, .26), "relevance_category"),
        ):
            with self.subTest(probabilities=values):
                score = {"probabilities": dict(zip(("0", "1", "2", "3"), values))}
                execution["trace"]["stages"]["rich"]["scores"][self.source] = score
                loss = evaluator.candidate_loss([[self.source]], [], execution, "sources")
                self.assertEqual(loss[0]["alternatives"][0]["stage"], expected_stage)

    def test_malformed_trace_probabilities_are_not_owner_categories(self):
        for score in (None, {}, {"probabilities": []}, {"probabilities": {}},
                      {"probabilities": {"0": 0, "1": 0, "2": 0, "3": 0}},
                      {"probabilities": {"0": 0, "1": 0, "2": 0, "3": "1"}},
                      {"probabilities": {"0": 0, "1": 0, "2": 0, "3": True}},
                      {"probabilities": {"0": 0, "1": 0, "2": 0, "3": float("nan")}},
                      {"probabilities": {"0": 0, "1": 0, "2": 0, "3": float("inf")}},
                      {"probabilities": {"0": 0, "1": 0, "2": 0, "3": 1, "4": 1}}):
            with self.subTest(score=score):
                self.assertFalse(evaluator._owner_category(score))

    def test_frozen_corpus_hash_shape_and_development_rejection(self):
        path = evaluator.REPO_ROOT / "tests/fixtures/nav_assist_evaluation.json"
        before = path.read_bytes()
        corpus = evaluator.load_corpus(path)
        self.assertEqual(corpus["sha256"], evaluator.FROZEN_SHA256)
        self.assertEqual(corpus["counts"], evaluator.FROZEN_COUNTS)
        self.assertEqual(len(corpus["cases"]), 20)
        self.assertEqual(path.read_bytes(), before)
        development = evaluator.REPO_ROOT / "tests/fixtures/nav_assist_development.json"
        with self.assertRaisesRegex(ValueError, "qualification_requires"):
            evaluator.load_corpus(development)
        self.assertEqual(len(evaluator.load_corpus(development, development=True)["cases"]), 16)
        altered = self.write("altered.json", before.decode() + "\n")
        with self.assertRaisesRegex(ValueError, "qualification_requires"):
            evaluator.load_corpus(altered)

    def test_corpus_rejects_missing_groups_duplicate_ids_and_unsafe_paths(self):
        good = {"schema_version": 1, "cases": [case()]}
        for mutate in (
            lambda value: value["cases"].append(case()),
            lambda value: value["cases"][0].update(source_groups=[]),
            lambda value: value["cases"][0].update(test_groups=[[]]),
            lambda value: value["cases"][0].update(source_groups=[["../secret.py"]]),
            lambda value: value["cases"][0].update(source_groups=[[{}]]),
            lambda value: value["cases"][0].update(group="no_match"),
        ):
            value = copy.deepcopy(good)
            mutate(value)
            path = self.write("synthetic.json", json.dumps(value))
            with self.assertRaises(ValueError):
                evaluator.load_corpus(path, development=True)

    def test_credential_corpus_leaves_are_rejected_before_output_or_children(self):
        secret = 'synthetic-' + 'key"\\with-escaping'
        mutations = (
            lambda value: value["cases"][0].update(query="Inspect " + secret),
            lambda value: value["cases"][0].update(source_groups=[["ea_node_editor/" + secret + ".py"]]),
            lambda value: value["cases"][0].update(test_groups=[["tests/" + secret + ".py"]]),
            lambda value: value["cases"][0].update(evidence=[{"reason": secret}]),
            lambda value: value["cases"][0].update(unknown_metadata={"nested": [secret]}),
            lambda value: value.update(unknown_metadata={secret: "innocent value"}),
        )
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": secret}):
            for index, mutate in enumerate(mutations):
                with self.subTest(field=index):
                    value = {"schema_version": 1, "cases": [case()]}
                    mutate(value)
                    raw = json.dumps(value)
                    # A scan of serialized JSON would miss the actual configured key.
                    self.assertNotIn(secret, raw)
                    corpus = self.write("sensitive-corpus.json", raw)
                    output = self.root / "not-created" / f"report-{index}.json"
                    with self.assertRaisesRegex(ValueError, "^unsafe_corpus$"):
                        evaluator.load_corpus(corpus, development=True)
                    stdout, stderr = io.StringIO(), io.StringIO()
                    with patch.object(evaluator, "evaluate") as run, \
                            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        code = evaluator.main(["--corpus", str(corpus), "--output", str(output), "--development"])
                    self.assertEqual(code, 2)
                    run.assert_not_called()
                    self.assertFalse(output.parent.exists())
                    self.assertEqual(corpus.read_text(), raw)
                    self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def test_recognizable_credential_in_unknown_metadata_is_rejected(self):
        value = {"schema_version": 1, "cases": [case()],
                 "unknown": {"note": "password" + ' = "' + "synthetic-value-123456789" + '"'}}
        corpus = self.write("recognizable-corpus.json", json.dumps(value))
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}), \
                self.assertRaisesRegex(ValueError, "^unsafe_corpus$"):
            evaluator.load_corpus(corpus, development=True)

    def test_programmatic_corpus_rejection_precedes_children(self):
        secret = "synthetic-" + "programmatic-secret"
        corpus = corpus_for([case()])
        corpus["cases"][0]["unknown"] = [secret]
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": secret}), \
                patch.object(evaluator, "run_isolated") as child, \
                self.assertRaisesRegex(ValueError, "^unsafe_corpus$"):
            evaluator.evaluate(corpus, root=self.root)
        child.assert_not_called()

    def test_report_serialization_rejects_raw_nested_credentials_without_writing_them(self):
        secret = 'synthetic-' + 'report"\\secret'
        corpus = self.write("safe-corpus.json", json.dumps({"schema_version": 1, "cases": [case()]}))
        output = self.root / "rejected-report.json"
        report = {"summary": {"qualified": False, "complete_corpus": True},
                  "cases": [{"pilot": {"trace": {"unknown": [secret]}}}]}
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": secret}):
            with self.assertRaisesRegex(ValueError, "^unsafe_report$"):
                evaluator.render_report(report)
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(evaluator, "evaluate", return_value=report), \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = evaluator.main(["--corpus", str(corpus), "--output", str(output), "--development"])
        self.assertEqual(code, 2)
        self.assertEqual(output.read_bytes(), b"")
        self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())

    def qualifying_rows(self):
        cases, rows = [], []
        for group, count in evaluator.FROZEN_COUNTS.items():
            for number in range(count):
                expected = case(f"{group}{number}", group)
                if group == "no_match":
                    expected.update(source_groups=[], test_groups=[])
                    execution = self.execution(status="no_match", sources=[], tests=[])
                else:
                    execution = self.execution(mode="exact" if group == "exact" else "semantic")
                execution["grade"] = evaluator.grade_case(expected, execution, self.root)
                cases.append(expected)
                rows.append({"id": expected["id"], "group": group,
                             **{arm: copy.deepcopy(execution) for arm in evaluator.ARMS}})
        corpus = corpus_for(cases, development=False)
        corpus["sha256"] = evaluator.FROZEN_SHA256
        return corpus, rows

    def summary(self, corpus, rows, **changes):
        return evaluator.summarize(corpus, rows, identities_stable=changes.get("identities_stable", True),
                                   corpus_unchanged=changes.get("corpus_unchanged", True))

    def test_exact_thresholds_and_failed_cases_keep_eighteen_denominator(self):
        corpus, rows = self.qualifying_rows()
        self.assertTrue(self.summary(corpus, rows)["qualified"])
        rows[0]["pilot"]["grade"]["source_pass"] = False
        for row in rows[:3]:
            row["pilot"]["grade"]["test_pass"] = False
        summary = self.summary(corpus, rows)
        self.assertEqual(summary["arms"]["pilot"]["actionable_denominator"], 18)
        self.assertTrue(summary["qualified"])
        rows[1]["pilot"]["grade"]["source_pass"] = False
        self.assertFalse(self.summary(corpus, rows)["gates"]["source_17_of_18"])
        rows[3]["pilot"]["grade"]["test_pass"] = False
        self.assertFalse(self.summary(corpus, rows)["gates"]["tests_15_of_18"])
        rows[0]["pilot"] = {"outcome": "timeout", "pack": None, "wall_seconds": 60,
                             "grade": evaluator.grade_case(corpus["cases"][0], {"outcome": "timeout"}, self.root)}
        summary = self.summary(corpus, rows)
        self.assertEqual(summary["arms"]["pilot"]["actionable_denominator"], 18)
        self.assertEqual(summary["arms"]["pilot"]["command_failures"], 1)
        self.assertEqual(summary["arms"]["pilot"]["latency_samples"], 20)
        self.assertFalse(summary["qualified"])

    def test_nearest_rank_p95_and_strict_ten_second_gate(self):
        self.assertEqual(evaluator.nearest_rank_p95(list(range(1, 21))), 19)
        self.assertEqual(evaluator.nearest_rank_p95([3]), 3)
        self.assertIsNone(evaluator.nearest_rank_p95([]))
        corpus, rows = self.qualifying_rows()
        rows[-1]["pilot"]["wall_seconds"] = 50
        rows[-2]["pilot"]["wall_seconds"] = 10
        summary = self.summary(corpus, rows)
        self.assertEqual(summary["arms"]["pilot"]["p95_wall_seconds"], 10)
        self.assertFalse(summary["gates"]["uncached_p95_below_10_seconds"])
        rows[-2]["pilot"]["wall_seconds"] = 9.999
        self.assertTrue(self.summary(corpus, rows)["gates"]["uncached_p95_below_10_seconds"])

    def test_development_subsets_mutated_corpus_and_changed_sources_never_qualify(self):
        corpus, rows = self.qualifying_rows()
        corpus["development"] = True
        self.assertFalse(self.summary(corpus, rows)["qualified"])
        corpus["development"] = False
        self.assertFalse(self.summary(corpus, rows[:2])["qualified"])
        self.assertFalse(self.summary(corpus, rows, corpus_unchanged=False)["qualified"])
        self.assertFalse(self.summary(corpus, rows, identities_stable=False)["qualified"])
        rows[0]["pilot"]["diagnostics"]["inventory_sha256"] = "changed-inventory"
        self.assertFalse(self.summary(corpus, rows)["gates"]["source_identity_stable"])

    def test_evaluate_runs_fresh_arms_and_preserves_interrupt_with_no_gold_in_worker(self):
        cases = [case("one"), case("two")]
        path = self.write("synthetic.json", json.dumps({"schema_version": 1, "cases": cases}))
        corpus = evaluator.load_corpus(path, development=True)
        calls = []
        def run(query, root, arm, *, timeout):
            calls.append((query, root, arm, timeout))
            if len(calls) == 3:
                raise KeyboardInterrupt
            return self.execution()
        with patch.object(evaluator, "run_isolated", side_effect=run):
            report = evaluator.evaluate(corpus, root=self.root)
        self.assertEqual([call[2] for call in calls], ["baseline", "pilot", "baseline"])
        self.assertTrue(report["interrupted"])
        self.assertEqual(len(report["cases"]), 2)
        self.assertEqual(report["cases"][1]["pilot"]["outcome"], "not_run")
        self.assertEqual(report["summary"]["arms"]["pilot"]["actionable_denominator"], 2)
        self.assertFalse(report["summary"]["qualified"])
        self.assertFalse(report["summary"]["complete_corpus"])
        self.assertNotIn("trace", report["cases"][0]["pilot"])

    def test_evaluate_subset_requires_explicit_development(self):
        corpus, _ = self.qualifying_rows()
        with self.assertRaisesRegex(ValueError, "subsets_require_development"):
            evaluator.evaluate(corpus, root=self.root, case_ids=[corpus["cases"][0]["id"]])

    def test_cli_rejects_existing_output_source_suffix_and_corpus_overwrite_before_calls(self):
        corpus = self.write("corpus.json", json.dumps({"schema_version": 1, "cases": [case()]}))
        existing = self.write("report.json", "preserve report")
        for output in (existing, corpus, self.root / "source.py"):
            with patch.object(evaluator, "evaluate") as run, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(evaluator.main(["--corpus", str(corpus), "--output", str(output), "--development"]), 2)
            run.assert_not_called()
        self.assertEqual(existing.read_text(), "preserve report")
        self.assertEqual(json.loads(corpus.read_text())["cases"][0]["id"], "sample")

    def test_cli_writes_explicit_report_without_exposing_error_text(self):
        corpus = self.write("corpus.json", json.dumps({"schema_version": 1, "cases": [case()]}))
        output = self.root / "reports/development.json"
        report = {"summary": {"qualified": False, "complete_corpus": True}}
        with patch.object(evaluator, "evaluate", return_value=report), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(evaluator.main(["--corpus", str(corpus), "--output", str(output), "--development"]), 0)
        self.assertEqual(json.loads(output.read_text()), report)


if __name__ == "__main__":
    unittest.main()
