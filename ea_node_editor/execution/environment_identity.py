# Purpose: Compute authoritative route identity once without publishing client state.
# Map: subsystems/execution.md
# Tests: tests/test_generation_readiness.py, tests/test_backend_client.py
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import threading

from ea_node_editor.execution.backends import (
    EXTERNAL_SUBPROCESS_BACKEND,
    ExecutionBackendSelection,
)
from ea_node_editor.execution.client_generation import (
    _result_affecting_selection_payload,
)
from ea_node_editor.execution.solution_identity import canonical_digest
from ea_node_editor.nodes.registry import NodeRegistry

_EXTERNAL_RUNTIME_IDENTITY_PROBE = r"""
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

names = json.loads(sys.argv[1])
mapping = importlib.metadata.packages_distributions()
packages = []
for name in names:
    distributions = mapping.get(name, ()) or (name,)
    versions = []
    for distribution in sorted(set(distributions)):
        try:
            versions.append((distribution, importlib.metadata.version(distribution)))
        except importlib.metadata.PackageNotFoundError:
            continue
    packages.append((name, versions or [("", "missing")]))
executable = Path(sys.executable)
digest = hashlib.sha256()
with executable.open("rb") as source:
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
print(json.dumps({
    "implementation": sys.implementation.name,
    "cache_tag": sys.implementation.cache_tag or "",
    "version": list(sys.version_info[:3]),
    "platform": [platform.system(), platform.release(), platform.machine()],
    "executable_size": executable.stat().st_size,
    "executable_sha256": digest.hexdigest(),
    "packages": packages,
}, sort_keys=True, separators=(",", ":")))
"""


def _package_versions(package_names: tuple[str, ...]) -> tuple[tuple[str, object], ...]:
    mapping = importlib.metadata.packages_distributions()
    result = []
    for name in package_names:
        distributions = mapping.get(name, ()) or (name,)
        versions = []
        for distribution in sorted(set(distributions)):
            try:
                versions.append(
                    (distribution, importlib.metadata.version(distribution))
                )
            except importlib.metadata.PackageNotFoundError:
                continue
        result.append((name, tuple(versions) or (("", "missing"),)))
    return tuple(result)


def _local_runtime_identity(package_names: tuple[str, ...]) -> dict[str, object]:
    executable = Path(sys.executable)
    digest = hashlib.sha256()
    with executable.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "implementation": sys.implementation.name,
        "cache_tag": sys.implementation.cache_tag or "",
        "version": tuple(sys.version_info[:3]),
        "platform": (platform.system(), platform.release(), platform.machine()),
        "executable_size": executable.stat().st_size,
        "executable_sha256": digest.hexdigest(),
        "packages": _package_versions(package_names),
    }


class EnvironmentIdentityCache:
    """Memoize built-in identity independently of physical worker lifetimes.

    Preview and reservation share the same immutable registry/route contract.
    External environments retain their existing on-demand identity probe.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._digests: OrderedDict[tuple[str, str], str] = OrderedDict()

    def compute(
        self, selection: ExecutionBackendSelection, registry: NodeRegistry
    ) -> str:
        if not registry.is_frozen:
            raise ValueError("environment identity requires a frozen registry")
        registry_fingerprint = registry.contract_fingerprint()
        selection_payload = _result_affecting_selection_payload(selection)
        if selection.backend_id == EXTERNAL_SUBPROCESS_BACKEND:
            return self._compute(
                selection, registry, registry_fingerprint, selection_payload
            )
        key = registry_fingerprint, canonical_digest(selection_payload)
        with self._lock:
            digest = self._digests.get(key)
            if digest is None:
                digest = self._compute(
                    selection, registry, registry_fingerprint, selection_payload
                )
                self._digests[key] = digest
            self._digests.move_to_end(key)
            while len(self._digests) > 2:
                self._digests.popitem(last=False)
            return digest

    @staticmethod
    def _compute(selection, registry, registry_fingerprint, selection_payload) -> str:
        declared_facts = registry.execution_environment_facts()
        package_names = tuple(declared_facts.get("python_packages", ()))
        if selection.backend_id == EXTERNAL_SUBPROCESS_BACKEND:
            result = subprocess.run(
                [
                    selection.python_executable,
                    "-c",
                    _EXTERNAL_RUNTIME_IDENTITY_PROBE,
                    json.dumps(package_names, separators=(",", ":")),
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=10.0,
            )
            if result.returncode != 0:
                raise RuntimeError("External Python runtime identity handshake failed.")
            try:
                runtime_facts = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "External Python runtime identity handshake was invalid."
                ) from exc
            if not isinstance(runtime_facts, Mapping):
                raise RuntimeError(
                    "External Python runtime identity handshake was invalid."
                )
        else:
            runtime_facts = _local_runtime_identity(package_names)
        environment_digest = canonical_digest(
            {
                "schema_version": 1,
                "selection": selection_payload,
                "runtime": dict(runtime_facts),
                "declared": declared_facts,
                "registry_contract_fingerprint": registry_fingerprint,
            }
        )
        return environment_digest
