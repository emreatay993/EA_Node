# Purpose: Prove the automation launcher: mode validation, interpreter choice, spawn env/command per mode, startup polling/timeout/exit paths, and handle termination.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_launcher.py
from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

from ea_node_editor.automation import discovery, errors, gate, launcher

LOG_LINE = b"fake corex startup log line\n"
RECORD_PORT = 43210
_ENV_KEYS_TO_CLEAR = (
    "QT_QPA_PLATFORM",
    "QT_QPA_FONTDIR",
    "QT_QUICK_CONTROLS_STYLE",
    gate.ENV_SESSION_STATE_DIR,
    gate.ENV_ENABLED,
    gate.ENV_PORT,
    gate.ENV_INSTANCE_ID,
    gate.ENV_TOKEN,
    gate.ENV_MODE,
    launcher.BOOTSTRAP_SENTINEL,
)


@contextlib.contextmanager
def _clean_environ() -> Iterator[None]:
    with patch.dict(os.environ):
        for key in _ENV_KEYS_TO_CLEAR:
            os.environ.pop(key, None)
        yield


def _record(instance_id: str, *, port: int = RECORD_PORT, mode: str = "private") -> discovery.InstanceRecord:
    return discovery.InstanceRecord(
        instance_id=instance_id,
        pid=4242,
        port=port,
        token="tok",
        mode=mode,
        app_version="0.0-test",
        started_at=time.time(),
    )


class _FakeProcess:
    def __init__(self, args: list[str], **kwargs: Any) -> None:
        self.args = list(args)
        self.kwargs = kwargs
        self.pid = 4242
        self.returncode: int | None = None
        self.polls = 0
        self.terminate_calls = 0
        self.kill_calls = 0
        self.exit_code_after_polls: int | None = None
        self.hang_on_terminate = False
        self.survive_kill = False
        stdout = kwargs.get("stdout")
        if stdout is not None and hasattr(stdout, "write"):
            stdout.write(LOG_LINE)
            stdout.flush()

    def poll(self) -> int | None:
        self.polls += 1
        if self.returncode is None and self.exit_code_after_polls is not None and self.polls > self.exit_code_after_polls:
            self.returncode = 3
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        if self.returncode is None:
            raise subprocess.TimeoutExpired(self.args, timeout)
        return self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1
        if not self.hang_on_terminate:
            self.returncode = -15

    def kill(self) -> None:
        self.kill_calls += 1
        if not self.survive_kill:
            self.returncode = -9


class _PopenFactory:
    def __init__(self, **process_options: Any) -> None:
        self.processes: list[_FakeProcess] = []
        self.options = process_options

    def __call__(self, args: list[str], **kwargs: Any) -> _FakeProcess:
        process = _FakeProcess(args, **kwargs)
        for name, value in self.options.items():
            setattr(process, name, value)
        self.processes.append(process)
        return process


class _LauncherTestCase(unittest.TestCase):
    popen_options: dict[str, Any] = {}

    def setUp(self) -> None:
        self.popen = _PopenFactory(**self.popen_options)
        self._start_patch(patch.object(launcher.subprocess, "Popen", self.popen))
        self._start_patch(patch.object(launcher, "_POLL_INTERVAL_S", 0.005))
        self.probe = self._start_patch(patch.object(launcher, "_probe_port", return_value=True))
        self.remove_instance_file = self._start_patch(patch.object(discovery, "remove_instance_file", return_value=True))

    def _start_patch(self, patcher: Any) -> Any:
        started = patcher.start()
        self.addCleanup(patcher.stop)
        return started

    def _find_instance_after(self, misses: int, *, port: int = RECORD_PORT) -> list[str | None]:
        """Patch ``discovery.find_instance`` to miss ``misses`` times, then return a record for the requested id."""
        calls: list[str | None] = []

        def fake_find(instance_id: str | None = None, *, mode: str | None = None) -> discovery.InstanceRecord | None:
            calls.append(instance_id)
            if len(calls) <= misses:
                return None
            return _record(instance_id or "inst-any", port=port)

        self._start_patch(patch.object(discovery, "find_instance", side_effect=fake_find))
        return calls

    def _cleanup_handle(self, handle: launcher.CorexInstanceHandle) -> None:
        if handle.session_state_dir is not None:
            self.addCleanup(shutil.rmtree, handle.session_state_dir, True)
        self.addCleanup(handle.terminate)


class LaunchModeValidationTests(_LauncherTestCase):
    def test_invalid_mode_and_port_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            launcher.launch_corex("visible")
        with self.assertRaises(ValueError):
            launcher.launch_corex("private", port=70000)
        with self.assertRaises(ValueError):
            launcher.launch_corex("private", port="soon")  # type: ignore[arg-type]
        self.assertEqual(self.popen.processes, [])

    def test_python_executable_prefers_the_repo_venv_and_falls_back(self) -> None:
        fake_root = Path(tempfile.mkdtemp(prefix="corex-launcher-root-"))
        self.addCleanup(shutil.rmtree, fake_root, True)
        with patch.object(launcher, "_repo_root", return_value=fake_root):
            self.assertEqual(launcher.python_executable(), Path(sys.executable))
            candidate = launcher._venv_python(fake_root)
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(b"")
            self.assertEqual(launcher.python_executable(), candidate)
        self.assertIn("venv", candidate.parts)


class AttachModeTests(_LauncherTestCase):
    def test_attach_without_a_live_instance_raises_not_found(self) -> None:
        with patch.object(discovery, "find_instance", return_value=None) as find_instance:
            with self.assertRaises(errors.AutomationOpError) as raised:
                launcher.launch_corex("attach", instance_id="abc")
        find_instance.assert_called_once_with("abc")
        self.assertEqual(raised.exception.code, errors.NOT_FOUND)
        self.assertIn("--automation", raised.exception.hint)
        self.assertIn("private", raised.exception.hint)
        self.assertEqual(raised.exception.details["instance_id"], "abc")
        self.assertFalse(raised.exception.retryable)
        self.assertEqual(self.popen.processes, [])

    def test_attach_returns_a_non_owned_handle_whose_terminate_is_a_noop(self) -> None:
        record = _record("live-1", mode="visible")
        with patch.object(discovery, "find_instance", return_value=record):
            handle = launcher.launch_corex("attach")
        self.assertEqual(handle.record, record)
        self.assertFalse(handle.owned)
        self.assertFalse(handle.spawned)
        self.assertFalse(handle.private)
        self.assertIsNone(handle.poll())
        self.assertIsNone(handle.wait(timeout_s=0.01))
        handle.terminate()
        handle.terminate()
        self.assertTrue(handle.terminated)
        self.remove_instance_file.assert_not_called()
        self.assertEqual(self.popen.processes, [])

    def test_auto_attaches_when_an_instance_is_live(self) -> None:
        record = _record("live-2", mode="visible")
        with patch.object(discovery, "find_instance", return_value=record) as find_instance:
            handle = launcher.launch_corex("auto", headless=True)
        # auto only adopts visible instances; private/offscreen ones belong to whoever spawned them.
        find_instance.assert_called_once_with(None, mode="visible")
        self.assertFalse(handle.owned)
        self.assertIsNone(handle.process)
        self.assertEqual(self.popen.processes, [])

    def test_auto_never_adopts_a_private_instance_and_spawns_instead(self) -> None:
        calls: list[tuple[str | None, str | None]] = []

        def fake_find(instance_id: str | None = None, *, mode: str | None = None) -> discovery.InstanceRecord | None:
            calls.append((instance_id, mode))
            if instance_id:
                return _record(instance_id, mode="visible")  # the freshly spawned window
            # Only a live *private* instance exists: the visible filter finds nothing.
            return None if mode == "visible" else _record("someone-elses-private", mode="private")

        with _clean_environ(), patch.object(discovery, "find_instance", side_effect=fake_find):
            handle = launcher.launch_corex("auto")
        self._cleanup_handle(handle)
        self.assertEqual(calls[0], (None, "visible"))
        self.assertEqual(len(self.popen.processes), 1)
        self.assertTrue(handle.owned)
        self.assertNotEqual(handle.record.instance_id, "someone-elses-private")


class SpawnTests(_LauncherTestCase):
    def test_private_headless_spawn_composes_env_command_and_log(self) -> None:
        with _clean_environ():
            calls = self._find_instance_after(2)
            handle = launcher.launch_corex("private", headless=True, extra_env={"COREX_TEST_FLAG": "1"})
        self._cleanup_handle(handle)
        process = self.popen.processes[0]
        env = process.kwargs["env"]
        instance_id = handle.record.instance_id
        self.assertTrue(handle.owned)
        self.assertTrue(handle.spawned)
        self.assertTrue(handle.private)
        self.assertIs(handle.process, process)
        self.assertEqual(handle.record.port, RECORD_PORT)
        self.assertEqual(calls, [instance_id] * 3)
        self.probe.assert_called_with(RECORD_PORT)
        self.assertEqual(
            process.args,
            [
                str(launcher.python_executable()),
                "-m",
                "ea_node_editor.bootstrap",
                "--automation",
                "--automation-port",
                "0",
                "--automation-instance-id",
                instance_id,
            ],
        )
        self.assertEqual(process.kwargs["cwd"], str(launcher._repo_root()))
        self.assertEqual(process.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(process.kwargs["stderr"], subprocess.STDOUT)
        self.assertEqual(env["EA_NODE_EDITOR_BOOTSTRAPPED"], "1")
        self.assertEqual(env["COREX_AUTOMATION_ENABLED"], "1")
        self.assertEqual(env["COREX_AUTOMATION_PORT"], "0")
        self.assertEqual(env["COREX_AUTOMATION_INSTANCE_ID"], instance_id)
        self.assertTrue(env["COREX_AUTOMATION_TOKEN"])
        self.assertEqual(env["COREX_AUTOMATION_MODE"], "private")
        self.assertEqual(env["COREX_SESSION_STATE_DIR"], str(handle.session_state_dir))
        self.assertEqual(env["QT_QPA_PLATFORM"], "offscreen")
        self.assertEqual(env["COREX_TEST_FLAG"], "1")
        self.assertEqual(handle.env, env)
        if sys.platform == "win32":
            self.assertEqual(env["QT_QPA_FONTDIR"], "C:\\Windows\\Fonts")
            self.assertEqual(env["QT_QUICK_CONTROLS_STYLE"], "Basic")
            self.assertEqual(process.kwargs["creationflags"], subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            self.assertNotIn("QT_QPA_FONTDIR", env)
            self.assertNotIn("creationflags", process.kwargs)
        assert handle.session_state_dir is not None
        self.assertTrue(handle.session_state_dir.is_dir())
        self.assertTrue(handle.session_state_dir.name.startswith("corex-automation-"))
        self.assertEqual(handle.log_path, handle.session_state_dir / "corex-automation.log")
        self.assertEqual(handle.log_path.read_bytes(), LOG_LINE)
        handle.terminate()
        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.kill_calls, 0)
        self.assertFalse(handle.session_state_dir.exists())
        self.remove_instance_file.assert_called_once_with(instance_id)
        handle.terminate()
        self.assertEqual(process.terminate_calls, 1)
        self.remove_instance_file.assert_called_once()

    def test_private_windowed_spawn_has_no_platform_override(self) -> None:
        with _clean_environ():
            self._find_instance_after(1)
            handle = launcher.launch_corex("private", headless=False, instance_id="fixed-id", port=45000)
        self._cleanup_handle(handle)
        process = self.popen.processes[0]
        env = process.kwargs["env"]
        self.assertEqual(handle.record.instance_id, "fixed-id")
        self.assertEqual(env["COREX_AUTOMATION_INSTANCE_ID"], "fixed-id")
        self.assertEqual(env["COREX_AUTOMATION_PORT"], "45000")
        self.assertEqual(process.args[-3:], ["45000", "--automation-instance-id", "fixed-id"])
        self.assertEqual(env["COREX_AUTOMATION_MODE"], "private")
        self.assertIn("COREX_SESSION_STATE_DIR", env)
        self.assertNotIn("QT_QPA_PLATFORM", env)
        self.assertNotIn("QT_QPA_FONTDIR", env)
        if sys.platform == "win32":
            self.assertEqual(env["QT_QUICK_CONTROLS_STYLE"], "Basic")

    def test_quick_controls_style_is_not_overridden_when_already_set(self) -> None:
        with _clean_environ():
            os.environ["QT_QUICK_CONTROLS_STYLE"] = "Fusion"
            self._find_instance_after(0)
            handle = launcher.launch_corex("private")
        self._cleanup_handle(handle)
        self.assertEqual(self.popen.processes[0].kwargs["env"]["QT_QUICK_CONTROLS_STYLE"], "Fusion")

    def test_auto_spawns_a_visible_instance_with_its_own_session_dir(self) -> None:
        with _clean_environ():
            calls = self._find_instance_after(2)
            handle = launcher.launch_corex("auto", headless=True)
        self._cleanup_handle(handle)
        process = self.popen.processes[0]
        env = process.kwargs["env"]
        instance_id = handle.record.instance_id
        self.assertEqual(calls, [None, instance_id, instance_id])
        self.assertTrue(handle.owned)
        self.assertFalse(handle.private)
        self.assertFalse(handle.detached)
        self.assertEqual(env["COREX_AUTOMATION_MODE"], "visible")
        self.assertEqual(env["EA_NODE_EDITOR_BOOTSTRAPPED"], "1")
        self.assertEqual(env["COREX_AUTOMATION_ENABLED"], "1")
        self.assertNotIn("QT_QPA_PLATFORM", env)
        self.assertNotIn("QT_QPA_FONTDIR", env)
        # B2: a visible spawn must never restore or delete the user's autosave / last-session / staging.
        assert handle.session_state_dir is not None
        self.assertTrue(handle.session_state_dir.is_dir())
        self.assertTrue(handle.session_state_dir.name.startswith("corex-automation-"))
        self.assertEqual(env["COREX_SESSION_STATE_DIR"], str(handle.session_state_dir))
        # The startup log lives inside the session dir (no stray temp log file).
        self.assertEqual(handle.log_path, handle.session_state_dir / "corex-automation.log")
        self.assertEqual(handle.log_path.read_bytes(), LOG_LINE)
        self.assertTrue(handle.alive)
        handle.terminate()
        self.assertEqual(process.terminate_calls, 1)
        self.assertFalse(handle.alive)
        self.assertFalse(handle.session_state_dir.exists())
        self.remove_instance_file.assert_called_once_with(instance_id)

    def test_two_spawns_never_share_a_session_dir(self) -> None:
        def fake_find(instance_id: str | None = None, *, mode: str | None = None) -> discovery.InstanceRecord | None:
            return _record(instance_id) if instance_id else None  # nothing to adopt; each spawn publishes itself

        with _clean_environ(), patch.object(discovery, "find_instance", side_effect=fake_find):
            first = launcher.launch_corex("private")
            second = launcher.launch_corex("auto")
        self._cleanup_handle(first)
        self._cleanup_handle(second)
        self.assertIsNotNone(first.session_state_dir)
        self.assertIsNotNone(second.session_state_dir)
        self.assertNotEqual(first.session_state_dir, second.session_state_dir)

    def test_startup_waits_for_a_published_port_that_accepts_connections(self) -> None:
        records = iter([None, _record("wait-id", port=0), _record("wait-id"), _record("wait-id")])
        self.probe.side_effect = [False, True]
        with _clean_environ(), patch.object(discovery, "find_instance", side_effect=lambda *a, **k: next(records)):
            handle = launcher.launch_corex("private", instance_id="wait-id")
        self._cleanup_handle(handle)
        self.assertEqual(handle.record.port, RECORD_PORT)
        self.assertEqual(self.probe.call_count, 2)
        self.assertEqual([call.args for call in self.probe.call_args_list], [(RECORD_PORT,), (RECORD_PORT,)])

    def test_startup_timeout_terminates_the_process_and_reports_the_log_tail(self) -> None:
        with _clean_environ(), patch.object(discovery, "find_instance", return_value=None):
            with self.assertRaises(errors.AutomationOpError) as raised:
                launcher.launch_corex("private", instance_id="slow-id", startup_timeout_s=0.03)
        error = raised.exception
        process = self.popen.processes[0]
        self.assertEqual(error.code, errors.TIMEOUT)
        self.assertFalse(error.retryable)
        self.assertEqual(error.details["instance_id"], "slow-id")
        self.assertIn(LOG_LINE.decode().strip(), error.details["log_tail"])
        self.assertTrue(error.details["log_path"])
        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.returncode, -15)
        self.assertFalse(Path(process.kwargs["env"]["COREX_SESSION_STATE_DIR"]).exists())
        self.remove_instance_file.assert_called_once_with("slow-id")

    def test_popen_failure_raises_internal_and_removes_the_session_dir(self) -> None:
        for mode in ("private", "auto"):
            with self.subTest(mode=mode):
                created: list[Path] = []
                real_mkdtemp = tempfile.mkdtemp

                def recording_mkdtemp(*args: Any, **kwargs: Any) -> str:
                    path = real_mkdtemp(*args, **kwargs)
                    created.append(Path(path))
                    return path

                with _clean_environ(), patch.object(discovery, "find_instance", return_value=None), patch.object(
                    launcher.tempfile, "mkdtemp", side_effect=recording_mkdtemp
                ), patch.object(launcher.subprocess, "Popen", side_effect=OSError("no such interpreter")):
                    with self.assertRaises(errors.AutomationOpError) as raised:
                        launcher.launch_corex(mode)
                self.assertEqual(raised.exception.code, errors.INTERNAL)
                self.assertFalse(raised.exception.retryable)
                self.assertIn("no such interpreter", raised.exception.message)
                self.assertEqual(raised.exception.details["command"][1:4], ["-m", "ea_node_editor.bootstrap", "--automation"])
                self.assertEqual(len(created), 1)
                self.addCleanup(shutil.rmtree, created[0], True)
                self.assertFalse(created[0].exists())


class SpawnExitDuringStartupTests(_LauncherTestCase):
    popen_options = {"exit_code_after_polls": 1}

    def test_process_exit_during_startup_raises_internal_with_the_log_tail(self) -> None:
        with _clean_environ(), patch.object(discovery, "find_instance", return_value=None):
            with self.assertRaises(errors.AutomationOpError) as raised:
                launcher.launch_corex("private", instance_id="dead-id", startup_timeout_s=5.0)
        error = raised.exception
        process = self.popen.processes[0]
        self.assertEqual(error.code, errors.INTERNAL)
        self.assertFalse(error.retryable)
        self.assertEqual(error.details["exit_code"], 3)
        self.assertEqual(error.details["instance_id"], "dead-id")
        self.assertIn(LOG_LINE.decode().strip(), error.details["log_tail"])
        self.assertEqual(process.terminate_calls, 0)
        self.assertFalse(Path(process.kwargs["env"]["COREX_SESSION_STATE_DIR"]).exists())
        self.remove_instance_file.assert_called_once_with("dead-id")


class HandleTerminationTests(_LauncherTestCase):
    def test_terminate_escalates_to_kill_and_is_idempotent(self) -> None:
        process = _FakeProcess(["corex"])
        process.hang_on_terminate = True
        session_dir = Path(tempfile.mkdtemp(prefix="corex-launcher-test-"))
        self.addCleanup(shutil.rmtree, session_dir, True)
        handle = launcher.CorexInstanceHandle(
            record=_record("hang-id"),
            process=process,
            owned=True,
            session_state_dir=session_dir,
            log_path=session_dir / "corex-automation.log",
            env={gate.ENV_MODE: gate.MODE_PRIVATE},
        )
        self.assertTrue(handle.private)
        handle.terminate(timeout_s=0.01)
        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.kill_calls, 1)
        self.assertEqual(process.returncode, -9)
        self.assertEqual(handle.poll(), -9)
        self.assertFalse(session_dir.exists())
        self.remove_instance_file.assert_called_once_with("hang-id")
        handle.terminate(timeout_s=0.01)
        self.assertEqual(process.terminate_calls, 1)
        self.assertEqual(process.kill_calls, 1)
        self.remove_instance_file.assert_called_once()

    def test_owned_visible_handle_deletes_its_session_dir_and_ignores_discovery_errors(self) -> None:
        process = _FakeProcess(["corex"])
        session_dir = Path(tempfile.mkdtemp(prefix="corex-launcher-test-"))
        self.addCleanup(shutil.rmtree, session_dir, True)
        handle = launcher.CorexInstanceHandle(
            record=_record("vis-id", mode="visible"),
            process=process,
            owned=True,
            session_state_dir=session_dir,
            env={gate.ENV_MODE: gate.MODE_VISIBLE},
        )
        self.remove_instance_file.side_effect = ValueError("bad id")
        self.assertFalse(handle.private)
        handle.terminate()
        self.assertEqual(process.terminate_calls, 1)
        self.assertTrue(handle.terminated)
        self.assertFalse(session_dir.exists())

    def test_terminate_never_deletes_the_session_dir_of_a_live_process(self) -> None:
        process = _FakeProcess(["corex"])
        process.hang_on_terminate = True
        process.survive_kill = True
        session_dir = Path(tempfile.mkdtemp(prefix="corex-launcher-test-"))
        self.addCleanup(shutil.rmtree, session_dir, True)
        handle = launcher.CorexInstanceHandle(
            record=_record("zombie-id"),
            process=process,
            owned=True,
            session_state_dir=session_dir,
            env={gate.ENV_MODE: gate.MODE_PRIVATE},
        )
        handle.terminate(timeout_s=0.01)
        self.assertEqual((process.terminate_calls, process.kill_calls), (1, 1))
        self.assertTrue(handle.alive)
        self.assertTrue(handle.terminated)
        self.assertTrue(session_dir.is_dir(), "the session dir must survive while its process is alive")
        self.remove_instance_file.assert_not_called()

    def test_private_is_derived_from_the_record_when_env_is_empty(self) -> None:
        self.assertTrue(launcher.CorexInstanceHandle(record=_record("p", mode="private")).private)
        self.assertFalse(launcher.CorexInstanceHandle(record=_record("v", mode="visible")).private)


if __name__ == "__main__":
    unittest.main()
