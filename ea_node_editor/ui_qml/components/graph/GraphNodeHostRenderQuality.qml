import QtQml 2.15

QtObject {
    id: root
    property var host: null

    readonly property var renderQuality: root.normalizedRenderQuality(
        root.host && root.host.nodeData ? root.host.nodeData.render_quality : null
    )
    readonly property bool viewportInteractionProxyEligible: {
        if (!root.host)
            return false;
        if (root.host.fullFidelityMode || !root.host.viewportInteractionCacheActive)
            return false;
        if (!root.proxySurfaceCapable || root.renderQuality.weight_class !== "heavy")
            return false;
        var surfaceFamily = String(root.host.surfaceFamily || "").trim();
        return surfaceFamily === "media" || surfaceFamily === "viewer";
    }
    // Heavy media/viewer surfaces still pay significant bitmap resampling cost
    // during viewport interaction, so let them reuse the existing proxy path in
    // transient max-performance windows instead of staying at full quality.
    readonly property bool reducedQualityRequested: root.host
        ? (root.host.snapshotReuseActive || root.viewportInteractionProxyEligible)
        : false
    readonly property string requestedQualityTier: root.reducedQualityRequested ? "reduced" : "full"
    readonly property bool proxySurfaceCapable: root.renderQuality.max_performance_strategy === "proxy_surface"
        && root.supportsRenderQualityTier("proxy")
    readonly property bool proxySurfaceRequested: root.requestedQualityTier === "reduced" && root.proxySurfaceCapable
    readonly property string resolvedQualityTier: {
        if (root.proxySurfaceRequested)
            return "proxy";
        if (root.requestedQualityTier === "reduced" && root.supportsRenderQualityTier("reduced"))
            return "reduced";
        return "full";
    }
    readonly property var surfaceQualityContext: ({
        "requested_quality_tier": root.requestedQualityTier,
        "resolved_quality_tier": root.resolvedQualityTier,
        "render_quality": root.renderQuality,
        "proxy_surface_requested": root.proxySurfaceRequested
    })

    function normalizedRenderQuality(renderQualityLike) {
        var normalized = {
            "weight_class": "standard",
            "max_performance_strategy": "generic_fallback",
            "supported_quality_tiers": ["full"]
        };
        if (!renderQualityLike)
            return normalized;

        var weightClass = String(renderQualityLike.weight_class || "").trim();
        if (weightClass === "heavy")
            normalized.weight_class = "heavy";

        var strategy = String(renderQualityLike.max_performance_strategy || "").trim();
        if (strategy === "proxy_surface")
            normalized.max_performance_strategy = "proxy_surface";

        var tiers = root.normalizedQualityTierList(renderQualityLike.supported_quality_tiers);
        if (tiers.length > 0)
            normalized.supported_quality_tiers = tiers;
        return normalized;
    }

    function normalizedQualityTierList(value) {
        if (value === undefined || value === null)
            return [];

        var rawItems = [];
        if (typeof value === "string")
            rawItems = [value];
        else if (value.length !== undefined)
            rawItems = value;
        else
            rawItems = [value];

        var normalized = [];
        var seen = {};
        for (var index = 0; index < rawItems.length; index++) {
            var tier = String(rawItems[index] || "").trim();
            if (tier !== "full" && tier !== "reduced" && tier !== "proxy")
                continue;
            if (seen[tier])
                continue;
            normalized.push(tier);
            seen[tier] = true;
        }
        return normalized;
    }

    function supportsRenderQualityTier(tier) {
        return root.renderQuality.supported_quality_tiers.indexOf(String(tier || "").trim()) >= 0;
    }
}
