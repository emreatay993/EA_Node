import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".." as GraphShared
import "../surface_controls" as SurfaceControls
import "../surface_controls/SurfaceControlGeometry.js" as SurfaceControlGeometry

GraphShared.GraphSurfaceBase {
    id: root
    objectName: "graphDpfWorkflowSurface"

    readonly property string nodeId: host && host.nodeData ? String(host.nodeData.node_id || "") : ""
    readonly property string nodeType: host && host.nodeData ? String(host.nodeData.type_id || "") : ""
    readonly property var summaryLookup: host && host.executionFacts
        ? host.executionFacts.dpfWorkflowSummaryLookup
        : ({})
    readonly property var runSummary: summaryLookup && summaryLookup[nodeId]
        ? summaryLookup[nodeId]
        : ({})
    readonly property bool blocksHostInteraction: false
    readonly property var surfaceActions: []
    readonly property real minimumBodyWidth: 300
    readonly property real minimumBodyHeight: 188
    readonly property string nextRequiredAction: _nextRequiredAction()
    readonly property string fieldMathPortGuidance: _fieldMathPortGuidance()
    readonly property string statusMessage: _statusText()
    readonly property bool incomplete: nextRequiredAction.length > 0
    readonly property var controlRows: _buildControlRows()
    readonly property var embeddedInteractiveRects: {
        var lists = [];
        for (var index = 0; index < controlsRepeater.count; ++index) {
            var row = controlsRepeater.itemAt(index);
            if (row && row.visible && row.controlRects)
                lists.push(row.controlRects);
        }
        return SurfaceControlGeometry.combineRectLists(lists);
    }

    implicitHeight: Math.max(minimumBodyHeight, contentColumn.implicitHeight + 16)

    function dispatchSurfaceAction(_actionId) { return false; }
    function requestInlineEditAt(_localX, _localY) { return false; }
    function commitInlineEditFromExternalInteraction(_localX, _localY) { return false; }

    function _pretty(value) {
        var text = String(value === undefined || value === null ? "" : value).replace(/_/g, " ");
        if (!text.length)
            return "—";
        return text.replace(/\b\w/g, function(letter) { return letter.toUpperCase(); });
    }

    function _scopeModeLabel(value) {
        var labels = {
            "choose_scope": "Choose scope",
            "all": "Whole model",
            "named_selection": "Named selection",
            "node_ids": "Node IDs",
            "element_ids": "Element IDs"
        };
        return labels[String(value || "")] || _pretty(value);
    }

    function _timeModeLabel(value) {
        var labels = {
            "first_set": "First set",
            "last_set": "Last set",
            "all_sets": "All sets",
            "set_ids": "Set IDs",
            "time_values": "Time values"
        };
        return labels[String(value || "")] || _pretty(value);
    }

    function _locationLabel(value) {
        var labels = {
            "auto": "Native location",
            "nodal": "Nodal",
            "elemental": "Elemental",
            "elemental_nodal": "Elemental nodal"
        };
        return labels[String(value || "")] || _pretty(value);
    }

    function _invariantLabel(value) {
        var labels = {
            "von_mises": "Von Mises",
            "principal_1": "Principal S1",
            "principal_2": "Principal S2",
            "principal_3": "Principal S3",
            "intensity": "Stress intensity",
            "max_shear": "Maximum shear"
        };
        return labels[String(value || "")] || _pretty(value);
    }

    function _operationLabel(value) {
        var labels = {
            "add": "Add",
            "subtract": "Subtract",
            "multiply": "Multiply",
            "divide": "Divide",
            "scale": "Scale"
        };
        return labels[String(value || "")] || _pretty(value);
    }

    function _propertyExists(key) {
        return nodeProperties && nodeProperties[key] !== undefined && nodeProperties[key] !== null;
    }

    function _portConnected(key) {
        var ports = host && host.nodeData && host.nodeData.ports ? host.nodeData.ports : [];
        for (var index = 0; index < ports.length; ++index) {
            var port = ports[index];
            if (String(port && port.key || "") === String(key) && Boolean(port.connected))
                return true;
        }
        return false;
    }

    function _pathLabel() {
        var path = propString("path", "").trim();
        if (!path.length)
            return "Choose result file";
        var parts = path.split(/[\\/]/);
        return parts.length ? parts[parts.length - 1] : path;
    }

    function _scopeLabel() {
        var mode = propString("selection_mode", "all");
        if (mode === "choose_scope")
            return "Choose scope";
        if (mode === "all")
            return "Whole model";
        if (mode === "named_selection")
            return propString("named_selection", "").trim() || "Choose named selection";
        if (mode === "node_ids")
            return propString("node_ids", "").trim() ? "Node IDs" : "Choose Node IDs";
        if (mode === "element_ids")
            return propString("element_ids", "").trim() ? "Element IDs" : "Choose Element IDs";
        return _pretty(mode);
    }

    function _timeLabel() {
        var mode = propString("time_scope_mode", "");
        if (!mode.length)
            return "";
        if (mode === "first_set")
            return "First set";
        if (mode === "last_set")
            return "Last set";
        if (mode === "all_sets")
            return "All sets";
        if (mode === "set_ids")
            return propString("set_ids", "").trim() ? "Set IDs" : "Choose Set IDs";
        if (mode === "time_values")
            return propString("time_values", "").trim() ? "Selected time values" : "Choose time values";
        return _pretty(mode);
    }

    function _resultLabel() {
        if (nodeType === "dpf.workflow.result_source")
            return _pathLabel();
        if (nodeType === "dpf.workflow.stress_invariants")
            return _invariantLabel(propString("invariant", "von_mises"));
        if (nodeType === "dpf.workflow.field_math")
            return "Field " + _operationLabel(propString("operation", "add"));
        if (nodeType === "dpf.workflow.table_export")
            return "CSV table export";
        return _pretty(propString("result_name", ""));
    }

    function _configurationSummary() {
        var values = [_resultLabel()];
        if (_propertyExists("selection_mode"))
            values.push(_scopeLabel());
        var time = _timeLabel();
        if (time.length)
            values.push(time);
        if (_propertyExists("location"))
            values.push(_locationLabel(propString("location", "auto")));
        return values.join(" · ");
    }

    function _buildControlRows() {
        var rows = [];
        if (_propertyExists("selection_mode")) {
            var scopeValues = nodeType === "dpf.workflow.time_history_probe"
                ? ["choose_scope", "named_selection", "node_ids", "element_ids"]
                : ["all", "named_selection", "node_ids", "element_ids"];
            rows.push({
                "key": "selection_mode",
                "label": "Scope",
                "value": propString("selection_mode", scopeValues[0]),
                "values": scopeValues,
                "labels": scopeValues.map(_scopeModeLabel)
            });
        }
        if (_propertyExists("time_scope_mode")) {
            var timeValues = ["first_set", "last_set", "all_sets", "set_ids", "time_values"];
            rows.push({
                "key": "time_scope_mode",
                "label": "Time",
                "value": propString("time_scope_mode", "first_set"),
                "values": timeValues,
                "labels": timeValues.map(_timeModeLabel)
            });
        }
        if (_propertyExists("location")) {
            var locationValues = ["auto", "nodal", "elemental", "elemental_nodal"];
            rows.push({
                "key": "location",
                "label": "Location",
                "value": propString("location", "auto"),
                "values": locationValues,
                "labels": locationValues.map(_locationLabel)
            });
        }
        if (_propertyExists("invariant")) {
            var invariantValues = [
                "von_mises", "principal_1", "principal_2", "principal_3", "intensity", "max_shear"
            ];
            rows.push({
                "key": "invariant",
                "label": "Invariant",
                "value": propString("invariant", "von_mises"),
                "values": invariantValues,
                "labels": invariantValues.map(_invariantLabel)
            });
        }
        if (_propertyExists("operation")) {
            var operationValues = ["add", "subtract", "multiply", "divide", "scale"];
            rows.push({
                "key": "operation",
                "label": "Operation",
                "value": propString("operation", "add"),
                "values": operationValues,
                "labels": operationValues.map(_operationLabel)
            });
        }
        return rows;
    }

    function _commitProperty(key, value) {
        if (!host || !host.nodeData || !host.inlinePropertyCommitted)
            return false;
        host.surfaceControlInteractionStarted(nodeId);
        host.inlinePropertyCommitted(nodeId, String(key || ""), value);
        return true;
    }

    function _nextRequiredAction() {
        if ((nodeType === "dpf.workflow.result_source") && !propString("path", "").trim().length
                && !_portConnected("path"))
            return "Choose a result file in Inspector";
        if ([
            "dpf.workflow.result_fields",
            "dpf.workflow.min_max_envelope",
            "dpf.workflow.time_history_probe",
            "dpf.workflow.stress_invariants"
        ].indexOf(nodeType) >= 0 && !_portConnected("model"))
            return "Connect Model";
        if (_propertyExists("result_name") && !propString("result_name", "").trim().length)
            return "Choose a result type in Inspector";
        var scope = propString("selection_mode", "all");
        if (scope === "choose_scope")
            return "Choose a named selection, Node IDs, or Element IDs in Inspector";
        if (scope === "named_selection" && !propString("named_selection", "").trim().length)
            return "Choose a named selection in Inspector";
        if (scope === "node_ids" && !propString("node_ids", "").trim().length)
            return "Enter Node IDs in Inspector";
        if (scope === "element_ids" && !propString("element_ids", "").trim().length)
            return "Enter Element IDs in Inspector";
        var timeMode = propString("time_scope_mode", "");
        if (timeMode === "set_ids" && !propString("set_ids", "").trim().length)
            return "Enter Set IDs in Inspector";
        if (timeMode === "time_values" && !propString("time_values", "").trim().length)
            return "Enter time values in Inspector";
        if (nodeType === "dpf.workflow.field_math") {
            if (!_portConnected("a"))
                return "Connect input A";
            if (propString("operation", "add") !== "scale" && !_portConnected("b"))
                return "B required for " + _operationLabel(propString("operation", "add"))
                    + " — connect input B";
        }
        if (nodeType === "dpf.workflow.table_export" && !_portConnected("fields"))
            return "Connect Fields";
        if (nodeType === "dpf.workflow.table_export" && !_portConnected("model"))
            return "Connect Model";
        return "";
    }

    function _fieldMathPortGuidance() {
        if (nodeType !== "dpf.workflow.field_math")
            return "";
        var operation = propString("operation", "add");
        var operationLabel = _operationLabel(operation);
        if (operation === "scale") {
            return _portConnected("b")
                ? "B unused for Scale — disconnect input B"
                : "B unused for Scale";
        }
        return _portConnected("b")
            ? "B required for " + operationLabel + " — connected"
            : "B required for " + operationLabel + " — connect input B";
    }

    function _statusText() {
        if (host && host.isFailedNode)
            return "Execution failed — open Errors for details";
        if (host && host.isRunningNode)
            return "Running DPF post-processing…";
        if (incomplete)
            return "Setup incomplete — " + nextRequiredAction;
        if (String(runSummary.state || "") === "stale")
            return "Previous result is stale — run again";
        if (String(runSummary.headline || "").length)
            return "Ready · latest result available";
        if (fieldMathPortGuidance.length)
            return fieldMathPortGuidance;
        return "Ready to run";
    }

    function _statusColor() {
        if (host && host.isFailedNode)
            return host.failureOutlineColor;
        if (host && host.isRunningNode)
            return host.runningOutlineColor;
        if (incomplete || String(runSummary.state || "") === "stale"
                || (nodeType === "dpf.workflow.field_math"
                    && propString("operation", "add") === "scale" && _portConnected("b")))
            return host ? host.warningOutlineColor : "#d4a72c";
        return host ? host.completedOutlineColor : "#3fb950";
    }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.host ? Qt.alpha(root.host.inlineRowColor, 0.72) : "#20242b"
        border.width: 1
        border.color: root.host ? root.host.inlineRowBorderColor : "#3a414d"
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        Text {
            objectName: "dpfWorkflowConfigurationSummary"
            Layout.fillWidth: true
            text: root._configurationSummary()
            color: root.host ? root.host.inlineInputTextColor : "#eef2f7"
            font.pixelSize: root.host && root.host.graphSharedTypography
                ? root.host.graphSharedTypography.inlinePropertyPixelSize
                : 10
            font.bold: true
            wrapMode: Text.Wrap
            elide: Text.ElideRight
            maximumLineCount: 2
        }

        Text {
            objectName: "dpfWorkflowFieldMathGuidance"
            Layout.fillWidth: true
            visible: root.fieldMathPortGuidance.length > 0
            text: root.fieldMathPortGuidance
            color: root.host ? root.host.inlineLabelColor : "#b7c0ce"
            font.pixelSize: 8
            elide: Text.ElideRight
            maximumLineCount: 1
        }

        Repeater {
            id: controlsRepeater
            model: root.controlRows

            delegate: RowLayout {
                id: controlRow
                objectName: "dpfWorkflowControl_" + String(modelData.key || "")
                Layout.fillWidth: true
                spacing: 6
                readonly property var controlRects: editor.embeddedInteractiveRects

                Text {
                    Layout.preferredWidth: 58
                    text: String(modelData.label || "")
                    color: root.host ? root.host.inlineLabelColor : "#b7c0ce"
                    font.pixelSize: 9
                    elide: Text.ElideRight
                }

                SurfaceControls.GraphSurfaceComboBox {
                    id: editor
                    Layout.fillWidth: true
                    host: root.host
                    model: modelData.labels || []
                    currentIndex: Math.max(0, (modelData.values || []).indexOf(modelData.value))
                    controlHeight: 24
                    onControlStarted: {
                        if (root.host)
                            root.host.surfaceControlInteractionStarted(root.nodeId);
                    }
                    onActivated: function(index) {
                        var values = modelData.values || [];
                        if (index >= 0 && index < values.length)
                            root._commitProperty(modelData.key, values[index]);
                    }
                }
            }
        }

        Rectangle {
            objectName: "dpfWorkflowStatusStrip"
            Layout.fillWidth: true
            implicitHeight: statusText.implicitHeight + 8
            radius: 3
            color: Qt.alpha(root._statusColor(), 0.13)
            border.width: 1
            border.color: Qt.alpha(root._statusColor(), 0.66)

            Text {
                id: statusText
                anchors.fill: parent
                anchors.margins: 4
                text: root.statusMessage
                color: root.host ? root.host.inlineInputTextColor : "#eef2f7"
                font.pixelSize: 9
                wrapMode: Text.Wrap
                verticalAlignment: Text.AlignVCenter
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            visible: String(root.runSummary.headline || "").length > 0

            Text {
                objectName: "dpfWorkflowResultHeadline"
                Layout.fillWidth: true
                text: String(root.runSummary.headline || "")
                color: root.host ? root.host.inlineInputTextColor : "#eef2f7"
                font.pixelSize: 10
                font.bold: true
                elide: Text.ElideRight
            }
            Text {
                objectName: "dpfWorkflowResultDetail"
                Layout.fillWidth: true
                text: String(root.runSummary.detail || "")
                color: root.host ? root.host.inlineLabelColor : "#b7c0ce"
                font.pixelSize: 9
                elide: Text.ElideRight
                visible: text.length > 0
            }
            ColumnLayout {
                id: factsColumn
                Layout.fillWidth: true
                spacing: 1
                Repeater {
                    model: root.runSummary.facts ? root.runSummary.facts.slice(0, 3) : []
                    Text {
                        Layout.fillWidth: true
                        text: String(modelData.label || "") + ": " + String(modelData.value || "")
                        color: root.host ? root.host.inlineLabelColor : "#b7c0ce"
                        font.pixelSize: 8
                        elide: Text.ElideMiddle
                        maximumLineCount: 1
                    }
                }
            }
        }
    }
}
