# ADR-0001: UI Stack

- Status: Accepted
- Date: 2026-03-01

## Decision
Use PyQt6 Widgets + `QGraphicsScene/QGraphicsView` for the node editor canvas with custom `QGraphicsItem` nodes/edges.

## Rationale
- Predictable desktop behavior for Windows engineering users.
- Strong control over render performance and item-level optimization.
- Simpler integration with existing QWidget tool panels.

## Consequences
- QML is deferred.
- Styling flexibility is lower than full QtQuick but acceptable for skeleton core.
