# Purpose: Tests for automation instance discovery files: atomic write, listing/liveness cleanup, find by id/mode, env override, malformed files.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_discovery.py
from __future__ import annotations

import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ea_node_editor.automation import discovery

DEAD_PID = 2**22 + 9999


def _record(instance_id: str, *, pid: int | None = None, mode: str = "visible", started_at: float = 100.0, port: int = 40000) -> discovery.InstanceRecord:
    return discovery.InstanceRecord(
        instance_id=instance_id,
        pid=os.getpid() if pid is None else pid,
        port=port,
        token="tok-" + instance_id,
        mode=mode,
        app_version="0.0-test",
        started_at=started_at,
        project_path="",
    )


class _DiscoveryDirTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="corex-discovery-")
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        env = patch.dict(os.environ, {discovery.ENV_DISCOVERY_DIR: str(self.dir)})
        env.start()
        self.addCleanup(env.stop)

    def alive(self, value: bool) -> None:
        patcher = patch.object(discovery, "_instance_alive", return_value=value)
        patcher.start()
        self.addCleanup(patcher.stop)


class InstanceDirTests(unittest.TestCase):
    def test_env_override_wins(self) -> None:
        with patch.dict(os.environ, {discovery.ENV_DISCOVERY_DIR: r"C:\somewhere\else" if os.name == "nt" else "/somewhere/else"}):
            self.assertEqual(discovery.instances_dir(), Path(os.environ[discovery.ENV_DISCOVERY_DIR]))
            self.assertEqual(discovery.instance_file_path("abc"), discovery.instances_dir() / "abc.json")

    def test_default_lives_under_local_appdata_then_appdata_then_home(self) -> None:
        with patch.dict(os.environ, {"LOCALAPPDATA": "L", "APPDATA": "A"}):
            os.environ.pop(discovery.ENV_DISCOVERY_DIR, None)
            self.assertEqual(discovery.instances_dir(), Path("L") / "COREX_Node_Editor" / "automation" / "instances")
        with patch.dict(os.environ, {"APPDATA": "A"}):
            os.environ.pop(discovery.ENV_DISCOVERY_DIR, None)
            os.environ.pop("LOCALAPPDATA", None)
            self.assertEqual(discovery.instances_dir(), Path("A") / "COREX_Node_Editor" / "automation" / "instances")
        with patch.dict(os.environ):
            for key in (discovery.ENV_DISCOVERY_DIR, "LOCALAPPDATA", "APPDATA"):
                os.environ.pop(key, None)
            self.assertEqual(discovery.instances_dir(), Path.home() / ".config" / "COREX_Node_Editor" / "automation" / "instances")


class WriteRemoveTests(_DiscoveryDirTestCase):
    def test_write_creates_parents_atomically_and_round_trips(self) -> None:
        nested = self.dir / "deeper" / "still"
        with patch.dict(os.environ, {discovery.ENV_DISCOVERY_DIR: str(nested)}):
            record = _record("abc123")
            path = discovery.write_instance_file(record)
            self.assertEqual(path, nested / "abc123.json")
            self.assertTrue(path.is_file())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), record.to_dict())
            self.assertEqual([p.name for p in nested.iterdir()], ["abc123.json"], "no temp files left behind")
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            # Overwriting the same id replaces the content.
            updated = _record("abc123", started_at=200.0, port=40001)
            self.assertEqual(discovery.write_instance_file(updated), path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["port"], 40001)
            self.assertEqual([p.name for p in nested.iterdir()], ["abc123.json"])

    def test_remove_returns_true_then_false(self) -> None:
        discovery.write_instance_file(_record("gone"))
        self.assertTrue(discovery.remove_instance_file("gone"))
        self.assertFalse(discovery.instance_file_path("gone").exists())
        self.assertFalse(discovery.remove_instance_file("gone"))
        self.assertFalse(discovery.remove_instance_file("never-existed"))

    def test_written_file_carries_the_token(self) -> None:
        path = discovery.write_instance_file(_record("tokened"))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["token"], "tok-tokened")

    def test_invalid_instance_ids_are_rejected(self) -> None:
        for bad in ("", "   ", "../escape", "a/b", "a\\b", ".hidden", "x" * 200):
            with self.subTest(instance_id=bad):
                with self.assertRaises(ValueError):
                    discovery.write_instance_file(_bad_record(bad))
                with self.assertRaises(ValueError):
                    discovery.remove_instance_file(bad)
        self.assertEqual(list(self.dir.iterdir()), [])


def _listening_socket() -> socket.socket:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(4)
    return listener


def _closed_port() -> int:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])
    probe.close()
    return port


class RecordSecretTests(unittest.TestCase):
    def test_repr_hides_the_token_but_the_discovery_payload_keeps_it(self) -> None:
        record = _record("secret-holder")
        self.assertNotIn(record.token, repr(record))
        self.assertIn("secret-holder", repr(record))
        self.assertEqual(record.to_dict()["token"], record.token)


def _bad_record(instance_id: str) -> discovery.InstanceRecord:
    return discovery.InstanceRecord(
        instance_id=instance_id, pid=os.getpid(), port=40000, token="t", mode="visible", app_version="v", started_at=1.0
    )


class ListInstancesTests(_DiscoveryDirTestCase):
    def test_missing_directory_lists_nothing(self) -> None:
        with patch.dict(os.environ, {discovery.ENV_DISCOVERY_DIR: str(self.dir / "absent")}):
            self.assertEqual(discovery.list_instances(), [])
            self.assertIsNone(discovery.find_instance())

    def test_live_records_are_listed_newest_first(self) -> None:
        self.alive(True)
        discovery.write_instance_file(_record("old", started_at=100.0))
        discovery.write_instance_file(_record("new", started_at=300.0))
        discovery.write_instance_file(_record("mid", started_at=200.0))
        self.assertEqual([r.instance_id for r in discovery.list_instances()], ["new", "mid", "old"])
        self.assertEqual([r.instance_id for r in discovery.list_instances(live_only=False)], ["new", "mid", "old"])

    def test_dead_pid_files_are_dropped_and_deleted(self) -> None:
        live = _record("live")
        dead = _record("dead", pid=DEAD_PID, started_at=999.0)
        discovery.write_instance_file(live)
        discovery.write_instance_file(dead)

        def probe(record: discovery.InstanceRecord) -> bool:
            return record.pid != DEAD_PID

        with patch.object(discovery, "_instance_alive", side_effect=probe):
            self.assertEqual([r.instance_id for r in discovery.list_instances(live_only=False)], ["dead", "live"])
            self.assertTrue(discovery.instance_file_path("dead").exists())
            self.assertEqual(discovery.list_instances(), [live])
        self.assertFalse(discovery.instance_file_path("dead").exists(), "stale file must be deleted")
        self.assertTrue(discovery.instance_file_path("live").exists())

    def test_malformed_and_foreign_files_are_skipped_but_kept(self) -> None:
        self.alive(True)
        good = _record("good")
        discovery.write_instance_file(good)
        (self.dir / "broken.json").write_text("{not json", encoding="utf-8")
        (self.dir / "list.json").write_text("[1, 2]", encoding="utf-8")
        (self.dir / "partial.json").write_text(json.dumps({"instance_id": "partial", "pid": 1}), encoding="utf-8")
        (self.dir / "badport.json").write_text(json.dumps({**good.to_dict(), "instance_id": "badport", "port": 0}), encoding="utf-8")
        (self.dir / "badpid.json").write_text(json.dumps({**good.to_dict(), "instance_id": "badpid", "pid": "x"}), encoding="utf-8")
        (self.dir / "notes.txt").write_text(json.dumps(good.to_dict()), encoding="utf-8")
        (self.dir / "binary.json").write_bytes(b"\xff\xfe\x00garbage")
        self.assertEqual(discovery.list_instances(), [good])
        self.assertEqual(discovery.list_instances(live_only=False), [good])
        remaining = sorted(p.name for p in self.dir.iterdir())
        self.assertEqual(
            remaining,
            ["badpid.json", "badport.json", "binary.json", "broken.json", "good.json", "list.json", "notes.txt", "partial.json"],
        )

    def test_record_with_missing_optional_fields_uses_defaults(self) -> None:
        self.alive(True)
        (self.dir / "minimal.json").write_text(
            json.dumps({"pid": os.getpid(), "port": 5000, "token": "t"}), encoding="utf-8"
        )
        [record] = discovery.list_instances()
        self.assertEqual(record.instance_id, "minimal")
        self.assertEqual(record.mode, "visible")
        self.assertEqual(record.app_version, "")
        self.assertEqual(record.started_at, 0.0)
        self.assertEqual(record.project_path, "")


class RealLivenessTests(_DiscoveryDirTestCase):
    """Liveness without patching: pid must exist *and* the loopback port must accept a connect."""

    def test_live_pid_and_open_port_is_listed_and_found(self) -> None:
        listener = _listening_socket()
        self.addCleanup(listener.close)
        record = _record("up", port=int(listener.getsockname()[1]))
        discovery.write_instance_file(record)
        self.assertEqual(discovery.list_instances(), [record])
        self.assertEqual(discovery.find_instance(), record)
        self.assertEqual(discovery.find_instance("up"), record)
        self.assertTrue(discovery.instance_file_path("up").exists())

    def test_live_pid_with_a_closed_port_is_dropped_and_deleted(self) -> None:
        record = _record("port-gone", port=_closed_port())
        discovery.write_instance_file(record)
        self.assertIsNone(discovery.find_instance("port-gone"))
        self.assertEqual(discovery.list_instances(), [])
        self.assertFalse(discovery.instance_file_path("port-gone").exists(), "stale file must be deleted")

    def test_dead_pid_is_dropped_even_when_its_port_is_open(self) -> None:
        if discovery._psutil is None:
            self.skipTest("psutil not installed")
        listener = _listening_socket()
        self.addCleanup(listener.close)
        record = _record("pid-gone", pid=DEAD_PID, port=int(listener.getsockname()[1]))
        discovery.write_instance_file(record)
        self.assertIsNone(discovery.find_instance())
        self.assertFalse(discovery.instance_file_path("pid-gone").exists())


class FindInstanceTests(_DiscoveryDirTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.alive(True)
        discovery.write_instance_file(_record("vis-old", mode="visible", started_at=100.0))
        discovery.write_instance_file(_record("priv-new", mode="private", started_at=300.0))
        discovery.write_instance_file(_record("vis-mid", mode="visible", started_at=200.0))

    def test_exact_id_match(self) -> None:
        self.assertEqual(discovery.find_instance("vis-old").instance_id, "vis-old")
        self.assertEqual(discovery.find_instance("priv-new").instance_id, "priv-new")
        self.assertEqual(discovery.find_instance("  vis-mid ").instance_id, "vis-mid")
        # An explicit id never falls back to another instance, even with a mode given.
        self.assertIsNone(discovery.find_instance("missing"))
        self.assertIsNone(discovery.find_instance("missing", mode="visible"))
        # An id wins over a contradicting mode.
        self.assertEqual(discovery.find_instance("priv-new", mode="visible").instance_id, "priv-new")

    def test_mode_preference_and_filters(self) -> None:
        self.assertEqual(discovery.find_instance().instance_id, "vis-mid", "visible preferred over a newer private one")
        self.assertEqual(discovery.find_instance(mode="visible").instance_id, "vis-mid")
        self.assertEqual(discovery.find_instance(mode="PRIVATE").instance_id, "priv-new")
        self.assertIsNone(discovery.find_instance(mode="headless"))

    def test_falls_back_to_any_mode_when_no_visible_instance(self) -> None:
        discovery.remove_instance_file("vis-old")
        discovery.remove_instance_file("vis-mid")
        self.assertEqual(discovery.find_instance().instance_id, "priv-new")
        self.assertIsNone(discovery.find_instance(mode="visible"))

    def test_find_ignores_dead_instances(self) -> None:
        with patch.object(discovery, "_instance_alive", return_value=False):
            self.assertIsNone(discovery.find_instance())
            self.assertIsNone(discovery.find_instance("vis-mid"))
        self.assertEqual(list(self.dir.iterdir()), [])


class LivenessProbeTests(unittest.TestCase):
    def test_pid_probe_recognises_this_process_and_rejects_a_bogus_pid(self) -> None:
        if discovery._psutil is None:
            self.skipTest("psutil not installed")
        self.assertTrue(discovery._pid_exists(os.getpid()))
        self.assertFalse(discovery._pid_exists(DEAD_PID))
        self.assertFalse(discovery._pid_exists(0))
        self.assertFalse(discovery._pid_exists(-5))

    def test_port_probe_detects_listener_and_closed_port(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        try:
            self.assertTrue(discovery._port_open(port))
        finally:
            listener.close()
        self.assertFalse(discovery._port_open(port))
        self.assertFalse(discovery._port_open(0))
        self.assertFalse(discovery._port_open(70000))

    def test_instance_alive_requires_a_live_pid_and_an_open_port(self) -> None:
        record = _record("probe", pid=DEAD_PID, port=1)
        cases = (
            # (pid exists, port open) -> alive
            ((True, True), True),
            ((True, False), False),
            ((False, True), False),
        )
        for (pid_alive, port_open), expected in cases:
            with self.subTest(pid_alive=pid_alive, port_open=port_open):
                with patch.object(discovery, "_psutil", object()), patch.object(
                    discovery, "_pid_exists", return_value=pid_alive
                ) as pid_probe, patch.object(discovery, "_port_open", return_value=port_open) as port_probe:
                    self.assertIs(discovery._instance_alive(record), expected)
                    pid_probe.assert_called_once_with(DEAD_PID)
                    if pid_alive:
                        port_probe.assert_called_once_with(1)
                    else:
                        port_probe.assert_not_called()
        # Without psutil only the port can be checked.
        with patch.object(discovery, "_psutil", None), patch.object(discovery, "_port_open", return_value=True) as port_probe:
            self.assertTrue(discovery._instance_alive(record))
            port_probe.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
