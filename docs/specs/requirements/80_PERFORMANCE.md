# Performance Requirements

## Targets
- `REQ-PERF-001`: Target scale is 1000 nodes / 5000 edges per scene.
- `REQ-PERF-002`: Pan/zoom p95 frame time target is <= 33 ms on reference hardware.
- `REQ-PERF-003`: Project load target is < 3s for target-scale graph.

## Rendering Strategy
- `REQ-PERF-004`: Use `QGraphicsView.MinimalViewportUpdate` and optimization flags.
- `REQ-PERF-005`: Use explicit scene rect and avoid full-scene invalidation.
- `REQ-PERF-006`: Node/edge painting shall avoid hot-path allocations where practical.

## Concurrency
- `REQ-PERF-007`: Heavy execution/analysis work shall run outside UI thread.

## Acceptance
- `AC-REQ-PERF-002-01`: Stress test script reports p95 <= 33 ms for pan/zoom.
- `AC-REQ-PERF-003-01`: Load timer confirms startup target under reference conditions.
