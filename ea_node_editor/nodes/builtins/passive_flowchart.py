from __future__ import annotations

from ea_node_editor.nodes.builtins.passive_flow_ports import CARDINAL_PASSIVE_FLOW_PORTS
from ea_node_editor.nodes.decorators import node_type, prop_str
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult

PASSIVE_FLOWCHART_CATEGORY = "Flowchart"

PASSIVE_FLOWCHART_START_TYPE_ID = "passive.flowchart.start"
PASSIVE_FLOWCHART_END_TYPE_ID = "passive.flowchart.end"
PASSIVE_FLOWCHART_PROCESS_TYPE_ID = "passive.flowchart.process"
PASSIVE_FLOWCHART_DECISION_TYPE_ID = "passive.flowchart.decision"
PASSIVE_FLOWCHART_DOCUMENT_TYPE_ID = "passive.flowchart.document"
PASSIVE_FLOWCHART_CONNECTOR_TYPE_ID = "passive.flowchart.connector"
PASSIVE_FLOWCHART_INPUT_OUTPUT_TYPE_ID = "passive.flowchart.input_output"
PASSIVE_FLOWCHART_PREDEFINED_PROCESS_TYPE_ID = "passive.flowchart.predefined_process"
PASSIVE_FLOWCHART_DATABASE_TYPE_ID = "passive.flowchart.database"


class _PassiveFlowchartNodePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


def _flowchart_title_property(default_title: str):
    return (
        prop_str("title", default_title, "Title"),
        prop_str("body", default_title, "Body", inspector_editor="textarea"),
    )


@node_type(
    type_id=PASSIVE_FLOWCHART_START_TYPE_ID,
    display_name="Start",
    category=PASSIVE_FLOWCHART_CATEGORY,
    icon="play_circle",
    description="Flowchart start terminator.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=_flowchart_title_property("Start"),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="start",
)
class PassiveFlowchartStartNodePlugin(_PassiveFlowchartNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_FLOWCHART_END_TYPE_ID,
    display_name="End",
    category=PASSIVE_FLOWCHART_CATEGORY,
    icon="stop_circle",
    description="Flowchart end terminator.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=_flowchart_title_property("End"),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="end",
)
class PassiveFlowchartEndNodePlugin(_PassiveFlowchartNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_FLOWCHART_PROCESS_TYPE_ID,
    display_name="Process",
    category=PASSIVE_FLOWCHART_CATEGORY,
    icon="crop_din",
    description="Flowchart process step.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=_flowchart_title_property("Process"),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="process",
)
class PassiveFlowchartProcessNodePlugin(_PassiveFlowchartNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_FLOWCHART_DECISION_TYPE_ID,
    display_name="Decision",
    category=PASSIVE_FLOWCHART_CATEGORY,
    icon="diamond",
    description="Flowchart decision branch.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=_flowchart_title_property("Decision"),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="decision",
)
class PassiveFlowchartDecisionNodePlugin(_PassiveFlowchartNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_FLOWCHART_DOCUMENT_TYPE_ID,
    display_name="Document",
    category=PASSIVE_FLOWCHART_CATEGORY,
    icon="description",
    description="Flowchart document step.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=_flowchart_title_property("Document"),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="document",
)
class PassiveFlowchartDocumentNodePlugin(_PassiveFlowchartNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_FLOWCHART_CONNECTOR_TYPE_ID,
    display_name="Connector",
    category=PASSIVE_FLOWCHART_CATEGORY,
    icon="radio_button_checked",
    description="Flowchart connector marker.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=_flowchart_title_property("Connector"),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="connector",
)
class PassiveFlowchartConnectorNodePlugin(_PassiveFlowchartNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_FLOWCHART_INPUT_OUTPUT_TYPE_ID,
    display_name="Input / Output",
    category=PASSIVE_FLOWCHART_CATEGORY,
    icon="input",
    description="Flowchart input or output step.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=_flowchart_title_property("Input / Output"),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="input_output",
)
class PassiveFlowchartInputOutputNodePlugin(_PassiveFlowchartNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_FLOWCHART_PREDEFINED_PROCESS_TYPE_ID,
    display_name="Predefined Process",
    category=PASSIVE_FLOWCHART_CATEGORY,
    icon="view_column",
    description="Flowchart predefined process step.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=_flowchart_title_property("Predefined Process"),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="predefined_process",
)
class PassiveFlowchartPredefinedProcessNodePlugin(_PassiveFlowchartNodePlugin):
    pass


@node_type(
    type_id=PASSIVE_FLOWCHART_DATABASE_TYPE_ID,
    display_name="Database",
    category=PASSIVE_FLOWCHART_CATEGORY,
    icon="storage",
    description="Flowchart database store.",
    ports=CARDINAL_PASSIVE_FLOW_PORTS,
    properties=_flowchart_title_property("Database"),
    collapsible=False,
    runtime_behavior="passive",
    surface_family="flowchart",
    surface_variant="database",
)
class PassiveFlowchartDatabaseNodePlugin(_PassiveFlowchartNodePlugin):
    pass


PASSIVE_FLOWCHART_NODE_PLUGINS = (
    PassiveFlowchartStartNodePlugin,
    PassiveFlowchartEndNodePlugin,
    PassiveFlowchartProcessNodePlugin,
    PassiveFlowchartDecisionNodePlugin,
    PassiveFlowchartDocumentNodePlugin,
    PassiveFlowchartConnectorNodePlugin,
    PassiveFlowchartInputOutputNodePlugin,
    PassiveFlowchartPredefinedProcessNodePlugin,
    PassiveFlowchartDatabaseNodePlugin,
)


__all__ = [
    "PASSIVE_FLOWCHART_CATEGORY",
    "PASSIVE_FLOWCHART_CONNECTOR_TYPE_ID",
    "PASSIVE_FLOWCHART_DATABASE_TYPE_ID",
    "PASSIVE_FLOWCHART_DECISION_TYPE_ID",
    "PASSIVE_FLOWCHART_DOCUMENT_TYPE_ID",
    "PASSIVE_FLOWCHART_END_TYPE_ID",
    "PASSIVE_FLOWCHART_INPUT_OUTPUT_TYPE_ID",
    "PASSIVE_FLOWCHART_NODE_PLUGINS",
    "PASSIVE_FLOWCHART_PREDEFINED_PROCESS_TYPE_ID",
    "PASSIVE_FLOWCHART_PROCESS_TYPE_ID",
    "PASSIVE_FLOWCHART_START_TYPE_ID",
    "PassiveFlowchartConnectorNodePlugin",
    "PassiveFlowchartDatabaseNodePlugin",
    "PassiveFlowchartDecisionNodePlugin",
    "PassiveFlowchartDocumentNodePlugin",
    "PassiveFlowchartEndNodePlugin",
    "PassiveFlowchartInputOutputNodePlugin",
    "PassiveFlowchartPredefinedProcessNodePlugin",
    "PassiveFlowchartProcessNodePlugin",
    "PassiveFlowchartStartNodePlugin",
]
