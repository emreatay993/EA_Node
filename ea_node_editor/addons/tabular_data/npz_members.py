# Purpose: Inspect NPZ headers and cache selected members without loading unrelated arrays.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_npz_members.py
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import struct
import tempfile
import threading
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

NPY_HEADER_LIMIT = 10_000
COPY_CHUNK_BYTES = 1024 * 1024


def read_npy_header(stream: Any, *, member_size: int) -> dict[str, Any]:
    """Read only the bounded NPY header; object payloads remain uninterpreted."""
    import numpy as np

    magic = stream.read(8)
    if len(magic) != 8 or magic[:6] != b"\x93NUMPY" or magic[6:] not in {b"\x01\x00", b"\x02\x00", b"\x03\x00"}:
        raise ValueError("Unsupported or malformed NPY header")
    length_bytes = 2 if magic[6] == 1 else 4
    raw_length = stream.read(length_bytes)
    if len(raw_length) != length_bytes:
        raise ValueError("Truncated NPY header length")
    length = struct.unpack("<H" if length_bytes == 2 else "<I", raw_length)[0]
    if length > NPY_HEADER_LIMIT:
        raise ValueError(f"NPY header exceeds {NPY_HEADER_LIMIT} bytes")
    header = stream.read(length)
    if len(header) != length:
        raise ValueError("Truncated NPY header")
    try:
        info = ast.literal_eval(header.decode("utf-8" if magic[6] == 3 else "latin1"))
    except (ValueError, SyntaxError, UnicodeError) as exc:
        raise ValueError("Malformed NPY header dictionary") from exc
    if not isinstance(info, dict) or set(info) != {"descr", "fortran_order", "shape"}:
        raise ValueError("Invalid NPY header fields")
    shape = info["shape"]
    if not isinstance(shape, tuple) or any(type(n) is not int or n < 0 for n in shape):
        raise ValueError("Invalid NPY shape")
    if type(info["fortran_order"]) is not bool:
        raise ValueError("Invalid NPY memory order")
    dtype = np.dtype(info["descr"])
    nbytes = math.prod(shape) * dtype.itemsize
    if not dtype.hasobject and 8 + length_bytes + length + nbytes != member_size:
        raise ValueError("NPY member size does not match its shape and dtype")
    return {"shape": shape, "dtype": str(dtype), "nbytes": nbytes,
            "object_dtype": bool(dtype.hasobject), "fortran_order": info["fortran_order"]}


def catalogue_npz(path: Path, *, check_cancelled: Callable[[], None] | None = None) -> list[dict[str, Any]]:
    result = []
    with zipfile.ZipFile(path, "r") as archive:
        seen: set[str] = set()
        for info in archive.infolist():
            if check_cancelled is not None:
                check_cancelled()
            if info.is_dir() or not info.filename.endswith(".npy"):
                continue
            key = info.filename[:-4]
            if key in seen:
                raise ValueError(f"NPZ contains duplicate member {key!r}")
            seen.add(key)
            entry: dict[str, Any] = {"member": key, "compressed_bytes": info.compress_size,
                                     "uncompressed_bytes": info.file_size, "supported": True}
            try:
                with archive.open(info) as stream:
                    entry.update(read_npy_header(stream, member_size=info.file_size))
                if entry["object_dtype"]:
                    entry.update(supported=False, error="Object arrays require pickle and are unavailable")
            except (ValueError, TypeError, OSError, zipfile.BadZipFile) as exc:
                entry.update(supported=False, error=str(exc))
            result.append(entry)
    return result


class NpzMemberCache:
    """One shared disk budget, atomic member extraction and read-only mmap access."""

    def __init__(self, directory: Path, *, max_bytes: int, reserve: Callable[[int], None] | None = None) -> None:
        self.directory = directory
        self.max_bytes = max_bytes
        self._reserve = reserve
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}

    def open(self, source: Path, member: str, *, content_sha256: str = "", check_cancelled: Callable[[], None] | None = None) -> Any:
        import numpy as np

        source_stat = source.stat()
        identity = [str(source.resolve()), source_stat.st_size, source_stat.st_mtime_ns, content_sha256, member]
        key = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode("utf-8")).hexdigest()
        destination = self.directory / (key + ".npy")
        with self._guard:
            lock = self._locks.setdefault(key, threading.Lock())
        with lock:
            if check_cancelled is not None:
                check_cancelled()
            if not destination.is_file():
                self.directory.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(source) as archive:
                    info = archive.getinfo(member + ".npy")
                    if info.file_size > self.max_bytes:
                        raise ValueError("Selected NPZ member exceeds the managed cache budget")
                    with archive.open(info) as stream:
                        header = read_npy_header(stream, member_size=info.file_size)
                    if header["object_dtype"]:
                        raise ValueError("Object arrays require pickle and are unavailable")
                    if self._reserve is not None:
                        self._reserve(info.file_size)
                    else:
                        self._evict_for(info.file_size)
                    fd, temporary_name = tempfile.mkstemp(prefix=key + "-", suffix=".partial", dir=self.directory)
                    temporary = Path(temporary_name)
                    try:
                        with os.fdopen(fd, "wb") as target, archive.open(info) as stream:
                            while True:
                                if check_cancelled is not None:
                                    check_cancelled()
                                chunk = stream.read(COPY_CHUNK_BYTES)
                                if not chunk:
                                    break
                                target.write(chunk)
                        current = source.stat()
                        if (current.st_size, current.st_mtime_ns) != (source_stat.st_size, source_stat.st_mtime_ns):
                            raise ValueError("NPZ source changed while preparing its selected array")
                        try:
                            os.replace(temporary, destination)
                        except PermissionError:
                            if not destination.is_file():
                                raise
                    finally:
                        temporary.unlink(missing_ok=True)
            result = np.load(destination, mmap_mode="r", allow_pickle=False)
        return result

    def _evict_for(self, incoming: int) -> None:
        entries = sorted(((p.stat().st_mtime_ns, p.stat().st_size, p) for p in self.directory.glob("*.npy")))
        total = sum(size for _, size, _ in entries)
        for _, size, path in entries:
            if total + incoming <= self.max_bytes:
                return
            try:
                path.unlink()
                total -= size
            except OSError:
                continue  # A live Windows mmap pins its member until the reader closes it.
        if total + incoming > self.max_bytes:
            raise ValueError("The managed NPZ cache is full; close active views or increase its budget")
