# UI Feature Packet Template

Use this template for future UI work after `P08`. Start from the [subsystem packet index](./SUBSYSTEM_PACKET_INDEX.md), name one owning source subsystem packet plus one owning regression packet, and inherit the required tests, entrypoints, and invariants from every packet doc you touch.

## Required Authoring Rules

- Name one primary source owner under `Owning Source Subsystem Packet`.
- Name one primary regression owner under `Owning Regression Packet`.
- Use `Inherited Secondary Subsystem Docs` only when the change crosses an already-defined source packet seam.
- Use `Inherited Secondary Regression Docs` only when the change widens an additional stable regression seam.
- Keep `Conservative Write Scope` inside the owning source and regression packets unless the packet spec explicitly inherits another contract.
- Copy the owning source packet's `Public Entry Points`, `State Owner`, `Invariants`, `Forbidden Shortcuts`, and `Required Tests` into the packet-specific reasoning instead of restating them from memory.
- Copy the owning regression packet's `Public Entry Points`, `Invariants`, `Forbidden Shortcuts`, and `Required Tests` into the packet-specific reasoning before widening a stable entrypoint or helper surface.
- Add or update contract docs when a packet changes a public entry point, a dependency rule, or a stable regression entrypoint.

## Template Skeleton

### Packet Metadata

- Packet: `PXX`
- Title: `<short feature title>`
- Owning Source Subsystem Packet: [Shell Packet](./SHELL_PACKET.md)
- Owning Regression Packet: [Main Window Shell Test Packet](./MAIN_WINDOW_SHELL_TEST_PACKET.md)
- Inherited Secondary Subsystem Docs: `none` or [Graph Canvas Packet](./GRAPH_CANVAS_PACKET.md)
- Inherited Secondary Regression Docs: `none` or [Graph Surface Test Packet](./GRAPH_SURFACE_TEST_PACKET.md)
- Execution Dependencies: `<prior packet or baseline>`

### Objective

- State the user-visible or engineering outcome without reopening unrelated packet seams.

### Conservative Write Scope

- List only the files required for this feature packet.

### Source Public Entry Points

- Name the existing packet-owned source entry points this feature depends on or changes.

### Regression Public Entry Points

- Name the stable regression entrypoints and suite export surfaces this feature depends on or changes.

### State Owner

- Name the authoritative source-side state owner and explain whether the packet only projects that state or mutates it.

### Allowed Dependencies

- Enumerate the source and regression packet docs plus the public helpers this packet may depend on.

### Required Invariants

- Copy forward the invariants from the owning source and regression packet docs and add any feature-specific invariants.

### Forbidden Shortcuts

- Copy forward the owning packet docs' forbidden shortcuts and list any new shortcuts this feature must avoid.

### Required Tests

- List the owning regression packet's stable entrypoints first.
- List the owning source packet's required tests next.
- Add inherited secondary-packet tests only when the packet crosses subsystem or regression boundaries.
- Add packet-specific tests only when new behavior or docs need narrower proof than the baseline anchors.

### Verification Commands

- Keep the commands as narrow as the owning source and regression packets allow.

### Review Gate

- Re-run the owning regression packet's review gate or the narrow inherited equivalent, and include the source-side review gate when a broader source seam changed.

### Expected Artifacts

- List wrap-up docs plus any packet-owned docs, helpers, or tests this feature is expected to produce.

### Acceptance Criteria

- Tie the result back to the owning source subsystem contract, the owning regression packet contract, and the inherited verification anchors.

### Handoff Notes

- Record which later packet or follow-up should absorb any deferred work without broadening the current packet.
