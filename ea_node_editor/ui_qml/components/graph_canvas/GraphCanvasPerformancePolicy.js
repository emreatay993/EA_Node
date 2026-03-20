.pragma library

function normalizePerformanceMode(mode) {
    var normalized = String(mode || "").trim();
    if (normalized === "max_performance")
        return "max_performance";
    return "full_fidelity";
}

function resolvePerformancePolicy(mode, viewportInteractionActive, mutationBurstActive) {
    var resolvedMode = normalizePerformanceMode(mode);
    var viewportActive = Boolean(viewportInteractionActive);
    var mutationActive = Boolean(mutationBurstActive);
    var transientActivityActive = viewportActive || mutationActive;
    var maxPerformanceMode = resolvedMode === "max_performance";

    return {
        "resolvedMode": resolvedMode,
        "fullFidelityMode": !maxPerformanceMode,
        "maxPerformanceMode": maxPerformanceMode,
        "viewportInteractionActive": viewportActive,
        "mutationBurstActive": mutationActive,
        "transientActivityActive": transientActivityActive,
        "transientDegradedWindowActive": maxPerformanceMode && transientActivityActive,
        "viewportWorldCacheActive": viewportActive,
        "highQualityRendering": !viewportActive,
        "gridSimplificationActive": false,
        "minimapSimplificationActive": false,
        "edgeLabelSimplificationActive": false,
        "shadowSimplificationActive": false,
        "snapshotProxyReuseActive": false
    };
}
