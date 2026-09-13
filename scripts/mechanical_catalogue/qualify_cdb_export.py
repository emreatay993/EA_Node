# Purpose: Qualify no-solve CDB export/readback from an explicitly disposable native snapshot.
# Map: subsystems/addons.md
# Tests: tests/mechanical_catalogue/test_cdb_export.py
"""Run one bounded native CDB case; never build a mesh or run a numerical solve.

The input must be a disposable, native-staged .mechdb/.mechdat, not a user source.
Every run gets an isolated child job. Detailed output belongs in ignored artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import traceback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--analysis", default="")
    parser.add_argument("--content", choices=("mesh", "full"), default="mesh")
    parser.add_argument("--step", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = args.output_dir.resolve()
    if args.child:
        if sys.stdin.buffer.read(1) != b"1":
            return 2
        from ea_node_editor.addons.mechanical.cdb_export import export_cdb_snapshot
        try:
            receipt = export_cdb_snapshot(
                snapshot_path=args.snapshot.resolve(), stage_path=root / "result.cdb",
                work_root=root / "native", content=args.content, analysis=args.analysis,
                load_step=args.step, timeout_sec=args.timeout,
            )
            (root / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            return 0
        except BaseException:
            (root / "failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
            raise
    root.mkdir(parents=True, exist_ok=False)
    from ea_node_editor.addons.mechanical.owner_process import _WindowsKillJob
    command = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], "--child"]
    job = _WindowsKillJob()
    try:
        with (root / "qualification.log").open("wb") as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=log,
                                       stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                job.assign(process)
                process.stdin.write(b"1")
                process.stdin.close()
                code = process.wait(timeout=args.timeout + 10)
            finally:
                job.terminate()
                process.wait(timeout=10)
    finally:
        job.close()
    if code:
        print((root / "failure.txt").read_text() if (root / "failure.txt").is_file()
              else f"Native qualification failed; inspect {root / 'qualification.log'}")
    else:
        print((root / "receipt.json").read_text())
    return code


if __name__ == "__main__":
    raise SystemExit(main())
