.pragma library

function _normalizedBoolean(value) {
    return Boolean(value);
}

function normalizePerformanceMode(mode) {
    var normalized = String(mode || "").trim();
    if (normalized === "max_performance")
        return "max_performance";
    return "full_fidelity";
}

function _resolveModeFlags(resolvedMode) {
    var maxPerformanceMode = resolvedMode === "max_performance";
    return {
        "resolvedMode": resolvedMode,
        "fullFidelityMode": !maxPerformanceMode,
        "maxPerformanceMode": maxPerformanceMode
    };
}

function _resolveTransientActivity(viewportInteractionActive, mutationBurstActive) {
    var viewportActive = _normalizedBoolean(viewportInteractionActive);
    var mutationActive = _normalizedBoolean(mutationBurstActive);
    return {
        "viewportInteractionActive": viewportActive,
        "mutationBurstActive": mutationActive,
        "transientActivityActive": viewportActive || mutationActive
    };
}

function _resolveRenderingFlags(viewportActive) {
    return {
        "viewportWorldCacheActive": viewportActive,
        "highQualityRendering": !viewportActive
    };
}

function _resolveSimplificationFlags() {
    return {
        "gridSimplificationActive": false,
        "minimapSimplificationActive": false,
        "edgeLabelSimplificationActive": false,
        "shadowSimplificationActive": false,
        "snapshotProxyReuseActive": false
    };
}

function resolvePerformancePolicy(mode, viewportInteractionActive, mutationBurstActive) {
    var resolvedMode = normalizePerformanceMode(mode);
    var modeFlags = _resolveModeFlags(resolvedMode);
    var activityFlags = _resolveTransientActivity(viewportInteractionActive, mutationBurstActive);
    var renderingFlags = _resolveRenderingFlags(activityFlags.viewportInteractionActive);
    var simplificationFlags = _resolveSimplificationFlags();

    return {
        "resolvedMode": modeFlags.resolvedMode,
        "fullFidelityMode": modeFlags.fullFidelityMode,
        "maxPerformanceMode": modeFlags.maxPerformanceMode,
        "viewportInteractionActive": activityFlags.viewportInteractionActive,
        "mutationBurstActive": activityFlags.mutationBurstActive,
        "transientActivityActive": activityFlags.transientActivityActive,
        "transientDegradedWindowActive": modeFlags.maxPerformanceMode && activityFlags.transientActivityActive,
        "viewportWorldCacheActive": renderingFlags.viewportWorldCacheActive,
        "highQualityRendering": renderingFlags.highQualityRendering,
        "gridSimplificationActive": simplificationFlags.gridSimplificationActive,
        "minimapSimplificationActive": simplificationFlags.minimapSimplificationActive,
        "edgeLabelSimplificationActive": simplificationFlags.edgeLabelSimplificationActive,
        "shadowSimplificationActive": simplificationFlags.shadowSimplificationActive,
        "snapshotProxyReuseActive": simplificationFlags.snapshotProxyReuseActive
    };
}
