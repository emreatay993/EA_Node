from __future__ import annotations

import json
import os
import queue
import shlex
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from ea_node_editor.nodes.output_artifacts import (
    artifact_store_for_context,
    write_managed_output,
)
from ea_node_editor.nodes.types import NodeResult, NodeTypeSpec, PortSpec, PropertySpec

PROCESS_STREAM_CAPTURE_CHAR_LIMIT = 262_144
PROCESS_STREAM_QUEUE_SIZE = 256
PROCESS_STDERR_ERROR_TAIL_CHAR_LIMIT = 4_096
PROCESS_OUTPUT_MODE_MEMORY = "memory"
PROCESS_OUTPUT_MODE_STORED = "stored"
PROCESS_TRANSCRIPT_SUFFIX = ".log"
PROCESS_TRANSCRIPT_SUBDIRECTORY = "generated/process_run"


def normalize_args(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:  # noqa: BLE001
        pass
    return shlex.split(text, posix=False)


def normalize_env(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    text = str(value).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:  # noqa: BLE001
        return {}
    if isinstance(parsed, dict):
        return {str(key): str(item) for key, item in parsed.items()}
    return {}


def normalize_output_mode(value: Any) -> str:
    normalized = str(value or PROCESS_OUTPUT_MODE_MEMORY).strip().lower()
    if normalized not in {PROCESS_OUTPUT_MODE_MEMORY, PROCESS_OUTPUT_MODE_STORED}:
        raise ValueError(
            "Process Run output_mode must be either "
            f"{PROCESS_OUTPUT_MODE_MEMORY!r} or {PROCESS_OUTPUT_MODE_STORED!r}."
        )
    return normalized


def _discard_stored_transcript_entries(ctx, artifact_ids: tuple[str, ...]) -> None:  # noqa: ANN001
    if not artifact_ids:
        return
    store = artifact_store_for_context(ctx)
    store.discard_staged_entries(artifact_ids)


class ProcessRunNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="io.process_run",
            display_name="Process Run",
            category="Input / Output",
            icon="terminal",
            description="Executes an external command and captures stdout/stderr.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=False),
                PortSpec("command", "in", "data", "str", required=False),
                PortSpec("args", "in", "data", "list[str]", required=False),
                PortSpec("stdin_text", "in", "data", "str", required=False),
                PortSpec("stdout", "out", "data", "str", exposed=True),
                PortSpec("stderr", "out", "data", "str", exposed=True),
                PortSpec("exit_code", "out", "data", "int", exposed=True),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
                PortSpec("on_failed", "out", "failed", "any", exposed=True),
            ),
            properties=(
                PropertySpec("command", "str", "", "Command"),
                PropertySpec("args", "str", "[]", "Args"),
                PropertySpec(
                    "output_mode",
                    "enum",
                    PROCESS_OUTPUT_MODE_MEMORY,
                    "Output Mode",
                    enum_values=(PROCESS_OUTPUT_MODE_MEMORY, PROCESS_OUTPUT_MODE_STORED),
                    inline_editor="enum",
                ),
                PropertySpec("cwd", "path", "", "Working Directory"),
                PropertySpec("env", "json", {}, "Environment"),
                PropertySpec("timeout_sec", "float", 60.0, "Timeout (sec)"),
                PropertySpec("shell", "bool", False, "Use Shell"),
                PropertySpec("fail_on_nonzero", "bool", True, "Fail on Non-zero"),
                PropertySpec("encoding", "str", "utf-8", "Encoding"),
            ),
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        command = str(ctx.inputs.get("command", ctx.properties.get("command", ""))).strip()
        if not command:
            raise ValueError("Process Run requires a command.")

        args = normalize_args(ctx.inputs.get("args", ctx.properties.get("args", "[]")))
        stdin_text = str(ctx.inputs.get("stdin_text", ""))
        cwd_text = str(ctx.properties.get("cwd", "")).strip()
        cwd = cwd_text or None
        if cwd and not Path(cwd).exists():
            raise ValueError(f"Process Run working directory does not exist: {cwd}")

        output_mode = normalize_output_mode(ctx.properties.get("output_mode", PROCESS_OUTPUT_MODE_MEMORY))
        timeout_sec = float(ctx.properties.get("timeout_sec", 60.0))
        if timeout_sec <= 0:
            raise ValueError("Process Run timeout_sec must be > 0.")

        shell = bool(ctx.properties.get("shell", False))
        fail_on_nonzero = bool(ctx.properties.get("fail_on_nonzero", True))
        encoding = str(ctx.properties.get("encoding", "utf-8")).strip() or "utf-8"
        env_overrides = normalize_env(ctx.properties.get("env", {}))
        env = dict(os.environ)
        env.update(env_overrides)

        popen_args: Any
        if shell:
            popen_args = " ".join([command, *args]).strip()
        else:
            popen_args = [command, *args]

        process = subprocess.Popen(
            popen_args,
            cwd=cwd,
            env=env,
            shell=shell,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding=encoding,
            errors="replace",
        )

        def _cancel() -> None:
            if process.poll() is not None:
                return
            process.terminate()
            try:
                process.wait(timeout=0.6)
            except subprocess.TimeoutExpired:
                process.kill()
            finally:
                for stream in (process.stdin, process.stdout, process.stderr):
                    try:
                        if stream:
                            stream.close()
                    except OSError:
                        continue

        ctx.register_cancel(_cancel)

        if process.stdin:
            try:
                if stdin_text:
                    process.stdin.write(stdin_text)
                process.stdin.close()
            except OSError:
                pass

        def _append_bounded(
            chunks: deque[str],
            total_chars: int,
            text: str,
            *,
            limit: int = PROCESS_STREAM_CAPTURE_CHAR_LIMIT,
        ) -> tuple[int, bool]:
            if not text:
                return total_chars, False
            chunks.append(text)
            total_chars += len(text)
            truncated = False
            while total_chars > limit and chunks:
                total_chars -= len(chunks.popleft())
                truncated = True
            return total_chars, truncated

        def _create_stored_transcript(output_key: str):
            return write_managed_output(
                ctx,
                output_key=output_key,
                default_suffix=PROCESS_TRANSCRIPT_SUFFIX,
                managed_subdirectory=PROCESS_TRANSCRIPT_SUBDIRECTORY,
                write_payload=lambda output_path: output_path.write_text("", encoding=encoding),
            )

        stored_stdout = None
        stored_stderr = None
        stdout_stream = None
        stderr_stream = None
        keep_stored_outputs = False
        stderr_error_tail: deque[str] = deque()
        stderr_error_tail_chars = 0
        stored_artifact_ids: tuple[str, ...] = ()

        if output_mode == PROCESS_OUTPUT_MODE_STORED:
            stored_stdout = _create_stored_transcript("stdout")
            stored_stderr = _create_stored_transcript("stderr")
            stored_artifact_ids = (
                stored_stdout.artifact_ref.artifact_id,
                stored_stderr.artifact_ref.artifact_id,
            )
            stdout_stream = stored_stdout.path.open("a", encoding=encoding)
            stderr_stream = stored_stderr.path.open("a", encoding=encoding)

        stream_queue: queue.Queue[tuple[str, str]] = queue.Queue(maxsize=PROCESS_STREAM_QUEUE_SIZE)
        dropped_chunks: dict[str, int] = {"stdout": 0, "stderr": 0}
        dropped_lock = threading.Lock()

        def _stream_reader(stream_name: str, stream: Any) -> None:
            try:
                for chunk in iter(stream.readline, ""):
                    if not chunk:
                        break
                    try:
                        stream_queue.put_nowait((stream_name, chunk))
                    except queue.Full:
                        with dropped_lock:
                            dropped_chunks[stream_name] = dropped_chunks.get(stream_name, 0) + 1
            except OSError:
                return

        reader_threads: list[threading.Thread] = []
        if process.stdout is not None:
            stdout_reader = threading.Thread(
                target=_stream_reader,
                args=("stdout", process.stdout),
                daemon=True,
                name="process-run-stdout-reader",
            )
            stdout_reader.start()
            reader_threads.append(stdout_reader)
        if process.stderr is not None:
            stderr_reader = threading.Thread(
                target=_stream_reader,
                args=("stderr", process.stderr),
                daemon=True,
                name="process-run-stderr-reader",
            )
            stderr_reader.start()
            reader_threads.append(stderr_reader)

        started_at = time.monotonic()
        stdout_chunks: deque[str] = deque()
        stderr_chunks: deque[str] = deque()
        stdout_chars = 0
        stderr_chars = 0
        stdout_truncated = False
        stderr_truncated = False
        try:
            while True:
                if ctx.should_stop():
                    _cancel()
                    raise InterruptedError("run_stop_requested")
                elapsed = time.monotonic() - started_at
                if elapsed > timeout_sec:
                    _cancel()
                    raise TimeoutError(f"Process Run timed out after {timeout_sec:.2f} seconds.")

                drained_any = False
                try:
                    while True:
                        stream_name, chunk = stream_queue.get_nowait()
                        drained_any = True
                        message = chunk.rstrip("\r\n")
                        for line in message.splitlines():
                            if line:
                                ctx.emit_log("info", f"[{stream_name}] {line}")
                        if (
                            output_mode == PROCESS_OUTPUT_MODE_STORED
                            and stream_name == "stdout"
                            and stdout_stream is not None
                        ):
                            stdout_stream.write(chunk)
                            stdout_stream.flush()
                        elif (
                            output_mode == PROCESS_OUTPUT_MODE_STORED
                            and stream_name == "stderr"
                            and stderr_stream is not None
                        ):
                            stderr_stream.write(chunk)
                            stderr_stream.flush()
                            stderr_error_tail_chars, _was_truncated = _append_bounded(
                                stderr_error_tail,
                                stderr_error_tail_chars,
                                chunk,
                                limit=PROCESS_STDERR_ERROR_TAIL_CHAR_LIMIT,
                            )
                        elif stream_name == "stdout":
                            stdout_chars, was_truncated = _append_bounded(stdout_chunks, stdout_chars, chunk)
                            stdout_truncated = stdout_truncated or was_truncated
                        elif stream_name == "stderr":
                            stderr_chars, was_truncated = _append_bounded(stderr_chunks, stderr_chars, chunk)
                            stderr_truncated = stderr_truncated or was_truncated
                except queue.Empty:
                    pass

                if process.poll() is not None and all(not thread.is_alive() for thread in reader_threads):
                    if stream_queue.empty():
                        break
                    continue
                if not drained_any:
                    time.sleep(0.02)

            for thread in reader_threads:
                thread.join(timeout=0.1)

            try:
                while True:
                    stream_name, chunk = stream_queue.get_nowait()
                    message = chunk.rstrip("\r\n")
                    for line in message.splitlines():
                        if line:
                            ctx.emit_log("info", f"[{stream_name}] {line}")
                    if (
                        output_mode == PROCESS_OUTPUT_MODE_STORED
                        and stream_name == "stdout"
                        and stdout_stream is not None
                    ):
                        stdout_stream.write(chunk)
                        stdout_stream.flush()
                    elif (
                        output_mode == PROCESS_OUTPUT_MODE_STORED
                        and stream_name == "stderr"
                        and stderr_stream is not None
                    ):
                        stderr_stream.write(chunk)
                        stderr_stream.flush()
                        stderr_error_tail_chars, _was_truncated = _append_bounded(
                            stderr_error_tail,
                            stderr_error_tail_chars,
                            chunk,
                            limit=PROCESS_STDERR_ERROR_TAIL_CHAR_LIMIT,
                        )
                    elif stream_name == "stdout":
                        stdout_chars, was_truncated = _append_bounded(stdout_chunks, stdout_chars, chunk)
                        stdout_truncated = stdout_truncated or was_truncated
                    elif stream_name == "stderr":
                        stderr_chars, was_truncated = _append_bounded(stderr_chunks, stderr_chars, chunk)
                        stderr_truncated = stderr_truncated or was_truncated
            except queue.Empty:
                pass

            exit_code = int(process.returncode or 0)
            stdout_text = "".join(stdout_chunks)
            stderr_text = "".join(stderr_chunks)

            if stdout_truncated:
                ctx.emit_log(
                    "warning",
                    (
                        "Process Run stdout capture exceeded limit and was truncated to the most recent "
                        f"{PROCESS_STREAM_CAPTURE_CHAR_LIMIT} characters."
                    ),
                )
            if stderr_truncated:
                ctx.emit_log(
                    "warning",
                    (
                        "Process Run stderr capture exceeded limit and was truncated to the most recent "
                        f"{PROCESS_STREAM_CAPTURE_CHAR_LIMIT} characters."
                    ),
                )
            with dropped_lock:
                dropped_stdout = int(dropped_chunks.get("stdout", 0))
                dropped_stderr = int(dropped_chunks.get("stderr", 0))
            if dropped_stdout > 0 or dropped_stderr > 0:
                ctx.emit_log(
                    "warning",
                    (
                        "Process Run dropped streamed chunks due to output backpressure "
                        f"(stdout={dropped_stdout}, stderr={dropped_stderr})."
                    ),
                )

            if fail_on_nonzero and exit_code != 0:
                if output_mode == PROCESS_OUTPUT_MODE_STORED:
                    stderr_tail = "".join(stderr_error_tail).strip()
                    transcript_hint = f" stderr_tail={stderr_tail!r}" if stderr_tail else ""
                    raise RuntimeError(
                        "Process Run returned non-zero exit code "
                        f"{exit_code}. stored_transcripts_discarded=True.{transcript_hint}"
                    )
                raise RuntimeError(
                    f"Process Run returned non-zero exit code {exit_code}. stderr={stderr_text.strip()}"
                )
            if output_mode == PROCESS_OUTPUT_MODE_STORED and stored_stdout is not None and stored_stderr is not None:
                keep_stored_outputs = True
                return NodeResult(
                    outputs={
                        "stdout": stored_stdout.artifact_ref,
                        "stderr": stored_stderr.artifact_ref,
                        "exit_code": exit_code,
                        "exec_out": True,
                    }
                )
            return NodeResult(
                outputs={
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "exit_code": exit_code,
                    "exec_out": True,
                }
            )
        finally:
            for thread in reader_threads:
                if thread.is_alive():
                    thread.join(timeout=0.1)
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    if stream:
                        stream.close()
                except OSError:
                    continue
            for transcript_stream in (stdout_stream, stderr_stream):
                if transcript_stream is None:
                    continue
                try:
                    transcript_stream.close()
                except OSError:
                    continue
            if not keep_stored_outputs:
                _discard_stored_transcript_entries(ctx, stored_artifact_ids)
