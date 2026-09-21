// Shared canvas-background color mapping consumed by GraphCanvasBackground.
// Port notches are true chrome cutouts and do not imitate this fill color.
.pragma library

function effectiveVariant(variant) {
    var normalized = String(variant || "theme").toLowerCase().trim();
    if (normalized === "dark" || normalized === "light" || normalized === "white")
        return normalized;
    return "theme";
}

function fillColor(variant, themePalette) {
    var resolved = effectiveVariant(variant);
    if (resolved === "dark")
        return "#1d1f24";
    if (resolved === "light")
        return "#f3f5f8";
    if (resolved === "white")
        return "#ffffff";
    return themePalette && themePalette.canvas_bg ? themePalette.canvas_bg : "#1d1f24";
}
