from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_RELATIVE_ROOT = Path("tests") / "ansys_dpf_core" / "example_outputs"


def _candidate_repo_roots() -> tuple[Path, ...]:
    candidates: list[Path] = [_REPO_ROOT]
    main_checkout = _REPO_ROOT.parent.parent / "EA_Node_Editor"
    if main_checkout not in candidates:
        candidates.append(main_checkout)
    return tuple(candidates)


def dpf_fixture_root() -> Path:
    searched: list[Path] = []
    for repo_root in _candidate_repo_roots():
        candidate = repo_root / _FIXTURE_RELATIVE_ROOT
        searched.append(candidate)
        if candidate.exists():
            return candidate
    searched_paths = ", ".join(str(path) for path in searched)
    raise FileNotFoundError(f"Could not locate DPF example outputs under: {searched_paths}")


def dpf_fixture_path(case_name: str, filename: str) -> Path:
    fixture_path = dpf_fixture_root() / case_name / filename
    if not fixture_path.exists():
        raise FileNotFoundError(f"Missing DPF fixture: {fixture_path}")
    return fixture_path.resolve()


STATIC_ANALYSIS_RST = dpf_fixture_path("static_analysis_1_bolted_joint", "file.rst")
MODAL_ANALYSIS_RST = dpf_fixture_path("modal_analysis_1_bolted_joint", "file.rst")
THERMAL_ANALYSIS_RTH = dpf_fixture_path("steady_state_thermal_analysis_1_bolted_joint", "file.rth")


__all__ = [
    "MODAL_ANALYSIS_RST",
    "STATIC_ANALYSIS_RST",
    "THERMAL_ANALYSIS_RTH",
    "dpf_fixture_path",
    "dpf_fixture_root",
]
