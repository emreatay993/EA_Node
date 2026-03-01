# ADR-0001: UI Stack

- Status: Accepted
- Date: 2026-03-01

## Decision
Use a QML-first desktop shell (`QtQuick`) with a QML graph canvas for node/edge rendering and interaction, hosted by a thin PyQt6 `QMainWindow` bridge.

## Rationale
- Stitch visual fidelity is a primary acceptance criterion for shell and graph surfaces.
- QtQuick/QML provides stronger control for matching reference visuals and interaction behavior.
- Python bridge/controllers preserve `.sfe` schema compatibility, execution engine behavior, and node SDK contracts.

## Consequences
- QWidget shell and `QGraphicsScene/QGraphicsView` are removed from the runtime UI path.
- Packaging must include QML assets and QtQuick runtime dependencies.
- UI parity tests target QML bridge/controller behavior instead of QWidget internals.
