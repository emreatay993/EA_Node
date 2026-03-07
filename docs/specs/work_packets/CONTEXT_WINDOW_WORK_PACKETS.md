# Context Window Work Packets

These packets are designed for independent implementation sessions with strict handoff contracts.

## Packet A: Shell and Theme
- Inputs: 10_ARCHITECTURE, 20_UI_UX
- Outputs: main window layout, menu/toolbar/status APIs, dark theme
- Contract: no graph-model schema changes

## Packet B: Graph Core
- Inputs: 30_GRAPH_MODEL, 80_PERFORMANCE
- Outputs: scene/view/items, node drag/select/connect, collapse visuals
- Contract: consume Node SDK contracts only

## Packet C: Workspace + Views
- Inputs: 20_UI_UX, 30_GRAPH_MODEL
- Outputs: workspace tabs, view switch/persistence, tab context menu actions
- Contract: preserve existing serializer schema

## Packet D: Node SDK + Library
- Inputs: 40_NODE_SDK
- Outputs: plugin contracts, registry, filtered node library UI
- Contract: backward-compatible type ids

## Packet E: Execution Engine
- Inputs: 50_EXECUTION_ENGINE
- Outputs: worker process, command/event protocol, run failure events
- Contract: event payload shape stable

## Packet F: Starter Integrations
- Inputs: 70_INTEGRATIONS
- Outputs: core + io nodes operational
- Contract: failures propagate as node-level errors

## Packet G: Persistence and Migration
- Inputs: 60_PERSISTENCE
- Outputs: save/load/migrate/session restore
- Contract: deterministic output

## Packet H: QA + Perf Gate
- Inputs: 80_PERFORMANCE, 90_QA_ACCEPTANCE
- Outputs: test suites, stress scripts, acceptance report
- Contract: report with target metrics
