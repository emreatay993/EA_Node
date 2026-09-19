# Purpose: Prove bounded TypeSafe navigation, exact bypass, typed failures and live evidence safety.
# Map: subsystems/verification_testing_docs_hygiene.md
# Tests: tests/test_nav_assist.py
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor

from scripts import nav_assist as nav
from scripts import nav_assist_client as transport
from scripts import nav_assist_selection as selection
from scripts.nav_assist_inventory import build_inventory
from tests.test_nav_assist_inventory import InventoryFixture


def response_for(questions, scores=None, scope="investigate"):
    answers = {}
    for identity, question in questions.items():
        if question["type"] == "choice":
            answers[identity] = {"type": "choice", "choice": scope, "confidence": 0.8,
                                 "probabilities": {key: float(key == scope) for key in question["criteria"]}}
        else:
            level = (scores or {}).get(identity, 3)
            answers[identity] = {"type": "score", "score": float(level), "confidence": 0.7,
                                 "probabilities": {str(index): float(index == level) for index in range(len(question["criteria"]))},
                                 "legend": {str(index): value for index, value in enumerate(question["criteria"])}}
    return {"model": transport.MODEL, "answers": answers, "usage": {"input_tokens": 20, "output_tokens": 10}}


class FakeClient:
    def __init__(self, *, relevant=None, scope="investigate", mutate=None):
        self.calls = []
        self.relevant = relevant
        self.scope = scope
        self.mutate = mutate

    def evaluate(self, state, questions):
        self.calls.append((copy.deepcopy(state), copy.deepcopy(questions)))
        scores = {record["id"]: 3 if self.relevant is None or record["path"] in self.relevant else 0
                  for record in state["candidates"]}
        if self.mutate:
            mutate, self.mutate = self.mutate, None
            mutate()
        return response_for(questions, scores, self.scope)


class NavigationTests(InventoryFixture):
    def setUp(self):
        super().setUp()
        self.source = "ea_node_editor/graph/forwarding.py"
        self.ui = "ea_node_editor/ui/recommendations.py"
        self.test = "tests/test_forwarding.py"
        self.ui_test = "tests/test_recommendations.py"
        self.neighbor = "tests/test_unrelated.py"
        self.write(self.source, "# Purpose: Forward every enabled type to accepted inputs.\n# Map: subsystems/sample.md\n# Tests: tests/test_forwarding.py\ndef forward_types():\n    return ['mixed', 'types']\n")
        self.write(self.ui, "# Purpose: Recommend connection insertion inputs for mixed types.\n# Map: subsystems/sample.md\n# Tests: tests/test_recommendations.py\ndef suggest_inputs():\n    return ['connection']\n")
        self.write(self.test, "from ea_node_editor.graph.forwarding import forward_types\ndef test_forwarded():\n    assert forward_types() == ['mixed', 'types']\n")
        self.write(self.ui_test, "from ea_node_editor.ui.recommendations import suggest_inputs\ndef test_suggestions():\n    assert suggest_inputs() == ['connection']\n")
        self.write(self.neighbor, "def test_other():\n    assert 1 == 1\n")
        self.write("docs/agent_maps/subsystems/sample.md", "# Mixed type connections\n## Start Here\n`" + self.source + "`\n`" + self.ui + "`\n## Focused Verification\n`" + self.test + "`\n`" + self.ui_test + "`\n`" + self.neighbor + "`\n")

    def test_exact_path_and_symbol_never_construct_client_or_need_key(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}), patch.object(nav, "TypeSafeClient", side_effect=AssertionError("client constructed")):
            for query in (self.source, "forward_types", "suggest_inputs", str(self.root / self.source)):
                with self.subTest(query=query):
                    result = nav.run(query, root=self.root)
                    self.assertEqual(result["status"], "ok")
                    self.assertEqual(result["mode"], "exact")
                    self.assertEqual(result["usage"]["requests"], 0)
                    self.assertIsNone(result["model"])
                    self.assertTrue(result["tests"])

    def test_semantic_multi_owner_preserves_independent_owners_and_direct_tests(self):
        expected = {self.source, self.ui, self.test, self.ui_test}
        client = FakeClient(relevant=expected)
        result = nav.run("Trace mixed forwarded types and connection insertion recommendations", root=self.root, client=client, include_trace=True)
        self.assertEqual(result["status"], "ok")
        self.assertEqual({item["path"] for item in result["sources"]}, {self.source, self.ui})
        self.assertEqual({item["path"] for item in result["tests"]}, {self.test, self.ui_test})
        self.assertTrue(all(item["relationship"] == "direct" for item in result["tests"]))
        for state, questions in client.calls:
            self.assertLessEqual(len(state["candidates"]), selection.BATCH_SIZE)
            self.assertTrue(all(question["type"] == "score" for identity, question in questions.items() if identity != "task_scope"))
        self.assertEqual(set(result["trace"]["stages"]), {"route", "initial", "rich"})
        self.assertNotIn("trace", json.loads(nav.render_json(result)))

    def test_scope_no_match_and_uncertain_empty_shortlist_are_distinct(self):
        no_match = nav.run("Find a Stripe payment webhook", root=self.root, client=FakeClient(scope="absent", relevant=set()))
        self.assertEqual(no_match["status"], "no_match")
        self.assertFalse(no_match["sources"] or no_match["tests"])
        unresolved = nav.run("Inspect unknown mixed type behavior", root=self.root, client=FakeClient(relevant=set()))
        self.assertEqual(unresolved["status"], "unresolved")
        self.assertTrue(unresolved["gaps"])

    def test_scope_has_complete_area_catalogue_beyond_lexical_cutoff(self):
        for number in range(25):
            self.write(f"docs/agent_maps/subsystems/area_{number:02}.md", f"# Independent area {number:02}\n`{self.source}`\n")
        self.write("docs/agent_maps/subsystems/z_last.md", f"# Last specialised area\n`{self.ui}`\n")
        inventory = build_inventory(self.root)
        client = FakeClient()
        result = nav.run("Find implementation behavior", inventory=inventory, client=client, include_trace=True)
        expected = {route.route_key for route in inventory.routes if route.kind != "qml_component"}
        state = next(state for state, questions in client.calls if "task_scope" in questions)
        self.assertEqual({area["area"] for area in state["area_catalogue"]}, expected)
        self.assertTrue(expected.issubset(result["trace"]["stages"]["route"]["candidates"]))
        self.assertLess(len(state["candidates"]), len(state["area_catalogue"]))
        self.assertTrue(all("COREX" in state["repository_context"] for state, _ in client.calls))

    def test_contradictory_scope_cannot_discard_independently_supported_owners(self):
        client = FakeClient(scope="absent", relevant={self.source, self.test})
        result = nav.run("Inspect mixed forwarded type connections", root=self.root, client=client)
        self.assertEqual(result["status"], "ok")
        self.assertIn(self.source, {item["path"] for item in result["sources"]})

    def test_split_owner_probability_is_combined_without_confidence_cutoff(self):
        class SplitOwnerClient(FakeClient):
            def evaluate(inner, state, questions):
                response = super().evaluate(state, questions)
                for identity, answer in response["answers"].items():
                    if identity == self.source:
                        answer.update(score=1.8, confidence=.25,
                                      probabilities={"0": .02, "1": .40, "2": .34, "3": .24})
                return response
        result = nav.run("Inspect mixed forwarded type connections", root=self.root,
                         client=SplitOwnerClient(relevant={self.source, self.test}))
        candidate = next(item for item in result["sources"] if item["path"] == self.source)
        self.assertEqual(candidate["owner_probability"], .58)
        self.assertEqual(candidate["confidence"], .25)
        self.assertTrue(any("combines" in text for text in result["uncertainty"]))

    def test_declaration_and_documentation_recall_can_find_an_opaque_late_owner(self):
        owner = "ea_node_editor/data/opaque.py"
        self.write(owner, "# Purpose: Format-specific behavior.\n" + "# filler\n" * 200
                   + 'def resolve_separator():\n    """Infer dialect from delimited tabular input."""\n    return 1\n')
        self.write("ea_node_editor/ui_qml/Opaque.qml", "import QtQuick\nItem {\n"
                   "property color resolvedBackgroundColor: palette.background\n"
                   "property int maximumTextWidth: 360\n}\n")
        inventory = build_inventory(self.root)
        scores = selection.lexical_scores(inventory, "Infer the delimiter separator and dialect")
        self.assertEqual(selection.rank_paths(inventory, scores, "source", 1), [owner])
        scores = selection.lexical_scores(inventory, "Set background color and maximum text width")
        self.assertEqual(selection.rank_paths(inventory, scores, "source", 1), ["ea_node_editor/ui_qml/Opaque.qml"])
        self.assertFalse(inventory._content)

    def test_owner_probability_normalizes_legitimate_provider_rounding(self):
        class RoundedClient(FakeClient):
            def evaluate(inner, state, questions):
                response = super().evaluate(state, questions)
                for identity, answer in response["answers"].items():
                    if identity == self.source:
                        answer.update(score=2.50, confidence=.4,
                                      probabilities={"0": 0, "1": 0, "2": .50, "3": .51})
                return response
        result = nav.run("Inspect mixed forwarded type connections", root=self.root,
                         client=RoundedClient(relevant={self.source, self.test}))
        candidate = next(item for item in result["sources"] if item["path"] == self.source)
        self.assertEqual(candidate["owner_probability"], 1.0)
        answer = {"probabilities": {"0": .25, "1": .26, "2": .25, "3": .25}}
        self.assertAlmostEqual(selection.owner_probability(answer), .5 / 1.01)
        self.assertFalse(selection._positive(answer))

    def test_ambiguous_or_missing_identifiers_stay_local(self):
        self.write("ea_node_editor/another.py", "def forward_types():\n    pass\n")
        with patch.object(nav, "TypeSafeClient", side_effect=AssertionError("client constructed")):
            ambiguous = nav.run("forward_types", root=self.root)
            missing = nav.run("ea_node_editor/absent.py", root=self.root)
        self.assertEqual(ambiguous["status"], "unresolved")
        self.assertEqual(len(ambiguous["sources"]), 2)
        self.assertEqual(missing["status"], "unresolved")
        self.assertFalse(missing["sources"])

    def test_natural_language_containing_reference_slashes_is_not_an_exact_path(self):
        client = FakeClient()
        result = nav.run("Inspect saved:// and temp:// reference grammar", root=self.root, client=client)
        self.assertEqual(result["mode"], "semantic")
        self.assertTrue(client.calls)

    def test_all_service_failure_codes_have_safe_local_fallback(self):
        for code in ("missing_key", "authentication", "rate_limited", "timeout", "invalid_response", "service"):
            with self.subTest(code=code):
                client = Mock()
                client.evaluate.side_effect = transport.ServiceUnavailable(code)
                result = nav.run("Inspect mixed forwarded type connections", root=self.root, client=client)
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["mode"], "local_fallback")
                self.assertEqual(result["error"]["code"], code)
                self.assertTrue(result["sources"])
                self.assertTrue(all(item["score"] is None for item in result["sources"]))
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}):
            result = nav.run("Inspect mixed forwarded type connections", root=self.root)
        self.assertEqual(result["error"]["code"], "missing_key")

    def test_changed_unselected_input_is_stale_instead_of_fresh_selected_output(self):
        client = FakeClient(relevant={self.source, self.test}, mutate=lambda: self.write(self.ui, "def replaced():\n    pass\n"))
        result = nav.run("Inspect mixed forwarded type connections", root=self.root, client=client)
        self.assertEqual(result["status"], "stale")
        self.assertFalse(result["sources"] or result["tests"])

    def test_changed_association_or_ignore_rules_reject_before_next_outbound_call(self):
        for change in (lambda: self.write("docs/agent_maps/subsystems/sample.md", "# Changed\n"),
                       lambda: self.write(".gitignore", self.source + "\n")):
            with self.subTest(change=change):
                fresh = build_inventory(self.root)
                change()
                client = FakeClient()
                result = nav.run("Inspect mixed forwarded type connections", inventory=fresh, client=client)
                self.assertEqual(result["status"], "stale")
                self.assertFalse(client.calls)
                self.write(".gitignore", "")

    def test_excerpts_are_current_numbered_lines_and_shared_route_is_not_direct(self):
        result = nav.run("Inspect mixed forwarded type connections", root=self.root, client=FakeClient())
        neighbor = next(item for item in result["tests"] if item["path"] == self.neighbor)
        self.assertEqual(neighbor["relationship"], "shared_route")
        self.assertFalse(neighbor["associations"])
        for item in result["sources"] + result["tests"]:
            lines = (self.root / item["path"]).read_text().splitlines()
            self.assertTrue(item["symbols"])
            self.assertTrue(item["excerpt"])
            self.assertTrue(all(lines[line["line"] - 1] == line["text"] for line in item["excerpt"]))

    def test_private_ignored_and_credential_data_are_not_sent_or_returned(self):
        self.write("ea_node_editor/private/secret.py", "SECRET_SENTINEL = 1\n")
        self.write("ea_node_editor/ignored.py", "IGNORED_SENTINEL = 1\n")
        self.write(".gitignore", "ea_node_editor/ignored.py\n")
        self.write("ea_node_editor/token_holder.py", "api_key = 'sk-abcdefghijklmnopqrstuvwxyz012345'\n")
        password_path = "ea_node_editor/password_holder.py"
        self.write(password_path, 'password = "a-long-confidential-password"\n')
        client = FakeClient()
        result = nav.run("Inspect mixed forwarded type connections", root=self.root, client=client)
        text = json.dumps(client.calls) + nav.render_json(result)
        for sentinel in ("SECRET_SENTINEL", "IGNORED_SENTINEL", "sk-abcdefghijklmnopqrstuvwxyz012345", "a-long-confidential-password"):
            self.assertNotIn(sentinel, text)
        self.assertGreater(result["diagnostics"]["excluded_sensitive"], 0)
        result = nav.run("Inspect API key sk-abcdefghijklmnopqrstuvwxyz012345", root=self.root, client=client)
        self.assertEqual(result["error"]["code"], "unsafe_input")
        self.assertNotIn("sk-", nav.render_json(result))
        exact = nav.run(password_path, root=self.root)
        self.assertNotIn("a-long-confidential-password", nav.render_json(exact))
        self.assertEqual(exact["status"], "unresolved")
        self.assertTrue(exact["gaps"])
        overlong = nav.run('password = "a-long-confidential-password" ' + 'z' * 2100, root=self.root)
        self.assertNotIn("a-long-confidential-password", nav.render_json(overlong))

    def test_full_route_metadata_is_screened_before_title_truncation(self):
        self.write("docs/agent_maps/subsystems/sample.md", '# password = "' + 'x' * 200 + '"\n`' + self.source + '`\n')
        client = FakeClient()
        nav.run("Inspect mixed forwarded type connections", root=self.root, client=client)
        self.assertNotIn('x' * 100, json.dumps(client.calls))

    def test_failure_cancels_unsent_batches(self):
        inventory = build_inventory(self.root)
        client = Mock()
        client.evaluate.side_effect = transport.ServiceUnavailable("rate_limited")
        selector = selection.Selection(inventory, "Inspect mixed types", client)
        records = [{"id": f"f_{index}", "path": f"safe_{index}"} for index in range(100)]
        with self.assertRaises(transport.ServiceUnavailable):
            selector.score(records, "test_failure")
        self.assertLessEqual(client.evaluate.call_count, selection.WORKERS)

    def test_text_json_and_cli_are_bounded_and_preserve_status_uncertainty(self):
        result = nav.run("Inspect mixed forwarded type connections", root=self.root, client=FakeClient(), include_trace=True)
        for item in result["sources"] + result["tests"]:
            item["excerpt"] = [{"line": number, "text": "\u03b1" * 500} for number in range(1, 101)]
        rendered = nav.render_json(result, max_chars=4096)
        value = json.loads(rendered)
        self.assertLessEqual(len(rendered), 4096)
        self.assertEqual(value["status"], "ok")
        self.assertTrue(value["uncertainty"])
        self.assertTrue(value["output_truncated"])
        text = nav.render_text(result, max_chars=4096)
        self.assertLessEqual(len(text), 4096)
        self.assertIn("Navigation: ok", text)
        with patch.object(nav, "run", return_value=result), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(nav.main(["task", "--json"]), 0)
        self.assertLessEqual(len(output.getvalue()), nav.MAX_JSON_CHARS + 1)
        self.assertEqual(json.loads(output.getvalue())["status"], "ok")

    def test_serialized_oversized_six_candidate_pack_retains_evaluator_valid_excerpts(self):
        from scripts.evaluate_nav_assist import validate_candidate

        paths = []
        for kind in ("source", "test"):
            for number in range(3):
                path = f"ea_node_editor/packed_{number}.py" if kind == "source" else f"tests/test_packed_{number}.py"
                content = "\n" * 4 + "\n".join(
                    f"def operation_{index}():\n    return '" + "context_" * 24 + "'" for index in range(40)) + "\n"
                self.write(path, content)
                paths.append(path)
        inventory = build_inventory(self.root)
        evidence = inventory.evidence_batch(paths, center_line=5, max_lines=48, max_chars=6000)
        result = nav._base("Inspect the packed operations")
        result.update(status="ok", mode="semantic")
        result["gaps"] = ["Existing uncertainty must remain visible."]
        result["sources"] = [nav._pack(inventory, item, "operation", None, set()) for item in evidence[:3]]
        result["tests"] = [nav._pack(inventory, item, "operation", None, set()) for item in evidence[3:]]
        before = copy.deepcopy(result)
        self.assertGreater(len(json.dumps(result)), nav.MAX_JSON_CHARS)
        for budget in (nav.MAX_JSON_CHARS, nav.MAX_TEXT_CHARS, 4096, 2048):
            with self.subTest(budget=budget):
                rendered = nav.render_json(result, max_chars=budget)
                parsed = json.loads(rendered)
                self.assertLessEqual(len(rendered), budget)
                self.assertEqual(parsed["status"], result["status"])
                self.assertEqual(parsed["uncertainty"], result["uncertainty"])
                self.assertIn(result["gaps"][0], parsed["gaps"])
                retained = parsed["sources"] + parsed["tests"]
                for candidate in retained:
                    self.assertGreaterEqual(len(candidate["excerpt"]), nav.MIN_EXCERPT_LINES)
                    self.assertTrue(any(line["text"].strip() for line in candidate["excerpt"]))
                    self.assertTrue(validate_candidate(candidate, self.root)["valid"])
                if budget == nav.MAX_JSON_CHARS:
                    self.assertEqual(len(retained), 6)
                if len(retained) < 6:
                    self.assertEqual(sum(parsed["output_omitted"].values()), 6 - len(retained))
                    self.assertTrue(any("Display omitted" in gap for gap in parsed["gaps"]))
                text = nav.render_text(result, max_chars=budget)
                self.assertLessEqual(len(text), budget)
                self.assertIn("Navigation: ok", text)
        self.assertEqual(result, before)

    def test_empty_or_blank_evidence_is_omitted_explicitly(self):
        result = nav.run(self.source, root=self.root)
        result["sources"][0]["excerpt"] = [{"line": 1, "text": "   "}]
        parsed = json.loads(nav.render_json(result))
        self.assertFalse(parsed["sources"])
        self.assertEqual(parsed["output_omitted"]["sources"], 1)
        self.assertTrue(any("Display omitted" in gap for gap in parsed["gaps"]))

    def test_long_query_tight_budget_terminates_in_a_bounded_subprocess(self):
        result = nav.run(self.source, root=self.root)
        result["query"] = "Inspect the detailed behavior of the selected implementation. " * 5
        result["sources"][0]["excerpt"] = [
            {"line": number, "text": "# " + "large exact source context " * 40}
            for number in range(1, nav.MIN_EXCERPT_LINES + 1)
        ]
        code = (
            "import json,sys; from scripts import nav_assist as nav; "
            "value=json.load(sys.stdin); packed=nav.render_json(value,max_chars=2048); "
            "text=nav.render_text(value,max_chars=2048); "
            "print(json.dumps({'packed':json.loads(packed),'json_size':len(packed),'text_size':len(text)}))"
        )
        completed = subprocess.run([sys.executable, "-c", code], input=json.dumps(result), text=True,
                                   capture_output=True, cwd=nav.REPO_ROOT, timeout=5, check=True)
        output = json.loads(completed.stdout)
        self.assertLessEqual(output["json_size"], 2048)
        self.assertLessEqual(output["text_size"], 2048)
        self.assertLessEqual(len(output["packed"]["query"]), 120)
        self.assertEqual(output["packed"]["output_omitted"]["sources"], 1)
        self.assertEqual(output["packed"]["status"], result["status"])


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.questions = {"f_abcd": {"type": "score", "instructions": "Evaluate", "criteria": selection.RELEVANCE}}
        self.response = response_for(self.questions)

    def test_strict_response_validation_and_legitimate_rounding(self):
        self.assertEqual(transport.validate_response(self.response, self.questions)["model"], transport.MODEL)
        rounded = copy.deepcopy(self.response)
        rounded["answers"]["f_abcd"].update(score=2.32, probabilities={"0": 0, "1": 0, "2": .67, "3": .33})
        transport.validate_response(rounded, self.questions)
        mutations = (
            lambda value: value.update(model="jev-latest"),
            lambda value: value["answers"].update(unrequested=value["answers"]["f_abcd"]),
            lambda value: value["answers"]["f_abcd"].update(type="noul"),
            lambda value: value["answers"]["f_abcd"].update(score=float("nan")),
            lambda value: value["answers"]["f_abcd"].update(confidence=float("inf")),
            lambda value: value["answers"]["f_abcd"].update(score=True),
            lambda value: value["answers"]["f_abcd"].update(score=1),
            lambda value: value["answers"]["f_abcd"].update(legend={}),
            lambda value: value["answers"]["f_abcd"].update(probabilities={"invented": 1}),
            lambda value: value["usage"].update(input_tokens=-1),
            lambda value: value["answers"]["f_abcd"].update(score=10 ** 400),
            lambda value: value["answers"]["f_abcd"].update(confidence=10 ** 400),
            lambda value: value["answers"]["f_abcd"]["probabilities"].update({"0": 10 ** 400}),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                response = copy.deepcopy(self.response)
                mutation(response)
                with self.assertRaises(transport.ServiceUnavailable):
                    transport.validate_response(response, self.questions)

    def test_invalid_environment_key_fails_without_header_or_secret_exception(self):
        for key in ("key-with\nnewline-and-secret", "key-with-\u03b1-unicode"):
            with patch.dict(os.environ, {"TYPESAFE_API_KEY": key}), patch.object(transport.http.client, "HTTPSConnection") as factory:
                with self.assertRaises(transport.ServiceUnavailable) as raised:
                    transport.TypeSafeClient()
                self.assertEqual(raised.exception.code, "authentication")
                self.assertNotIn(key, str(raised.exception))
                factory.assert_not_called()

    def test_https_endpoint_model_and_failure_responses_never_leak_raw_body(self):
        sentinel = "test-private-key-01234567890123456789"
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": sentinel, "TYPESAFE_ENDPOINT": "http://untrusted.test"}), patch.object(transport.http.client, "HTTPSConnection") as factory:
            connection = factory.return_value
            response = connection.getresponse.return_value
            response.status = 200
            response.read.return_value = json.dumps(self.response).encode()
            client = transport.TypeSafeClient()
            self.assertEqual(client.evaluate({"task": "example"}, self.questions)["model"], transport.MODEL)
            self.assertEqual(factory.call_args.args[0], "api.typesafe.ai")
            self.assertEqual(connection.request.call_args.args[:2], ("POST", "/v1/systemone"))
            self.assertEqual(json.loads(connection.request.call_args.kwargs["body"])["model"], transport.MODEL)
            for status, expected in ((401, "authentication"), (429, "rate_limited"), (529, "rate_limited"), (500, "service"), (302, "service")):
                response.status = status
                with self.subTest(status=status), self.assertRaises(transport.ServiceUnavailable) as raised:
                    client.evaluate({"task": "example"}, self.questions)
                self.assertEqual(raised.exception.code, expected)
                self.assertNotIn(sentinel, str(raised.exception))
            response.status = 200
            for raw in (b"<html>private response</html>", b'{"model":NaN}', b'{"answers":{},"answers":{}}', b"x" * (transport.MAX_RESPONSE_BYTES + 1), b"[" * 1500 + b"]" * 1500):
                response.read.return_value = raw
                with self.assertRaises(transport.ServiceUnavailable) as raised:
                    client.evaluate({"task": "example"}, self.questions)
                self.assertEqual(raised.exception.code, "invalid_response")
            connection.request.side_effect = socket.timeout("private failure details")
            with self.assertRaises(transport.ServiceUnavailable) as raised:
                client.evaluate({"task": "example"}, self.questions)
            self.assertEqual(raised.exception.code, "timeout")
            self.assertNotIn("private failure", str(raised.exception))

    def test_request_deadline_interrupts_trickled_headers_and_body(self):
        for phase in ("headers", "body"):
            with self.subTest(phase=phase):
                incoming, peer = socket.socketpair()
                connection = transport.http.client.HTTPConnection("api.typesafe.ai")
                connection.connect = lambda: setattr(connection, "sock", incoming)
                stopped = threading.Event()

                def send():
                    try:
                        if phase == "body":
                            peer.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 500\r\n\r\n")
                        while not stopped.wait(.01):
                            peer.sendall(b"x")
                    except OSError:
                        pass

                thread = threading.Thread(target=send, daemon=True)
                thread.start()
                try:
                    with patch.dict(os.environ, {"TYPESAFE_API_KEY": "fake-test-key"}), patch.object(transport.http.client, "HTTPSConnection", return_value=connection):
                        started = time.monotonic()
                        with self.assertRaises(transport.ServiceUnavailable) as raised:
                            transport.TypeSafeClient(timeout=.06).evaluate({"task": "example"}, self.questions)
                        self.assertEqual(raised.exception.code, "timeout")
                        self.assertLess(time.monotonic() - started, .8)
                finally:
                    stopped.set()
                    peer.close()
                    incoming.close()
                    thread.join(.2)

    def test_dns_resolution_wait_is_bounded_and_does_not_send_a_request(self):
        release = threading.Event()
        def resolve(*args, **kwargs):
            release.wait(2)
            return []
        try:
            with patch.object(transport.socket, "getaddrinfo", side_effect=resolve), patch.object(transport.socket, "socket") as factory:
                started = time.monotonic()
                with self.assertRaises(TimeoutError):
                    transport._deadline_socket(("api.typesafe.ai", 443), .05, None, deadline=started + .05)
                self.assertLess(time.monotonic() - started, .5)
                factory.assert_not_called()
        finally:
            release.set()

    def test_stalled_dns_resolvers_have_bounded_daemon_workers(self):
        release = threading.Event()
        workers = []
        def resolve(*args, **kwargs):
            workers.append(threading.current_thread())
            release.wait(2)
            return []
        def call():
            with self.assertRaises(TimeoutError):
                transport._deadline_socket(("api.typesafe.ai", 443), .04, None, deadline=time.monotonic() + .04)
        try:
            with patch.object(transport, "_DNS_SLOTS", threading.BoundedSemaphore(2)), patch.object(transport.socket, "getaddrinfo", side_effect=resolve):
                with ThreadPoolExecutor(max_workers=6) as executor:
                    list(executor.map(lambda _: call(), range(12)))
                self.assertLessEqual(len(workers), 2)
                self.assertTrue(all(worker.daemon for worker in workers))
                release.set()
                for worker in workers:
                    worker.join(.2)
        finally:
            release.set()


if __name__ == "__main__":
    unittest.main()
