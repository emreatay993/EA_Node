# QA and Acceptance Requirements

## Test Layers
- `REQ-QA-001`: Unit tests for registry filters, serializer round trip, workspace manager behavior.
- `REQ-QA-002`: Engine tests for run completed and run failed event paths.
- `REQ-QA-003`: Integration smoke test for Excel -> transform -> Excel pipeline.

## Functional Scenarios
- `REQ-QA-004`: Workspace lifecycle scenario test.
- `REQ-QA-005`: Multi-view state retention scenario test.
- `REQ-QA-006`: Node collapse and exposed-port behavior test.
- `REQ-QA-007`: Failure focus and error reporting test.

## Acceptance
- `AC-REQ-QA-001-01`: Included unit tests pass in CI/local runner.
- `AC-REQ-QA-004-01`: Workspace actions preserve correct tab-state and model state.
- `AC-REQ-QA-007-01`: Failed run centers node and reports exception details.
