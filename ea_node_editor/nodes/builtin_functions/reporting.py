# Purpose: Hold inert decorated source for Markdown flowchart nodes.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_reporting_nodes.py

SOURCE = r"""import corex

from ea_node_editor.nodes.builtins.reporting import (
    make_flowchart_node_value,
    render_flowchart,
)


@corex.node(
    id="reporting.markdown_flowchart_node",
    name="Markdown Flowchart Node",
    category=("Utilities", "Reporting"),
    icon="git-branch",
    description="Builds one typed node for a Markdown Mermaid flowchart.",
    keywords=("markdown", "mermaid", "flowchart", "reporting"),
)
@corex.input(
    "text",
    value_type="COREX.DataTypes.String",
    required=True,
    label="Text",
)
@corex.input(
    "input_nodes",
    value_type="COREX.Reporting.FlowchartNode",
    structure="list",
    required=False,
    label="Input Nodes",
)
@corex.number(
    "shape",
    default=0,
    minimum=0,
    maximum=8,
    label="Shape",
    port=True,
    _inline_editor="",
    _port_label="Shape",
    _port_required=True,
    _port_value_type="COREX.DataTypes.Int",
)
@corex.number(
    "link_type",
    default=0,
    minimum=0,
    maximum=3,
    label="Link Type",
    port=True,
    _inline_editor="",
    _port_label="Link Type",
    _port_required=True,
    _port_value_type="COREX.DataTypes.Int",
)
@corex.input(
    "link_text",
    value_type="COREX.DataTypes.String",
    required=False,
    label="Link Text",
)
@corex.output(
    "node",
    value_type="COREX.Reporting.FlowchartNode",
    label="Node",
)
def markdown_flowchart_node(ctx, text, input_nodes, link_text, settings):
    return {
        "node": make_flowchart_node_value(
            text=text,
            input_nodes=input_nodes,
            shape=settings.shape,
            link_type=settings.link_type,
            link_text=link_text if "link_text" in ctx.inputs else "",
        )
    }


@corex.node(
    id="reporting.markdown_flowchart",
    name="Markdown Flowchart",
    category=("Utilities", "Reporting"),
    icon="git-branch",
    description="Renders typed flowchart nodes as fenced Mermaid Markdown.",
    keywords=("markdown", "mermaid", "flowchart", "reporting"),
)
@corex.input(
    "nodes",
    value_type="COREX.Reporting.FlowchartNode",
    structure="list",
    required=True,
    label="Nodes",
)
@corex.number(
    "direction",
    default=0,
    minimum=0,
    maximum=1,
    label="Direction",
    port=True,
    _inline_editor="",
    _port_label="Direction",
    _port_required=True,
    _port_value_type="COREX.DataTypes.Int",
)
@corex.output(
    "flowchart",
    value_type="COREX.DataTypes.String",
    label="Flowchart",
)
def markdown_flowchart(ctx, nodes, settings):
    del ctx
    if type(nodes) is not list:
        raise ValueError("flowchart nodes must be a list")
    return {"flowchart": render_flowchart(nodes, settings.direction)}
"""

__all__ = ["SOURCE"]
