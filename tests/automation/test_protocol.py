# Purpose: Pin the automation wire contract: NDJSON codec, hello handshake, request defaults/clamps, error envelope and hints.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_protocol.py
from __future__ import annotations

import json
import unittest

from ea_node_editor.automation import errors, protocol


class ProtocolCodecTests(unittest.TestCase):
    def test_request_round_trips_and_applies_defaults(self) -> None:
        request = protocol.AutomationRequest.from_dict({"id": "r1", "op": "node.add", "params": {"x": 1}})
        self.assertEqual(request.id, "r1")
        self.assertEqual(request.op, "node.add")
        self.assertEqual(request.params, {"x": 1})
        self.assertEqual(request.timeout_s, protocol.DEFAULT_REQUEST_TIMEOUT_S)
        frame = protocol.encode_frame(request.to_dict())
        self.assertTrue(frame.endswith(b"\n"))
        decoded = protocol.AutomationRequest.from_dict(protocol.decode_frame(frame))
        self.assertEqual(decoded, request)

    def test_request_rejects_missing_op_and_non_object_params(self) -> None:
        with self.assertRaises(protocol.FrameError):
            protocol.AutomationRequest.from_dict({"id": "r1", "params": {}})
        with self.assertRaises(protocol.FrameError):
            protocol.AutomationRequest.from_dict({"id": "r1", "op": "x.y", "params": [1]})

    def test_request_timeout_is_clamped(self) -> None:
        low = protocol.AutomationRequest.from_dict({"op": "a.b", "timeout_s": -5})
        high = protocol.AutomationRequest.from_dict({"op": "a.b", "timeout_s": 1e9})
        junk = protocol.AutomationRequest.from_dict({"op": "a.b", "timeout_s": "soon"})
        self.assertEqual(low.timeout_s, 0.0)
        self.assertEqual(high.timeout_s, protocol.MAX_REQUEST_TIMEOUT_S)
        self.assertEqual(junk.timeout_s, protocol.DEFAULT_REQUEST_TIMEOUT_S)

    def test_success_and_failure_responses_round_trip(self) -> None:
        ok = protocol.AutomationResponse.success("r1", {"node_id": "node_1"})
        ok_payload = json.loads(protocol.encode_frame(ok.to_dict()))
        self.assertEqual(ok_payload, {"id": "r1", "ok": True, "result": {"node_id": "node_1"}})
        self.assertEqual(protocol.AutomationResponse.from_dict(ok_payload), ok)

        error = errors.AutomationOpError(errors.NOT_FOUND, "missing", details={"id": "node_9"})
        failure = protocol.AutomationResponse.failure("r2", error)
        payload = failure.to_dict()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], errors.NOT_FOUND)
        self.assertEqual(payload["error"]["hint"], errors.default_hint(errors.NOT_FOUND))
        self.assertFalse(payload["error"]["retryable"])
        decoded = protocol.AutomationResponse.from_dict(json.loads(protocol.encode_frame(payload)))
        self.assertFalse(decoded.ok)
        assert decoded.error is not None
        self.assertEqual(decoded.error.code, errors.NOT_FOUND)
        self.assertEqual(decoded.error.details, {"id": "node_9"})

    def test_failure_without_error_envelope_becomes_protocol_error(self) -> None:
        decoded = protocol.AutomationResponse.from_dict({"id": "r3", "ok": False})
        assert decoded.error is not None
        self.assertEqual(decoded.error.code, errors.PROTOCOL_ERROR)

    def test_hello_round_trip_and_first_frame_guard(self) -> None:
        hello = protocol.HelloRequest(token="secret")
        payload = protocol.decode_frame(protocol.encode_frame(hello.to_dict()))
        self.assertEqual(payload["op"], protocol.HELLO_OP)
        self.assertEqual(protocol.HelloRequest.from_dict(payload), hello)
        with self.assertRaises(protocol.FrameError):
            protocol.HelloRequest.from_dict({"op": "node.add", "token": "x"})
        response = protocol.HelloResponse(app_version="0.1.0", instance_id="abc", pid=42, mode="private")
        self.assertEqual(protocol.HelloResponse.from_dict(response.to_dict()), response)
        self.assertEqual(response.to_dict()["protocol"], protocol.PROTOCOL_VERSION)

    def test_frame_size_cap_is_enforced_both_ways(self) -> None:
        big = {"id": "r", "op": "x.y", "params": {"blob": "a" * (protocol.MAX_FRAME_BYTES + 1)}}
        with self.assertRaises(protocol.FrameError):
            protocol.encode_frame(big)
        with self.assertRaises(protocol.FrameError):
            protocol.decode_frame(b"x" * (protocol.MAX_FRAME_BYTES + 1))

    def test_decode_rejects_non_object_and_invalid_json(self) -> None:
        with self.assertRaises(protocol.FrameError):
            protocol.decode_frame(b"[1, 2]\n")
        with self.assertRaises(protocol.FrameError):
            protocol.decode_frame(b"{not json}\n")

    def test_encode_frame_serializes_tuples_sets_and_paths(self) -> None:
        from pathlib import Path

        payload = protocol.decode_frame(protocol.encode_frame({"a": (1, 2), "b": {3}, "c": Path("x")}))
        self.assertEqual(payload["a"], [1, 2])
        self.assertEqual(payload["b"], [3])
        self.assertEqual(payload["c"], "x")


class ErrorContractTests(unittest.TestCase):
    def test_every_code_has_an_imperative_default_hint(self) -> None:
        self.assertEqual(len(errors.ERROR_CODES), len(set(errors.ERROR_CODES)))
        for code in errors.ERROR_CODES:
            with self.subTest(code=code):
                hint = errors.default_hint(code)
                self.assertTrue(hint.strip())
                self.assertNotEqual(hint, errors.default_hint("__unknown__"))

    def test_retryable_defaults_follow_code_and_can_be_overridden(self) -> None:
        self.assertTrue(errors.AutomationOpError(errors.APP_BUSY, "busy").retryable)
        self.assertFalse(errors.AutomationOpError(errors.NOT_FOUND, "gone").retryable)
        self.assertTrue(errors.AutomationOpError(errors.NOT_FOUND, "gone", retryable=True).retryable)

    def test_constructors_populate_details(self) -> None:
        bad = errors.invalid_params(["params.x: is required"], op="node.add")
        self.assertEqual(bad.code, errors.INVALID_PARAMS)
        self.assertEqual(bad.details["problems"], ["params.x: is required"])
        self.assertEqual(bad.details["op"], "node.add")
        missing = errors.not_found("Node", "node_1")
        self.assertEqual(missing.details, {"kind": "Node", "id": "node_1"})
        stub = errors.not_implemented("run.start")
        self.assertEqual(stub.code, errors.NOT_IMPLEMENTED)
        quiet = errors.no_effect("node.update", "nothing changed", details={"node_id": "n"})
        self.assertEqual(quiet.details, {"op": "node.update", "node_id": "n"})

    def test_error_dict_round_trip(self) -> None:
        original = errors.AutomationOpError(errors.TIMEOUT, "slow", hint="wait", details={"s": 3})
        restored = errors.AutomationOpError.from_dict(original.to_dict())
        self.assertEqual(restored.to_dict(), original.to_dict())


if __name__ == "__main__":
    unittest.main()
