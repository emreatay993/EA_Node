// Purpose: Own the standard graph-port access, modifier, and dynamic-action menu.
// Map: feature_routes/port_availability_and_default_values.md
// Tests: tests/qml_quick/tst_graph_node_port_context_menu.qml

import QtQuick 2.15
import QtQuick.Controls 2.15

Menu {
    id: menu
    required property Item portsLayer

    objectName: "graphNodePortContextMenu"
    modal: false

    MenuItem {
        objectName: "graphNodePortAccessMetadata"
        visible: menu.portsLayer._isDataPort(menu.portsLayer.contextPortData)
        text: "Access: " + menu.portsLayer._dataAccessLabel(
            menu.portsLayer.contextPortData
        )
        enabled: false
    }
    MenuSeparator {
        visible: menu.portsLayer._isDataPort(menu.portsLayer.contextPortData)
    }
    MenuItem {
        objectName: "graphNodePortModifierGraft"
        text: "Graft"
        visible: menu.portsLayer._isDataPort(menu.portsLayer.contextPortData)
        checkable: true
        checked: menu.portsLayer._modifierChecked("graft")
        enabled: visible && !(menu.portsLayer.host && menu.portsLayer.host.graphReadOnly)
        onTriggered: menu.portsLayer._togglePortModifier("graft")
    }
    MenuItem {
        objectName: "graphNodePortModifierFlatten"
        text: "Flatten"
        visible: menu.portsLayer._isDataPort(menu.portsLayer.contextPortData)
        checkable: true
        checked: menu.portsLayer._modifierChecked("flatten")
        enabled: visible && !(menu.portsLayer.host && menu.portsLayer.host.graphReadOnly)
        onTriggered: menu.portsLayer._togglePortModifier("flatten")
    }
    MenuItem {
        objectName: "graphNodePortModifierSimplify"
        text: "Simplify"
        visible: menu.portsLayer._isDataPort(menu.portsLayer.contextPortData)
        checkable: true
        checked: menu.portsLayer._modifierChecked("simplify")
        enabled: visible && !(menu.portsLayer.host && menu.portsLayer.host.graphReadOnly)
        onTriggered: menu.portsLayer._togglePortModifier("simplify")
    }
    MenuItem {
        objectName: "graphNodePortModifierReverse"
        text: "Reverse"
        visible: menu.portsLayer._isDataPort(menu.portsLayer.contextPortData)
        checkable: true
        checked: menu.portsLayer._modifierChecked("reverse")
        enabled: visible && !(menu.portsLayer.host && menu.portsLayer.host.graphReadOnly)
        onTriggered: menu.portsLayer._togglePortModifier("reverse")
    }
    MenuItem {
        objectName: "graphNodePortModifierClean"
        text: "Clean"
        visible: menu.portsLayer._isDataPort(menu.portsLayer.contextPortData)
        checkable: true
        checked: menu.portsLayer._modifierChecked("clean")
        enabled: visible && !(menu.portsLayer.host && menu.portsLayer.host.graphReadOnly)
        onTriggered: menu.portsLayer._togglePortModifier("clean")
    }
    MenuSeparator {
        visible: Boolean(
            menu.portsLayer.contextPortData
                && menu.portsLayer.contextPortData.principal_eligible
        )
    }
    MenuItem {
        objectName: "graphNodePortPrincipal"
        text: "Principal"
        visible: Boolean(
            menu.portsLayer.contextPortData
                && menu.portsLayer.contextPortData.principal_eligible
        )
        checkable: true
        checked: Boolean(
            menu.portsLayer.contextPortData
                && menu.portsLayer.contextPortData.principal
        )
        enabled: !(menu.portsLayer.host && menu.portsLayer.host.graphReadOnly)
        onTriggered: menu.portsLayer._togglePrincipal()
    }
    MenuSeparator {
        visible: menu.portsLayer._dynamicPortGroupForPort(
            menu.portsLayer.contextPortData
        ) !== null
    }
    MenuItem {
        objectName: "graphNodeDynamicPortInsertBefore"
        text: "Insert Before"
        readonly property var dynamicGroup: menu.portsLayer._dynamicPortGroupForPort(
            menu.portsLayer.contextPortData
        )
        visible: dynamicGroup !== null && Boolean(dynamicGroup.can_insert)
        enabled: visible && menu.portsLayer._dynamicPortAuthoringAllowed()
        onTriggered: {
            var ordinal = menu.portsLayer._dynamicPortOrdinal(
                dynamicGroup,
                menu.portsLayer._portKey(menu.portsLayer.contextPortData)
            );
            if (ordinal >= 0)
                menu.portsLayer._insertDynamicPort(dynamicGroup.id, ordinal);
        }
    }
    MenuItem {
        objectName: "graphNodeDynamicPortInsertAfter"
        text: "Insert After"
        readonly property var dynamicGroup: menu.portsLayer._dynamicPortGroupForPort(
            menu.portsLayer.contextPortData
        )
        visible: dynamicGroup !== null && Boolean(dynamicGroup.can_insert)
        enabled: visible && menu.portsLayer._dynamicPortAuthoringAllowed()
        onTriggered: {
            var ordinal = menu.portsLayer._dynamicPortOrdinal(
                dynamicGroup,
                menu.portsLayer._portKey(menu.portsLayer.contextPortData)
            );
            if (ordinal >= 0)
                menu.portsLayer._insertDynamicPort(dynamicGroup.id, ordinal + 1);
        }
    }
    MenuItem {
        objectName: "graphNodeDynamicPortRename"
        text: "Rename"
        readonly property var dynamicGroup: menu.portsLayer._dynamicPortGroupForPort(
            menu.portsLayer.contextPortData
        )
        visible: dynamicGroup !== null
            && String(dynamicGroup.rename_mode || "none").trim().toLowerCase() !== "none"
        enabled: visible && menu.portsLayer._dynamicPortAuthoringAllowed()
        onTriggered: {
            menu.portsLayer.beginPortLabelEdit(
                menu.portsLayer._portKey(menu.portsLayer.contextPortData),
                String(dynamicGroup.direction || "")
            );
        }
    }
    MenuItem {
        objectName: "graphNodeDynamicPortRemove"
        text: "Remove"
        readonly property var dynamicGroup: menu.portsLayer._dynamicPortGroupForPort(
            menu.portsLayer.contextPortData
        )
        visible: dynamicGroup !== null
            && menu.portsLayer._dynamicPortCanRemove(menu.portsLayer.contextPortData)
        enabled: visible && menu.portsLayer._dynamicPortAuthoringAllowed()
        onTriggered: {
            menu.portsLayer._removeDynamicPort(
                dynamicGroup.id,
                menu.portsLayer._portKey(menu.portsLayer.contextPortData)
            );
        }
    }
}
