import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    objectName: "shellStatusStrip"
    property var canvasStateBridgeRef
    property var canvasCommandBridgeRef
    property var statusEngineRef
    property var statusJobsRef
    property var statusMetricsRef
    property var statusNotificationsRef
    readonly property var themePalette: themeBridge.palette
    readonly property string fullFidelityLabel: "Full Fidelity"
    readonly property string maxPerformanceLabel: "Max Performance"
    readonly property string fullFidelityCopy: "Keeps normal visual quality and applies only invisible structural optimizations."
    readonly property string maxPerformanceCopy: "Temporarily simplifies whole-canvas rendering during pan, zoom, and burst edits; idle quality restores automatically."
    readonly property string graphicsPerformanceMode: root.canvasStateBridgeRef
        ? String(root.canvasStateBridgeRef.graphics_performance_mode || "full_fidelity")
        : "full_fidelity"
    readonly property string graphicsPerformanceModeLabel: root.graphicsPerformanceMode === "max_performance"
        ? root.maxPerformanceLabel
        : root.fullFidelityLabel

    Layout.fillWidth: true
    Layout.preferredHeight: 24
    color: themePalette.status_bg
    border.color: themePalette.status_border

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 10

        Text {
            text: root.statusEngineRef.icon_value + " " + root.statusEngineRef.text_value
            color: root.themePalette.status_fg
            font.pixelSize: 11
            font.bold: true
        }
        Text {
            text: root.statusJobsRef.icon_value + " " + root.statusJobsRef.text_value
            color: root.themePalette.status_fg
            font.pixelSize: 11
        }
        Text {
            text: root.statusMetricsRef.icon_value + " " + root.statusMetricsRef.text_value
            color: root.themePalette.status_fg
            font.pixelSize: 11
        }
        Item { Layout.fillWidth: true }
        RowLayout {
            Layout.alignment: Qt.AlignVCenter
            spacing: 6

            Text {
                objectName: "shellStatusStripGraphicsModeSummary"
                text: "Graphics: " + root.graphicsPerformanceModeLabel
                color: root.themePalette.status_fg
                font.pixelSize: 11
            }

            ShellButton {
                objectName: "shellStatusStripFullFidelityButton"
                implicitHeight: 20
                text: root.fullFidelityLabel
                tooltipText: root.fullFidelityCopy
                selectedStyle: root.graphicsPerformanceMode === "full_fidelity"
                onClicked: {
                    if (root.canvasCommandBridgeRef && root.graphicsPerformanceMode !== "full_fidelity")
                        root.canvasCommandBridgeRef.set_graphics_performance_mode("full_fidelity")
                }
            }

            ShellButton {
                objectName: "shellStatusStripMaxPerformanceButton"
                implicitHeight: 20
                text: root.maxPerformanceLabel
                tooltipText: root.maxPerformanceCopy
                selectedStyle: root.graphicsPerformanceMode === "max_performance"
                onClicked: {
                    if (root.canvasCommandBridgeRef && root.graphicsPerformanceMode !== "max_performance")
                        root.canvasCommandBridgeRef.set_graphics_performance_mode("max_performance")
                }
            }
        }
        Text {
            text: root.statusNotificationsRef.icon_value + " " + root.statusNotificationsRef.text_value
            color: root.themePalette.status_fg
            font.pixelSize: 11
        }
    }
}
