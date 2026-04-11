"""HPC cluster job nodes: submit, monitor, status routing, and result fetching."""

from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path
from typing import Any

from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec


def _run_ssh_command(host: str, user: str, command: str, ctx: ExecutionContext) -> str:
    """Run a command on a remote host via SSH. Uses paramiko if available, falls back to system ssh."""
    try:
        import paramiko  # type: ignore[import-untyped]

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(host, username=user, timeout=15)
            _stdin, stdout, stderr = client.exec_command(command, timeout=30)
            output = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
            if err:
                ctx.emit_log("warning", f"SSH stderr: {err}")
            return output
        finally:
            client.close()
    except ImportError:
        ssh_cmd = ["ssh", f"{user}@{host}" if user else host, command]
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        if result.stderr.strip():
            ctx.emit_log("warning", f"SSH stderr: {result.stderr.strip()}")
        if result.returncode != 0:
            raise RuntimeError(f"SSH command failed (exit {result.returncode}): {result.stderr.strip()}")
        return result.stdout.strip()


class HPCSubmitNodePlugin:
    """Submits a job script to an HPC scheduler (Slurm, PBS, or LSF)."""

    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="hpc.submit",
            display_name="HPC Submit Job",
    category_path=("HPC",),
            icon="cloud_upload",
            description="Submits a job to an HPC cluster scheduler and outputs the job ID.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=False),
                PortSpec("script_path", "in", "data", "path", required=False),
                PortSpec("job_id", "out", "data", "str", exposed=True),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
                PortSpec("on_failed", "out", "failed", "any", exposed=True),
            ),
            properties=(
                PropertySpec("scheduler", "enum", "slurm", "Scheduler",
                             enum_values=("slurm", "pbs", "lsf")),
                PropertySpec("script_path", "path", "", "Job Script Path"),
                PropertySpec("host", "str", "", "SSH Host"),
                PropertySpec("user", "str", "", "SSH User"),
                PropertySpec("extra_args", "str", "", "Extra Submit Args"),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        scheduler = str(ctx.properties.get("scheduler", "slurm"))
        script_path = str(
            ctx.inputs.get("script_path", ctx.properties.get("script_path", ""))
        ).strip()
        if not script_path:
            raise ValueError("HPC Submit requires a job script path.")

        host = str(ctx.properties.get("host", "")).strip()
        user = str(ctx.properties.get("user", "")).strip()
        extra_args = str(ctx.properties.get("extra_args", "")).strip()

        submit_commands = {
            "slurm": f"sbatch {extra_args} {script_path}",
            "pbs": f"qsub {extra_args} {script_path}",
            "lsf": f"bsub {extra_args} < {script_path}",
        }
        command = submit_commands.get(scheduler, submit_commands["slurm"])

        ctx.emit_log("info", f"Submitting job: {command}")

        if host:
            output = _run_ssh_command(host, user, command, ctx)
        else:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Submit failed: {result.stderr.strip()}")
            output = result.stdout.strip()

        job_id = output.split()[-1] if output else ""
        ctx.emit_log("info", f"Job submitted: {job_id}")
        return NodeResult(outputs={"job_id": job_id, "exec_out": True})


class HPCMonitorNodePlugin:
    """Polls an HPC job until it reaches a terminal state."""

    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="hpc.monitor",
            display_name="HPC Monitor Job",
    category_path=("HPC",),
            icon="monitor_heart",
            description="Polls a running HPC job until it completes or fails.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=False),
                PortSpec("job_id", "in", "data", "str", required=True),
                PortSpec("status", "out", "data", "str", exposed=True),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
                PortSpec("on_failed", "out", "failed", "any", exposed=True),
            ),
            properties=(
                PropertySpec("scheduler", "enum", "slurm", "Scheduler",
                             enum_values=("slurm", "pbs", "lsf")),
                PropertySpec("host", "str", "", "SSH Host"),
                PropertySpec("user", "str", "", "SSH User"),
                PropertySpec("poll_interval_sec", "float", 30.0, "Poll Interval (sec)"),
                PropertySpec("timeout_sec", "float", 86400.0, "Timeout (sec)"),
            ),
            is_async=True,
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        job_id = str(ctx.inputs.get("job_id", "")).strip()
        if not job_id:
            raise ValueError("HPC Monitor requires a job_id input.")

        scheduler = str(ctx.properties.get("scheduler", "slurm"))
        host = str(ctx.properties.get("host", "")).strip()
        user = str(ctx.properties.get("user", "")).strip()
        poll_interval = max(5.0, float(ctx.properties.get("poll_interval_sec", 30.0)))
        timeout = float(ctx.properties.get("timeout_sec", 86400.0))

        status_commands = {
            "slurm": f"sacct -j {job_id} --format=State --noheader -P | head -1",
            "pbs": f"qstat -f {job_id} | grep job_state | awk '{{print $3}}'",
            "lsf": f"bjobs -noheader -o stat {job_id}",
        }
        command = status_commands.get(scheduler, status_commands["slurm"])

        terminal_states = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL",
                           "C", "E", "EXIT", "DONE"}

        started_at = time.monotonic()
        last_status = ""

        while not ctx.should_stop():
            elapsed = time.monotonic() - started_at
            if elapsed > timeout:
                raise TimeoutError(f"HPC Monitor timed out after {timeout:.0f}s for job {job_id}")

            try:
                if host:
                    output = _run_ssh_command(host, user, command, ctx)
                else:
                    result = subprocess.run(
                        command, shell=True, capture_output=True, text=True, timeout=30,
                    )
                    output = result.stdout.strip()
            except Exception as exc:  # noqa: BLE001
                ctx.emit_log("warning", f"Status check failed: {exc}")
                time.sleep(poll_interval)
                continue

            status = output.strip().upper()
            if status != last_status:
                ctx.emit_log("info", f"Job {job_id} status: {status}")
                last_status = status

            if status in terminal_states:
                is_success = status in {"COMPLETED", "C", "DONE"}
                if not is_success:
                    raise RuntimeError(f"Job {job_id} ended with status: {status}")
                return NodeResult(outputs={"status": status, "exec_out": True})

            time.sleep(poll_interval)

        raise InterruptedError("run_stop_requested")

    async def async_execute(self, ctx: ExecutionContext) -> NodeResult:
        """Non-blocking version that uses asyncio.sleep between polls."""
        job_id = str(ctx.inputs.get("job_id", "")).strip()
        if not job_id:
            raise ValueError("HPC Monitor requires a job_id input.")

        scheduler = str(ctx.properties.get("scheduler", "slurm"))
        host = str(ctx.properties.get("host", "")).strip()
        user = str(ctx.properties.get("user", "")).strip()
        poll_interval = max(5.0, float(ctx.properties.get("poll_interval_sec", 30.0)))
        timeout = float(ctx.properties.get("timeout_sec", 86400.0))

        status_commands = {
            "slurm": f"sacct -j {job_id} --format=State --noheader -P | head -1",
            "pbs": f"qstat -f {job_id} | grep job_state | awk '{{print $3}}'",
            "lsf": f"bjobs -noheader -o stat {job_id}",
        }
        command = status_commands.get(scheduler, status_commands["slurm"])
        terminal_states = {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL",
                           "C", "E", "EXIT", "DONE"}

        started_at = time.monotonic()
        last_status = ""

        while not ctx.should_stop():
            elapsed = time.monotonic() - started_at
            if elapsed > timeout:
                raise TimeoutError(f"HPC Monitor timed out after {timeout:.0f}s for job {job_id}")

            try:
                if host:
                    output = _run_ssh_command(host, user, command, ctx)
                else:
                    proc = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: subprocess.run(
                            command, shell=True, capture_output=True, text=True, timeout=30,
                        ),
                    )
                    output = proc.stdout.strip()
            except Exception as exc:  # noqa: BLE001
                ctx.emit_log("warning", f"Status check failed: {exc}")
                await asyncio.sleep(poll_interval)
                continue

            status = output.strip().upper()
            if status != last_status:
                ctx.emit_log("info", f"Job {job_id} status: {status}")
                last_status = status

            if status in terminal_states:
                is_success = status in {"COMPLETED", "C", "DONE"}
                if not is_success:
                    raise RuntimeError(f"Job {job_id} ended with status: {status}")
                return NodeResult(outputs={"status": status, "exec_out": True})

            await asyncio.sleep(poll_interval)

        raise InterruptedError("run_stop_requested")


class HPCOnStatusNodePlugin:
    """Routes execution based on an HPC job status string."""

    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="hpc.on_status",
            display_name="HPC On Status",
    category_path=("HPC",),
            icon="alt_route",
            description="Routes to different outputs based on job status (completed, failed, other).",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=False),
                PortSpec("status", "in", "data", "str", required=True),
                PortSpec("on_completed", "out", "exec", "exec", exposed=True),
                PortSpec("on_failed", "out", "failed", "any", exposed=True),
                PortSpec("on_other", "out", "exec", "exec", exposed=True),
                PortSpec("status_out", "out", "data", "str", exposed=True),
            ),
            properties=(),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        status = str(ctx.inputs.get("status", "")).strip().upper()
        success_states = {"COMPLETED", "C", "DONE"}
        failure_states = {"FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "E", "EXIT"}

        outputs: dict[str, Any] = {"status_out": status}
        if status in success_states:
            outputs["on_completed"] = True
        elif status in failure_states:
            raise RuntimeError(f"Job ended with failure status: {status}")
        else:
            outputs["on_other"] = True

        return NodeResult(outputs=outputs)


class HPCFetchResultNodePlugin:
    """Downloads result files from an HPC cluster."""

    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="hpc.fetch_result",
            display_name="HPC Fetch Results",
    category_path=("HPC",),
            icon="cloud_download",
            description="Copies output files from a remote HPC host to a local directory.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=False),
                PortSpec("remote_path", "in", "data", "path", required=False),
                PortSpec("local_path", "out", "data", "path", exposed=True),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
                PortSpec("on_failed", "out", "failed", "any", exposed=True),
            ),
            properties=(
                PropertySpec("remote_path", "str", "", "Remote Path"),
                PropertySpec("local_dir", "path", ".", "Local Directory"),
                PropertySpec("host", "str", "", "SSH Host"),
                PropertySpec("user", "str", "", "SSH User"),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        remote_path = str(
            ctx.inputs.get("remote_path", ctx.properties.get("remote_path", ""))
        ).strip()
        if not remote_path:
            raise ValueError("HPC Fetch Results requires a remote path.")

        local_dir = str(ctx.properties.get("local_dir", ".")).strip() or "."
        host = str(ctx.properties.get("host", "")).strip()
        user = str(ctx.properties.get("user", "")).strip()

        local_path = Path(local_dir)
        local_path.mkdir(parents=True, exist_ok=True)

        remote_spec = f"{user}@{host}:{remote_path}" if user else f"{host}:{remote_path}"

        if host:
            try:
                import paramiko  # type: ignore[import-untyped]

                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    client.connect(host, username=user, timeout=15)
                    sftp = client.open_sftp()
                    try:
                        filename = Path(remote_path).name
                        dest = local_path / filename
                        sftp.get(remote_path, str(dest))
                    finally:
                        sftp.close()
                finally:
                    client.close()
                result_path = str(dest)
            except ImportError:
                scp_cmd = ["scp", "-r", remote_spec, str(local_path)]
                proc = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=300)
                if proc.returncode != 0:
                    raise RuntimeError(f"SCP failed: {proc.stderr.strip()}")
                result_path = str(local_path / Path(remote_path).name)
        else:
            raise ValueError("HPC Fetch Results requires an SSH host for remote file transfer.")

        ctx.emit_log("info", f"Fetched {remote_path} -> {result_path}")
        return NodeResult(outputs={"local_path": result_path, "exec_out": True})
