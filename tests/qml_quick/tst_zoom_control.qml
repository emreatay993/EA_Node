// Purpose: Prove live zoom editing and controlled-state synchronization.
// Map: docs/agent_maps/subsystems/qml_shell_and_bridges.md
// Tests: tests/qml_quick/tst_zoom_control.qml
import QtQuick 2.15
import QtQuick.Controls 2.15
import QtTest 1.3
import "../../ea_node_editor/ui_qml/components/common" as Common

TestCase {
    id: testCase
    name: "ZoomControl"
    width: 400
    height: 200
    visible: true
    when: windowShown
    property real viewportZoom: 100
    property bool acceptRequests: true

    Common.ZoomControl {
        id: control
        x: 20; y: 30
        width: implicitWidth; height: implicitHeight
        zoom: testCase.viewportZoom
        onZoomRequested: function(percent) {
            if (testCase.acceptRequests) testCase.viewportZoom = percent;
        }
    }
    SignalSpy { id: requests; target: control; signalName: "zoomRequested" }
    SignalSpy { id: started; target: control; signalName: "zoomStarted" }
    SignalSpy { id: finished; target: control; signalName: "zoomFinished" }

    function init() {
        viewportZoom = 100;
        acceptRequests = true;
        control.minZoom = 10;
        control.maxZoom = 500;
        control.defaultZoom = 100;
        control.zoomDecimals = 0;
        control.showPercentSymbol = false;
        control.editableValue = true;
        control.restoreEditor();
        requests.clear(); started.clear(); finished.clear();
    }
    function field() { return findChild(control, "zoomControlValue"); }
    function slider() { return findChild(control, "zoomControlSlider"); }
    function enter(value) {
        field().forceActiveFocus();
        field().selectAll();
        keySequence("Ctrl+A");
        // keyClicks is not exposed by Qt Quick Test; insert marks the draft explicitly.
        field().text = value;
        field().dirty = true;
        keyClick(Qt.Key_Return);
    }

    function test_entry_validation_and_precision() {
        enter("75"); compare(viewportZoom, 75); compare(slider().value, 75);
        enter("999"); compare(viewportZoom, 500); compare(field().text, "500");
        enter("-5"); compare(viewportZoom, 10);
        enter("75junk"); compare(viewportZoom, 10); compare(field().text, "10");
        enter(""); compare(viewportZoom, 10);
        enter("83.5%"); compare(viewportZoom, 83.5); compare(field().text, "84");
        control.zoomDecimals = 1;
        control.showPercentSymbol = true;
        compare(field().text, "83.5%");
        compare(slider().value, 83.5);
    }
    function test_external_changes_do_not_emit_requests_or_lose_binding() {
        viewportZoom = 125;
        compare(slider().value, 125); compare(field().text, "125");
        compare(requests.count, 0);
        control.zoomIn(); compare(viewportZoom, 135);
        viewportZoom = 73.25;
        compare(slider().value, 73.25); compare(field().text, "73");
        compare(requests.count, 1);
        acceptRequests = false;
        control.setZoom(200);
        compare(control.zoom, 73.25);
        viewportZoom = 240;
        compare(control.zoom, 240); compare(field().text, "240");
    }
    function test_real_typing_escape_and_external_draft_replacement() {
        field().forceActiveFocus();
        field().selectAll();
        keyClick(Qt.Key_7); keyClick(Qt.Key_5);
        verify(field().dirty);
        compare(viewportZoom, 100);
        keyClick(Qt.Key_Return);
        compare(viewportZoom, 75);
        compare(requests.count, 1);
        field().selectAll(); keyClick(Qt.Key_9);
        keyClick(Qt.Key_Escape);
        compare(field().text, "75"); compare(viewportZoom, 75);
        viewportZoom = 83.1;
        field().selectAll(); keyClick(Qt.Key_9);
        viewportZoom = 83.2;
        compare(field().text, "83");
        keyClick(Qt.Key_Return);
        compare(viewportZoom, 83.2);
    }
    function test_live_drag_and_track_click() {
        var s = slider();
        mousePress(s, s.handle.x + 5, s.height / 2);
        mouseMove(s, s.width * 0.65, s.height / 2, 20);
        verify(s.pressed);
        verify(viewportZoom > 200, "Viewport must update before release");
        compare(started.count, 1); compare(finished.count, 0);
        mouseRelease(s, s.width * 0.65, s.height / 2);
        compare(finished.count, 1);
        compare(Number(field().text), viewportZoom);
        mouseClick(s, s.width - 6, s.height / 2);
        verify(viewportZoom > 450);
        viewportZoom = 73;
        compare(s.value, 73); compare(field().text, "73");
    }
    function test_keyboard_reset_and_custom_range() {
        slider().forceActiveFocus();
        keyClick(Qt.Key_Right); compare(viewportZoom, 110);
        keyClick(Qt.Key_Left); compare(viewportZoom, 100);
        control.minZoom = 25; control.maxZoom = 200; control.defaultZoom = 75;
        control.setZoom(500); compare(viewportZoom, 200);
        keyClick(Qt.Key_Home); compare(viewportZoom, 75);
        mouseClick(field(), 20, 12, Qt.RightButton);
        var menu = findChild(control, "zoomControlMenu");
        tryCompare(menu, "opened", true);
        control.setZoom(120);
        keyClick(Qt.Key_Down); keyClick(Qt.Key_Return);
        tryCompare(testCase, "viewportZoom", 75);
        control.editableValue = false;
        verify(field().readOnly);
    }
    function test_wheel_updates_authoritative_zoom() {
        var s = slider();
        mouseWheel(s, s.width / 2, s.height / 2, 0, 120);
        verify(Math.abs(viewportZoom - 110) < 0.000001);
        compare(field().text, "110");
        mouseWheel(s, s.width / 2, s.height / 2, 0, -120);
        verify(Math.abs(viewportZoom - 100) < 0.000001);
        compare(started.count, 2); compare(finished.count, 2);
    }
}
