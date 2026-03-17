#!/usr/bin/env python3
"""Launch the work packet monitor GUI."""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ea_node_editor.ui.work_packet_monitor import run


if __name__ == "__main__":
    raise SystemExit(run())
