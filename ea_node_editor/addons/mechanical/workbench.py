# Purpose: Launch and own local Workbench without the SDK's WMI parent escape.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_open_model.py

from __future__ import annotations

import base64
import ctypes
import json
import socket
import subprocess
import time
import uuid
from ctypes import wintypes
from pathlib import Path
from typing import Any

from ea_node_editor.addons.mechanical.owner_process import (
    _WindowsKillJob,
    _creation_time_for_pid,
)


class OwnedWorkbench:
    def __init__(self, client: Any, process: subprocess.Popen[Any], job: _WindowsKillJob) -> None:
        self._client, self._process, self._job = client, process, job
        self.identity = {
            "pid": process.pid,
            "creation_time_ns": _creation_time_for_pid(process.pid),
        }
        self._closed = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)

    def exit(self) -> None:
        if self._closed:
            return
        try:
            self._client.exit()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        finally:
            self._job.close()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._closed = True


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def launch_workbench_owner(*, release_code: int, show_gui: bool, client_workdir: str, server_workdir: str, timeout_sec: float = 120.0, **_options: Any) -> OwnedWorkbench:
    from ansys.tools.common.path import get_available_ansys_installations
    from ansys.workbench.core import connect_workbench
    import grpc

    root = get_available_ansys_installations().get(int(release_code))
    executable = Path(root or "") / "Framework" / "bin" / "Win64" / "RunWB2.exe"
    if not executable.is_file():
        raise RuntimeError(f"Workbench release {release_code} is not installed")
    work = Path(server_workdir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    port, token = _free_port(), uuid.uuid4().hex
    encoded = base64.b64encode(
        json.dumps(
            {"token": token, "workdir": work.as_posix(), "port": port},
            separators=(",", ":"),
        ).encode()
    ).decode("ascii")
    start = (
        "import base64,json\np=json.loads(base64.b64decode(" + repr(encoded)
        + ").decode('utf-8'))\n"
        "StartServer(EnvironmentPrefix=p['token'],WorkingDirectory=p['workdir'],"
        "PortToUse=p['port'],Security='wnua')"
    )
    args = [str(executable), "-I" if show_gui else "--start-and-wait"]
    if not show_gui:
        args.append("-nowindow")
    args.extend(("-E", start))
    flags = getattr(subprocess, "CREATE_SUSPENDED", 4)
    if not show_gui:
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    job = _WindowsKillJob()
    process = None
    try:
        process = subprocess.Popen(
            args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, creationflags=flags,
        )
        job.assign(process)
        status = ctypes.WinDLL("ntdll").NtResumeProcess(wintypes.HANDLE(int(process._handle)))
        if status:
            raise OSError(int(status), "NtResumeProcess failed")
        deadline = time.monotonic() + float(timeout_sec)
        while True:
            client = None
            try:
                client = connect_workbench(
                    port, client_workdir=client_workdir, host="localhost", security="wnua"
                )
                grpc.channel_ready_future(client.channel).result(
                    timeout=max(0.1, min(1.0, deadline - time.monotonic()))
                )
                if client.run_script_string(
                    "import json\nwb_script_result=json.dumps(True)"
                ) is True:
                    break
                client.exit()
                raise RuntimeError("Workbench health handshake was not accepted")
            except Exception:
                if client is not None:
                    client.exit()
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("Workbench server did not accept the owned connection")
                time.sleep(0.25)
        return OwnedWorkbench(client, process, job)
    except BaseException:
        job.close()
        if process is not None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        raise


__all__ = ["OwnedWorkbench", "launch_workbench_owner"]
