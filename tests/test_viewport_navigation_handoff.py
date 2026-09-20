# Purpose: Prove deferred viewport publication preserves ordered navigation math.
# Map: subsystems/graph_canvas.md
# Tests: tests/test_viewport_navigation_handoff.py
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


def _state(view):
    return (view.zoom_value, view.center_x, view.center_y)


def test_navigation_accumulates_without_publishing_before_preview_is_ready():
    expected, held = ViewportBridge(), ViewportBridge()
    held.set_view_change_guard(lambda: False)
    published = []
    held.view_state_changed.connect(lambda: published.append(_state(held)))
    for view in (expected, held):
        view.pan_by(12, -9)
        view.adjust_zoom_at_viewport_point(1.15, 270, 440)
        view.adjust_zoom_at_viewport_point(1.15, 330, 480)
        view.pan_by(-2, 11)
    assert _state(held) == (1.0, 0.0, 0.0)
    assert held.navigation_zoom() == expected.zoom_value
    assert published == []
    held.flush_deferred_view_state()
    assert _state(held) == _state(expected)
    assert published == [_state(expected)]
    held.flush_deferred_view_state()
    assert len(published) == 1


def test_latest_absolute_target_supersedes_queued_navigation():
    view = ViewportBridge()
    blocked = True
    view.set_view_change_guard(lambda: not blocked)
    view.adjust_zoom(2)
    view.pan_by(10, 20)
    blocked = False
    view.set_view_state(0.5, -30, 45)
    view.flush_deferred_view_state()
    assert _state(view) == (0.5, -30.0, 45.0)


def test_cancelling_a_workspace_handoff_discards_old_navigation():
    view = ViewportBridge()
    view.set_view_change_guard(lambda: False)
    view.adjust_zoom(2)
    view.pan_by(10, 20)
    view.cancel_deferred_view_state()
    view.flush_deferred_view_state()
    assert _state(view) == (1.0, 0.0, 0.0)


def test_noop_navigation_does_not_start_a_handoff():
    view = ViewportBridge()
    calls = []
    view.set_view_change_guard(lambda: calls.append(True) or False)
    assert view.set_view_state(1, 0, 0) is False
    assert calls == []
