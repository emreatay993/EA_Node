from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
import psutil

from ea_node_editor.addons.mechanical.owner_process import (
    MechanicalOwnerProcess,
    OwnerProtocolError,
    _creation_time_for_pid,
)


def test_real_owner_process_has_exact_identity_and_bounded_protocol() -> None:
    owner = MechanicalOwnerProcess()
    try:
        assert owner.identity.pid != os.getpid()
        assert owner.request(
            run_id="run",
            session_id="session",
            workspace_id="workspace",
            expected_revision=0,
            operation="health",
        ) == {"status": "ready"}
        with pytest.raises(OwnerProtocolError, match="Unsupported"):
            owner.request(
                run_id="run",
                session_id="session",
                workspace_id="workspace",
                expected_revision=0,
                operation="eval",
                args={"code": "1 + 1"},
            )
        with pytest.raises(OwnerProtocolError, match="identity"):
            owner.request(
                run_id="other",
                session_id="session",
                workspace_id="workspace",
                expected_revision=0,
                operation="health",
            )
    finally:
        owner.close()
    assert not owner.alive


def test_owner_protocol_rejects_non_data_arguments() -> None:
    owner = MechanicalOwnerProcess()
    try:
        with pytest.raises(TypeError):
            owner.request(
                run_id="run",
                session_id="session",
                workspace_id="workspace",
                expected_revision=0,
                operation="health",
                args={"value": object()},
            )
    finally:
        owner.close()


def test_owner_transport_crash_is_detected_without_touching_other_processes() -> None:
    owner = MechanicalOwnerProcess()
    pid = owner.identity.pid
    process = psutil.Process(pid)
    process.kill()
    process.wait(timeout=2.0)
    with pytest.raises(OwnerProtocolError, match="closed"):
        owner.request(
            run_id="run",
            session_id="session",
            workspace_id="workspace",
            expected_revision=0,
            operation="health",
            timeout_sec=0.1,
        )
    assert owner.identity.pid == pid and not owner.alive
    owner.close()


def _wait_for_identity(path: Path) -> dict:
    deadline = time.monotonic() + 10.0
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    return json.loads(path.read_text(encoding="utf-8"))


def _wait_owned_identity_dead(identity: dict) -> None:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            if _creation_time_for_pid(identity["pid"]) != identity["creation_time_ns"]:
                return
        except OSError:
            return
        time.sleep(0.02)
    pytest.fail(f"owned process identity survived: {identity}")


def test_missed_explicit_shutdown_does_not_orphan_owner(tmp_path: Path) -> None:
    identity_path = tmp_path / "owner.json"
    script = (
        "import json,os,sys; "
        "from ea_node_editor.addons.mechanical.owner_process import MechanicalOwnerProcess; "
        "o=MechanicalOwnerProcess(); "
        "open(sys.argv[1],'w').write(json.dumps({'pid':o.identity.pid,'creation_time_ns':o.identity.creation_time_ns})); "
        "os._exit(0)"
    )
    parent = subprocess.Popen([sys.executable, "-c", script, str(identity_path)])
    identity = _wait_for_identity(identity_path)
    parent.wait(timeout=10.0)
    _wait_owned_identity_dead(identity)


def test_forced_parent_death_does_not_orphan_owner(tmp_path: Path) -> None:
    identity_path = tmp_path / "owner.json"
    script = (
        "import json,sys,time; "
        "from ea_node_editor.addons.mechanical.owner_process import MechanicalOwnerProcess; "
        "o=MechanicalOwnerProcess(); "
        "open(sys.argv[1],'w').write(json.dumps({'pid':o.identity.pid,'creation_time_ns':o.identity.creation_time_ns})); "
        "time.sleep(60)"
    )
    parent = subprocess.Popen([sys.executable, "-c", script, str(identity_path)])
    identity = _wait_for_identity(identity_path)
    parent_process = psutil.Process(parent.pid)
    parent_process.kill()
    parent_process.wait(timeout=5.0)
    _wait_owned_identity_dead(identity)
