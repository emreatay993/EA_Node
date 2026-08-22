# ADR-0001: UI Stack

- Status: Historical, non-authoritative
- Date: 2026-03-01

## Current Authority
This ADR is retained as historical context. The current requirements pack supersedes it with the pre-release modernization baseline: the QML shell is one client of a headless Corex kernel, not the owner of kernel behavior.

## Decision
Use a QML-first desktop shell (`QtQuick`) with a QML graph canvas for node/edge rendering and interaction, hosted by a thin PyQt6 `QMainWindow` bridge.

## Rationale
- Stitch visual fidelity is a primary acceptance criterion for shell and graph surfaces.
- QtQuick/QML provides stronger control for matching reference visuals and interaction behavior.
- Python bridge/controllers keep the QML shell decoupled from graph, persistence, execution, and node SDK contracts that now move behind explicit kernel-facing interfaces.

## Consequences
- QWidget shell and `QGraphicsScene/QGraphicsView` are removed from the runtime UI path.
- Packaging must include QML assets and QtQuick runtime dependencies.
- UI parity tests target QML bridge/controller behavior instead of QWidget internals.
