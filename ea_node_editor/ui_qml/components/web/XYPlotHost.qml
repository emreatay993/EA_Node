// Purpose: Lazily host the local interactive XY client for a Media Panel session.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_plot_qml.py
import QtQuick 2.15

Item {
    id: root
    objectName: "xyPlotHost"
    property var payload: ({})
    property var sessionBridge: null
    property var webEngineItem: null
    property string errorText: ""
    readonly property bool canLoad: visible && !!sessionBridge && Boolean(payload.webengine_available)
        && String(payload.asset_url || "").length > 0
    clip: true
    onCanLoadChanged: Qt.callLater(sync)
    onSessionBridgeChanged: { release(); Qt.callLater(sync); }
    Component.onCompleted: Qt.callLater(sync)
    Component.onDestruction: release()

    Connections {
        target: root.sessionBridge || null
        function onCloseRequested() { root.requestClose(); }
    }

    function fail(message) {
        errorText = String(message);
        if (sessionBridge) sessionBridge.host_failed(errorText);
    }
    function requestClose() {
        if (!webEngineItem) return;
        webEngineItem.runJavaScript("window.corexXY && window.corexXY.requestClose()");
    }
    function handleEscape() {
        if (!webEngineItem) {
            if (sessionBridge) sessionBridge.request_close();
            return;
        }
        var bridge = sessionBridge;
        webEngineItem.runJavaScript("Boolean(window.corexXY && window.corexXY.cancelInteraction())", function(cancelled) {
            if (!cancelled && bridge && bridge === root.sessionBridge) bridge.request_close();
        });
    }
    function release() {
        if (webEngineItem) webEngineItem.destroy();
        webEngineItem = null;
    }
    function sync() {
        if (!canLoad) { release(); return; }
        if (webEngineItem) return;
        try {
            errorText = "";
            webEngineItem = Qt.createQmlObject(componentSource(), root, "xyPlotDynamic");
            webEngineItem.bridgeObject = sessionBridge;
            webEngineItem.pageUrl = String(payload.asset_url);
            webEngineItem.forceActiveFocus();
        } catch (error) { fail("Plot could not be loaded: " + error); }
    }
    function componentSource() {
        return [
            'import QtQuick 2.15', 'import QtWebEngine', 'import QtWebChannel',
            'Item { id: host; anchors.fill: parent; property var bridgeObject: null; property string pageUrl: "";',
            'function runJavaScript(script, callback) { if (callback) view.runJavaScript(script, callback); else view.runJavaScript(script); }',
            'onBridgeObjectChanged: { if (bridgeObject) channel.registerObjects({"xyBridge": bridgeObject}); }',
            'onPageUrlChanged: { if (bridgeObject) view.url = pageUrl; }',
            'WebChannel { id: channel; registeredObjects: [] }',
            'WebEngineView { id: view; objectName: "xyPlotWebEngineView"; anchors.fill: parent; focus: true; webChannel: channel;',
            'settings.localContentCanAccessRemoteUrls: false; settings.localContentCanAccessFileUrls: true;',
            'onNavigationRequested: function(request) { if (request.url.toString() !== host.pageUrl) request.action = WebEngineNavigationRequest.IgnoreRequest; }',
            'onNewWindowRequested: function(request) { }',
            'onLoadingChanged: function(info) { if (info.status === WebEngineView.LoadFailedStatus && host.bridgeObject) host.bridgeObject.host_failed(info.errorString); }',
            'onRenderProcessTerminated: function(status, code) { if (host.bridgeObject) host.bridgeObject.host_failed("Plot renderer stopped (" + code + ")."); }',
            '}', '}'
        ].join('\n');
    }
    Text {
        anchors.centerIn: parent
        width: Math.max(0, parent.width - 40)
        visible: !root.canLoad || root.errorText.length > 0
        text: root.errorText || String(root.payload.webengine_reason || "Preparing plot…")
        color: "#a72316"
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
    }
}
