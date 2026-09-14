# Purpose: Publish table/array exports atomically after a complete successful write.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_export.py
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile

from ea_node_editor.addons.tabular_data.operations import check_cancelled


@contextmanager
def atomic_tabular_output(path: Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix="." + path.stem + "-", suffix=path.suffix, dir=path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        yield temporary
        check_cancelled()
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
