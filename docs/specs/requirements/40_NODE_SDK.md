# Node SDK Requirements

## Contracts
- `REQ-NODE-001`: Node SDK shall include typed `PortSpec`, `PropertySpec`, and `NodeTypeSpec`.
- `REQ-NODE-002`: Node plugin contract shall provide `spec()` and `execute(context)` methods.
- `REQ-NODE-003`: Node registry shall support registration, instantiation, and filtered discovery.

## Properties and Ports
- `REQ-NODE-004`: Node properties shall be declarative and editable from inspector.
- `REQ-NODE-005`: Port exposure toggles shall be driven by node instance state and reflected immediately in UI.
- `REQ-NODE-006`: Nodes shall support `exec`, `completed`, and `data` port kinds.

## Decorator Authoring (RC2)
- `REQ-NODE-007`: SDK shall provide decorator helpers to author nodes without manually constructing `NodeTypeSpec`.
- `REQ-NODE-008`: Decorator-authored nodes and class-spec-authored nodes shall be registry-compatible.
- `REQ-NODE-016`: `NodeTypeSpec` shall expose `runtime_behavior` plus `surface_family` / `surface_variant` hints and additive `render_quality` metadata (`weight_class`, `max_performance_strategy`, `supported_quality_tiers`) so the registry can describe passive-vs-active behavior, host-routed canvas surfaces, and heavy-node quality/proxy behavior declaratively with safe defaults when the field is omitted.
- `REQ-NODE-017`: node authoring contracts shall support `flow` port kinds and declarative editor hints such as multiline text and filesystem path pickers for passive-node properties.

Example:

```python
from ea_node_editor.nodes.decorators import node_type, in_port, out_port, prop_int

@node_type(
    type_id="demo.scale",
    display_name="Scale",
    category="Core",
    icon="functions",
    ports=(in_port("value", data_type="float"), out_port("scaled", data_type="float")),
    properties=(prop_int("factor", 2, "Factor"),),
)
class ScaleNode:
    def execute(self, ctx):
        return NodeResult(outputs={"scaled": float(ctx.inputs.get("value", 0.0)) * int(ctx.properties["factor"])})
```

## Acceptance
- `AC-REQ-NODE-003-01`: Registry filtering returns expected nodes by text/category/type.
- `AC-REQ-NODE-004-01`: Property edits are reflected in model and execution context.
- `AC-REQ-NODE-005-01`: Toggling exposed ports changes rendered port list without restart.
- `AC-REQ-NODE-008-01`: Decorator-authored node plugins register and execute identically to class-spec plugins.
- `AC-REQ-NODE-016-01`: registry validation, graph-surface payload coverage, and passive catalog coverage confirm passive flowchart/planning/annotation/media specs publish stable runtime, surface, and `render_quality` metadata, while specs that omit the field inherit the safe defaults.
- `AC-REQ-NODE-017-01`: passive property-editor and media-node regressions confirm `flow` ports plus `textarea` / `path` editor hints round-trip and render without custom plugin code outside the SDK contract.
