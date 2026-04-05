# UI Feature Packet Template

Use this template for future UI work after `P08`. Start from the [subsystem packet index](./SUBSYSTEM_PACKET_INDEX.md), name one owning subsystem packet, and inherit the required tests and invariants from every subsystem doc you touch.

## Required Authoring Rules

- Name one primary owner under `Owning Subsystem Packet`.
- Use `Inherited Secondary Subsystem Docs` only when the change crosses an already-defined packet seam.
- Keep `Conservative Write Scope` inside the owning packet unless the packet spec explicitly inherits another subsystem contract.
- Copy the owning subsystem's `Required Tests`, `Invariants`, and `Forbidden Shortcuts` into the packet-specific reasoning instead of restating them from memory.
- Add or update contract docs when a packet changes a public entry point or a dependency rule.

## Template Skeleton

### Packet Metadata

- Packet: `PXX`
- Title: `<short feature title>`
- Owning Subsystem Packet: `[Shell Packet](./SHELL_PACKET.md)`
- Inherited Secondary Subsystem Docs: `none` or `[Graph Canvas Packet](./GRAPH_CANVAS_PACKET.md)`
- Execution Dependencies: `<prior packet or baseline>`

### Objective

- State the user-visible or engineering outcome without reopening unrelated packet seams.

### Conservative Write Scope

- List only the files required for this feature packet.

### Public Entry Points

- Name the existing packet-owned entry points this feature depends on or changes.

### State Owner

- Name the authoritative state owner and explain whether the packet only projects that state or mutates it.

### Allowed Dependencies

- Enumerate the subsystem docs and public helpers the packet may depend on.

### Required Invariants

- Copy forward the invariants from the owning packet doc and add any feature-specific invariants.

### Forbidden Shortcuts

- Copy forward the owning packet's forbidden shortcuts and list any new shortcuts this feature must avoid.

### Required Tests

- List the owning packet's required tests first.
- Add inherited secondary-packet tests when the packet crosses subsystem boundaries.
- Add packet-specific tests only when new behavior or docs need narrower proof than the baseline anchors.

### Verification Commands

- Keep the commands as narrow as the owning packet allows.

### Review Gate

- Re-run the owning packet's review gate or the narrow inherited equivalent.

### Expected Artifacts

- List wrap-up docs plus any packet-owned docs, helpers, or tests this feature is expected to produce.

### Acceptance Criteria

- Tie the result back to the owning subsystem contract and the inherited verification anchors.

### Handoff Notes

- Record which later packet or follow-up should absorb any deferred work without broadening the current packet.
