.pragma library
// Purpose: Paint EdgePaintPolicy flow-edge arrowhead shapes on a Canvas 2D context (edge canvas and toolbar glyphs).
// Map: feature_routes/edge_routing_labels_progress.md
// Tests: tests/test_flow_edge_labels.py

function paintMarkerShape(ctx, shape, color) {
    if (!ctx || !shape)
        return;
    ctx.save();
    ctx.setLineDash([]);
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = Math.max(0.01, Number(shape.strokeWidth) || 1.0);
    ctx.beginPath();
    var points = shape.points || [];
    for (var i = 0; i < points.length; i++) {
        if (i === 0)
            ctx.moveTo(Number(points[i].x), Number(points[i].y));
        else
            ctx.lineTo(Number(points[i].x), Number(points[i].y));
    }
    if (shape.closed)
        ctx.closePath();
    if (shape.filled)
        ctx.fill();
    ctx.stroke();
    ctx.restore();
}
