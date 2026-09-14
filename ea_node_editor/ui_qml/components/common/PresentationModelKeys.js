.pragma library

// Purpose: Separate presentation values from repeater identities.
// Map: feature_routes/run_controller_selected_workspace_state.md
// Tests: tests/test_presentation_model_keys.py, tests/test_shell_run_controller.py

// Repeater topology depends on identities, while delegate data stays bound to
// the current payload. Return the previous array for ordinary value updates so
// QML retains editors; structural changes rebuild the affected repeater.
function retain(previous, next) {
    if (!previous || previous.length !== next.length)
        return next;
    for (var row = 0; row < next.length; row++) {
        if (previous[row].length !== next[row].length)
            return next;
        for (var field = 0; field < next[row].length; field++) {
            if (previous[row][field] !== next[row][field])
                return next;
        }
    }
    return previous;
}

function properties(items) {
    return (items || []).map(function(item) {
        return [String(item.key || ""), String(item.type || ""), String(item.inline_editor || ""),
                String(item.list_item_type || ""), Boolean(item.exact_selectors)];
    });
}

function groups(items) {
    return (items || []).map(function(item) { return [String(item.group_id || "")]; });
}

function ports(items) {
    return (items || []).map(function(item) {
        return [String(item.key || ""), String(item.direction || ""), String(item.kind || "")];
    });
}

function settings(items) {
    return (items || []).map(function(item) {
        var property = item.property || ({});
        return [String(item.kind || ""), String(item.port_key || ""),
                String(item.property_key || ""), String(property.type || ""),
                String(property.inline_editor || "")];
    });
}
