# Python Script Nodes

`Core > Python Script` lets you add a small, local Python transform to a
workflow. Put the declarations and `run` function in the script editor, then
click **Apply**. COREX reads the declarations to create the node ports and
controls; it does not run your script while it is applying the draft.

This guide is for the built-in Python Script node. It is not the external
plugin API; keep using [Creating a Custom Node](../README.md#creating-a-custom-node)
when you want to ship a reusable node package.

## Start with a pass-through

Insert **Core > Python Script**, open its script editor, replace the draft with
this, and click **Apply**:

```python
@corex.node
@corex.input("payload", value_type=corex.Any)
@corex.output("result", value_type=corex.Any)
def run(ctx, payload):
    return {"result": payload}
```

`payload` is now an input socket and `result` is an output socket. The `run`
function receives the input and returns a mapping whose keys are declared
outputs.

## Declare ports

Put `@corex.node` directly above one synchronous function named `run`. Every
other declaration sits between it and the function. The source order is the
display order for inputs and controls; outputs stay at the top level.

```python
@corex.node
@corex.input("samples", value_type=float, structure="list", required=True)
@corex.output("average", value_type=float)
def run(ctx, samples):
    return {"average": sum(samples) / len(samples)}
```

`@corex.input` accepts `value_type=`, `structure=`, `required=`, `label=`,
`description=`, and `section=`. `@corex.output` accepts the same fields except
`required` and `section`. Names must be ordinary Python identifiers and cannot
be reused.

Use a built-in type, a supported alias, or a registered canonical type ID:

```python
@corex.input("enabled", value_type=bool)
@corex.input("title", value_type=str)
@corex.input("image", value_type=corex.Image)
@corex.output("colour", value_type=corex.Color)
@corex.output("catalog_text", value_type="COREX.DataTypes.String")
```

The built-ins are `bool`, `int`, `float`, and `str`. The aliases are
`corex.Any`, `corex.Image`, `corex.Color`, and `corex.Interval`. A canonical
type-ID string must already be registered or Apply reports an error.

`structure` describes the outer shape, independently of the element type:

| Structure | `run` receives or returns |
| --- | --- |
| `"item"` (default) | One value |
| `"list"` | One branch as a non-string sequence |
| `"tree"` | The complete `DataTree` topology |

Use `required=True` for an input that must be wired before the node can run.
Inputs are optional by default.

## Add a control

A control decorator creates a saved setting and a `run` parameter. Add
`port=True` when the setting should also have an optional input socket: a wire
temporarily overrides the saved value, and disconnecting restores that value.

```python
@corex.node
@corex.output("caption", value_type=str)
@corex.text("title", default="My plot", section="Style", port=True)
@corex.slider(
    "line_width", default=2.0, minimum=0.5, maximum=8.0, step=0.5,
    section="Style", port=True,
)
def run(ctx, title, line_width):
    return {"caption": f"{title} ({line_width}px)"}
```

All controls accept `label=`, `description=`, `section=`, and `port=` in
addition to the fields shown below. Defaults and decorator options must be
literals: write `options=("A", "B")`, not a function call or variable.

| Decorator | Use |
| --- | --- |
| `@corex.text("name", default="")` | One-line text |
| `@corex.text_area("notes", default="")` | Multi-line text |
| `@corex.number("count", default=1, minimum=0, maximum=10, step=1)` | Integer or floating-point field |
| `@corex.switch("enabled", default=True)` | Boolean switch |
| `@corex.dropdown("mode", options=("Fast", "Accurate"))` | Fixed text choices |
| `@corex.slider("width", default=2.0, minimum=0.5, maximum=8.0, step=0.5)` | Bounded integer or floating-point slider |
| `@corex.color("line_color", default="#4f8cff")` | Colour text value and colour editor |
| `@corex.path("output_file", default="", file_filter="CSV (*.csv)")` | File path field |
| `@corex.interval("range", default=(0.0, 1.0))` | Two endpoint fields |
| `@corex.list("labels", default=["A"], item_type=str)` | Typed editable list |

`@corex.slider` always needs `minimum` and `maximum`. `@corex.number` can be
unbounded. For an integer-backed dropdown, give each display label an integer
code; `run` receives the code, so the default is a code too:

```python
@corex.dropdown(
    "legend_position",
    default=1,
    options=("Upper left", "Upper right", "Lower right"),
    codes=(0, 1, 2),
)
```

Text dropdowns can use `searchable=True`. Integer-backed dropdowns cannot be
searchable.

An interval without bounds uses two fields and may have `default=None`. Add
both `minimum` and `maximum` plus a non-null default to use the bounded range
slider. Its direction is explicit and preserved; use `"increasing"` or
`"decreasing"`.

```python
@corex.interval("window", default=(10.0, 0.0))
@corex.interval(
    "x_range",
    default=(0.0, 10.0),
    minimum=0.0,
    maximum=10.0,
    step=0.1,
    direction="increasing",
)
```

Lists require a literal list default. `item_type=` can be `str`, `int`,
`float`, or `corex.Color`. A fixed-choice list uses `options=`; it may also use
integer `codes=` in the same way as a dropdown.

```python
@corex.list("line_widths", default=[1.0, 2.0], item_type=float)
@corex.list("series", default=["A"], options=("A", "B", "C"))
```

## Organize the node

Add `section="Style"` (or another label) to inputs and controls. Sections are
created in first-use order and start collapsed. Outputs do not belong to a
section. A section only changes presentation: the ports and wires remain real
graph topology while it is collapsed.

The same-key control/input created by `port=True` shows one setting plus one
optional input. While that input is wired, the local editor is disabled and
shows the safe upstream display value when available. The authored setting is
not overwritten. Disconnecting restores it immediately.

When a new script is applied, valid same-key settings and compatible same-key
wires stay. Removed, renamed, direction-changed, type-incompatible, or
structure-incompatible sockets are pruned with their wire state. A retained
setting whose value no longer validates is reset to its declared default.

## Write `run`

`run` must use plain required parameters: `ctx` first, followed by every
declared input and every control exactly once. It cannot be `async`, have a
default parameter, a positional-only or keyword-only parameter, `*args`, or
`**kwargs`. Keeping the parameters in declaration order makes the script easy
to scan.

Return a mapping of declared output names to values. You may omit a declared
output to leave it unset; returning an undeclared output key fails the run.
Trusted scripts may instead import and return an existing `NodeResult` instance
with the same output-key rule; a mapping is the normal and simpler choice.

`ctx` provides `log_info(message)`, `log_warning(message)`, and
`log_error(message)` for the run console. Set the node's **Timeout (sec)**
property to a positive value to enforce the existing process-isolated timeout;
`0` leaves it disabled.

The complete, parser-validated Signal Plot-style example is
[python_script_decorated_signal_plot.py](examples/python_script_decorated_signal_plot.py).
It deliberately returns a text summary so it can be copied without a plotting
library; connect its `series` input to a real data source and replace the body
with your renderer when you need an image. Change both the declaration and the
returned key together:

```python
@corex.node
@corex.input("series", value_type=corex.Any, structure="tree", required=True)
@corex.output("image", value_type=corex.Image)
def run(ctx, series):
    image = render_plot(series)
    return {"image": image}
```

## Apply, errors, and old scripts

COREX updates a Python Script node only when you click **Apply**. It reads the
decorators with a bounded, literal-only AST pass and then resolves the normal
`NodeTypeSpec` used by graph, persistence, presentation, and the worker. It
does not import the script or execute decorator expressions while applying.

An invalid draft stays dirty, shows a line-and-column error in the console, and
leaves the last applied source, ports, settings, wires, and collapsed-section
state untouched. A valid Apply is one graph/history action, so undo restores
the prior shape. Explicit Run actions first use a valid pending Apply; automatic
runs keep using the last applied script.

The old assignment-style script and canvas-authored Python Script ports are
removed. Convert this:

```python
result = payload
```

to the pass-through script at the top of this page. Declare every input,
output, and local setting in the source; do not add or rename Python Script
ports on the canvas.

## Limits

Python Script declarations do not update while you type. There are no output
sections, asynchronous `run` functions, varargs, secret defaults, or arbitrary
decorator expressions. Use a normal custom node when you need reusable package
metadata or capabilities outside this compact local-script surface.
