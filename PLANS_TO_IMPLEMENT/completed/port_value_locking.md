# Port Value Locking (Variant A — "Lock & Slide")

**Visual basis:** `port_value_locking_variants.html` → Variant A

## Context

Primitive input ports (`int`, `float`, `bool`, `str`) currently clutter the graph
even after a literal value has been entered via the inline editor — every one of
them still presents a connectable dot, inviting accidental wires and making dense
graphs (especially DPF operator stacks) visually noisy.

Users typically either *wire* a primitive input OR *type a literal* into it,
very rarely both. This plan formalises that intent:

- Primitive input ports are still always exposed in the spec, so the authoring
  surface remains uniform.
- Any primitive port whose value is "meaningful" (non-zero int, non-zero float,
  `True` bool, non-empty string) is shown in a **locked** state — its dot is
  replaced with a padlock visual (Variant A) and the port becomes *ineligible*
  as an incoming-edge target.
- Locking happens automatically on node creation when the spec's default meets
  the above criterion, and again whenever the user edits the value. Manual
  double-click on the dot toggles the state explicitly.
- Additional gestures let the user hide locked ports and optional ports to
  reduce on-canvas density further.

The goal is a graph where every visible dot is an *active connection choice*,
and literal parameters live quietly in the node body.

---

## Visual Basis (Variant A — Lock & Slide)

Reference the interactive prototype at `port_value_locking_variants.html`
(left panel, tagged "A · Lock & Slide"):

- **Locked dot**: small (~10px), dimmed (opacity ≈ 0.55), border in
  `outlineColor`, padlock glyph overlaid at centre.
- **Locked label**: `text-lo` colour, ~70% opacity.
- **Locked row background**: subtle warm tint `rgba(255, 200, 100, 0.03)`.
- **Row height**: unchanged — the locked row stays the same size, the inline
  property editor in `GraphInlinePropertiesLayer.qml` continues to render the
  value. (We are **not** moving the value editor into the port row; we only
  change the port's visual + eligibility.)
- **Hide-locked toggle**: locked rows collapse out of the ports payload entirely
  with an accordion animation in QML.

---

## Definitions

A port is **lockable** if:

1. Its `direction == "in"`.
2. Its `kind == "data"` (never `exec`/`flow`/`completed`/`failed`).
3. Its `data_type` is one of `{"int", "float", "bool", "str"}`.
4. The owning node's spec has a `PropertySpec` whose `key` matches the port's
   `key` (this is the value source — without it there is nothing to "lock to").

A value is **lock-triggering** (per user's rule):

| `data_type` | triggers lock when... |
|-------------|-----------------------|
| `int`       | `int(value) != 0`     |
| `float`     | `float(value) != 0.0` |
| `bool`      | `bool(value) is True` |
| `str`       | `value.strip() != ""` |

Ports that aren't lockable ignore the gesture entirely (double-click is a no-op).

---

## Data Model Changes

### 1. `NodeInstance` (`ea_node_editor/graph/model.py`)

Add a new dict field mirroring `exposed_ports`:

```python
locked_ports: dict[str, bool] = field(default_factory=dict)
```

Update the two serialisation helpers already in the file:

- `node_instance_to_mapping()` (~line 89) — add
  `"locked_ports": copy.deepcopy(node.locked_ports)`.
- `node_instance_from_mapping()` (~line 66) — add
  `locked_ports={str(k): bool(v) for k, v in _as_mapping(payload.get("locked_ports")).items()}`.

Undo/redo snapshots pick this up automatically because
`runtime_history.py` captures the full `WorkspaceSnapshot`.

### 2. `ViewState` (same file)

Add two per-view visibility toggles for the gesture bar:

```python
hide_locked_ports: bool = False
hide_optional_ports: bool = False
```

…with matching mapping updates. View state is already per-workspace, which is
the right scope for these toggles (each view can de-clutter independently).

### 3. `EffectivePort` (`ea_node_editor/graph/effective_ports.py`)

Add `locked: bool = False` alongside `exposed` and `required`. Populate in
`effective_ports()` from `node.locked_ports.get(port.key, False)`.

### 4. Persistence (`ea_node_editor/persistence/project_codec.py`)

Because serialisation goes through `node_instance_to_mapping()`, no codec
changes should be required, but verify by round-tripping a `.sfe` fixture.

---

## Auto-Lock Logic

### Helper module: `ea_node_editor/graph/port_locking.py` (new)

Small, pure-Python helper shared between creation, property-edit, and tests:

```python
LOCKABLE_PRIMITIVE_DATA_TYPES = frozenset({"int", "float", "bool", "str"})

def is_lockable_port(port_spec, spec) -> bool: ...
def value_triggers_lock(data_type: str, value) -> bool: ...
def compute_initial_locked_ports(spec, properties) -> dict[str, bool]: ...
```

- `value_triggers_lock` handles `None`, strings like `"0"`, booleans, numerics
  safely and uses `str.strip()` for strings.
- `compute_initial_locked_ports` iterates `spec.ports`, filters via
  `is_lockable_port`, looks up `properties[port.key]`, and returns only the
  keys that satisfy `value_triggers_lock`.

### Creation-time auto-lock

In `ea_node_editor/ui/selection_and_scope_ops.py` (~line 77–85, where
`mutations.add_node` is called):

```python
properties = registry.default_properties(type_id)
locked_ports = compute_initial_locked_ports(spec, properties)
mutations.add_node(
    ...,
    exposed_ports={port.key: port.exposed for port in spec.ports},
    locked_ports=locked_ports,
)
```

Thread `locked_ports` through `mutation_service.add_node` and
`normalization.add_node` so it reaches `NodeInstance`.

### Property-edit-time auto-lock (one-way)

Hook into `ValidatedGraphMutation.set_node_property` in
`ea_node_editor/graph/normalization.py`. After the value is written:

1. Look up the spec's `PortSpec` with the same key.
2. If it's lockable **and** the port is currently unlocked, compute
   `value_triggers_lock(data_type, new_value)`.
3. If the new value triggers a lock, flip `node.locked_ports[key] = True`
   (reusing the same internal path as `set_locked_port`).

**One-way semantics (per user decision):** auto-lock only ever *locks*. It
never auto-unlocks when a user clears a value back to zero/empty. Once a port
is locked — whether by creation-time rule, property-edit trigger, or manual
double-click — only an explicit manual unlock (double-click the padlock) will
re-enable it. This means a locked port can legitimately hold an empty literal
after the user clears it, and that's fine.

Both the property write and the induced lock flip live in the same history
action, so undo rewinds both together.

### Manual gesture — double-click on dot

Explicit user override (either direction) via `set_port_locked(node_id, key,
locked)`. Manual lock does **not** modify the property value. Manual unlock
does not modify the property value either — it simply re-enables the port as a
connection target even if a non-zero value remains in the inline editor (the
next incoming wire will shadow the literal at runtime via the existing
`ctx.inputs.get(key, ctx.properties.get(...))` fallback pattern used by e.g.
`core.branch`).

---

## Mutation Surface

### `ea_node_editor/graph/mutation_service.py`

Add:

```python
def set_locked_port(self, node_id: str, key: str, locked: bool) -> bool: ...
def set_view_hide_locked_ports(self, view_id: str, hidden: bool) -> bool: ...
def set_view_hide_optional_ports(self, view_id: str, hidden: bool) -> bool: ...
```

### `ea_node_editor/graph/normalization.py`

Matching `ValidatedGraphMutation` methods. `set_locked_port` validates the
target port is lockable; raises otherwise.

### `ea_node_editor/ui_qml/graph_scene/command_bridge.py`

Expose as Qt slots mirroring `set_exposed_port` (~line 167):

```python
@pyqtSlot(str, str, bool)
def set_port_locked(self, node_id: str, key: str, locked: bool) -> None: ...

@pyqtSlot(bool)
def set_hide_locked_ports(self, hidden: bool) -> None: ...

@pyqtSlot(bool)
def set_hide_optional_ports(self, hidden: bool) -> None: ...
```

Route through `_authoring_boundary` so they participate in undo/redo.

---

## Connection Validation

In `ea_node_editor/ui/graph_interactions.py` `connect_ports()` (~line 54) and
its helper `port_supports_incoming_edge()`:

Add an early check:

```python
if target_port.locked:
    return ConnectionResult(success=False, reason="Port is locked to its value")
```

This guarantees the backend refuses the edge even if a stale QML payload still
offered the dot. The QML side also suppresses drag-start on locked ports for
UX feedback.

---

## Payload → QML

In `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
`_GraphSceneNodePayloadFactory.build_ports_payload()` (~line 289):

```python
"locked": bool(node.locked_ports.get(port.key, False)),
"optional": not bool(port.required),
```

Respect the two view toggles while iterating:

```python
if view.hide_locked_ports and node.locked_ports.get(port.key, False):
    continue
if view.hide_optional_ports and not port.required:
    continue
```

(Same place the existing `exposed` filter lives.)

---

## QML / UI Implementation

### `GraphNodePortsLayer.qml`

Extend the existing port-dot delegate (currently branches on `inactiveState`):

1. New derived property:
   ```qml
   readonly property bool lockedState: !!(modelData && modelData.locked)
   ```
2. When `lockedState` is true:
   - Set `cursorShape: Qt.ForbiddenCursor`.
   - Skip drag on `onPressed`, short-circuit all drag events (mirror the
     existing `inactiveState` guards ~line 219, 239, 260, 294).
   - Render a padlock glyph overlay — use a Unicode lock (`"\uE897"` from the
     bundled Material icon font, or `"\uD83D\uDD12"` emoji) inside a small
     child `Text` node. Font comes from `graphSharedTypography`.
   - Reduce opacity to ~0.55 and fall back to transparent fill.
   - Tint label: `opacity: 0.7`, colour: `host.outlineColor`.
   - Subtle row tint via a background `Rectangle` with the warm-amber colour
     from the prototype.
3. Wire `onDoubleClicked` on the dot's `MouseArea` to call
   `root.host.portDoubleClicked(node_id, key, direction)` — a new host signal
   that forwards to `command_bridge.set_port_locked(node_id, key, !locked)`.
   Drag and double-click already coexist in Qt's `MouseArea` when
   `acceptedButtons` includes `LeftButton`; the single-click drag-start is
   unaffected because we only act on double-click when no drag occurred.
4. Collapse animation when the view toggle hides locked ports: leverage the
   existing row `height` binding — when filtered out of payload the row
   disappears naturally; add a `Behavior on height { NumberAnimation { duration
   180; easing.type: Easing.OutCubic } }` for the slide.

### `GraphInlinePropertiesLayer.qml`

No structural changes required — inline editors keep rendering their value.
Optionally add a tiny "🔒" affordance next to the property label when the
corresponding port is locked (nice-to-have, can land in a follow-up).

### Gesture routing for global shortcuts

Find the canvas-level input layer that currently handles pan/zoom (likely
`GraphCanvas.qml` or similar; to be confirmed during implementation — one
`Grep` for `MiddleButton` in `ui_qml/components/graph/`).

Add:

- `Ctrl + DoubleClick` on empty canvas → call
  `command_bridge.set_hide_locked_ports(!current)`.
- `MiddleButton + LeftButton` chord → same action as above (alternate gesture).
- `MiddleButton + RightButton` chord → `set_hide_optional_ports(!current)`.

Chord detection: track which buttons are currently held in the canvas
`MouseArea` (`pressedButtons` property) and trigger on the second-button press
event.

---

## Files to Modify

| Purpose | File |
|---------|------|
| Dataclass + serialisation + view state | `ea_node_editor/graph/model.py` |
| Effective port field | `ea_node_editor/graph/effective_ports.py` |
| Auto-lock helpers (new) | `ea_node_editor/graph/port_locking.py` |
| Normalized mutations | `ea_node_editor/graph/normalization.py` |
| Mutation service façade | `ea_node_editor/graph/mutation_service.py` |
| Creation-time auto-lock | `ea_node_editor/ui/selection_and_scope_ops.py` |
| Connection validation | `ea_node_editor/ui/graph_interactions.py` |
| QML command surface | `ea_node_editor/ui_qml/graph_scene/command_bridge.py` |
| Payload → QML | `ea_node_editor/ui_qml/graph_scene_payload_builder.py` |
| Port visuals + dbl-click | `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml` |
| Canvas-level chord gestures | canvas gesture layer (TBD — `GraphCanvas*.qml`) |
| Persistence round-trip | `ea_node_editor/persistence/project_codec.py` (verify only) |

---

## Test Plan

- **Unit — `port_locking.py`**
  - `value_triggers_lock` covers: `0`, `0.0`, `""`, `"  "`, `False`, `None`
    (→ False); `1`, `0.5`, `"x"`, `True` (→ True); stringified numbers
    (`"0"`, `"10"`) parsed per data type.
  - `compute_initial_locked_ports` builds the right dict for a mixed spec.
- **Unit — creation path**: adding a node whose spec defaults include
  `("verbose", bool, True)` produces `NodeInstance.locked_ports == {"verbose": True}`.
- **Unit — property-edit auto-lock (one-way)**:
  - Editing `iterations` from 0 → 10 on an unlocked port auto-locks it.
  - Editing `iterations` from 10 → 0 on a locked port leaves it **locked**
    (one-way semantics — no auto-unlock).
  - Editing a lockable property on a port that is already locked does nothing
    to the lock state.
  - Editing a non-lockable property never touches `locked_ports`.
- **Unit — manual override**: `set_port_locked` on a non-lockable port raises;
  on a lockable port toggles the dict entry; undo restores prior state.
- **Unit — connection validator**: `connect_ports()` rejects an edge whose
  target is a locked port.
- **Unit — payload builder**: view toggles filter rows as expected; `locked`
  and `optional` flags surface on payload dicts.
- **Serialization**: round-trip a fixture with locked ports + view toggles
  through `JsonProjectCodec` preserves state.
- **QML smoke (existing payload-snapshot tests)**: update golden snapshots to
  include the new fields.

## Verification (end-to-end)

1. Run the app, drop a node whose spec defaults include a non-zero primitive
   (e.g. a DPF operator with `iterations=10`).
   → that port appears with the padlock visual; connection drop is refused.
2. Drop a different node with only default-zero primitives.
   → all primitive ports render normally.
3. Double-click a locked port dot → unlocks; dot becomes a normal port and
   accepts a wire.
4. Type a value into an inline primitive editor → after commit, matching port
   locks automatically.
5. Clear the same inline editor back to empty → port **remains locked**
   (one-way semantics); manual double-click is required to re-enable it.
6. `Ctrl + DoubleClick` on empty canvas → all locked ports slide out; repeat
   to slide back in.
7. `MiddleButton + LeftButton` chord → same behaviour as (6).
8. `MiddleButton + RightButton` chord → optional (`required=False`) ports
   toggle visibility independently.
9. Save project → reload → locked state and view toggles persist.
10. Undo/redo through a series of lock changes, property edits, and view
    toggles → state is consistent at every step.

---

## Design Decisions (confirmed with user)

1. **Auto-unlock:** one-way. Auto-lock only *locks*; unlocking is always a
   manual double-click on the padlock.
2. **Orphan primitive ports** (no matching property): the lock gesture is a
   no-op. Only ports with a matching-key `PropertySpec` are lockable.
3. **Toggle scope:** per-view. `hide_locked_ports` and `hide_optional_ports`
   are stored on `ViewState` and persist with the project file.
4. **Lock visual:** padlock glyph inside the dimmed dot, matching the
   `port_value_locking_variants.html` Variant A prototype.
