.pragma library

function pointInRect(localX, localY, rectLike) {
    if (!rectLike)
        return false;
    var rectX = Number(rectLike.x || 0);
    var rectY = Number(rectLike.y || 0);
    var rectWidth = Number(rectLike.width || 0);
    var rectHeight = Number(rectLike.height || 0);
    return rectWidth > 0
        && rectHeight > 0
        && localX >= rectX
        && localX <= rectX + rectWidth
        && localY >= rectY
        && localY <= rectY + rectHeight;
}

function pointInAnyRect(localX, localY, rects) {
    if (!rects || rects.length <= 0)
        return false;
    for (var index = 0; index < rects.length; index++) {
        if (pointInRect(localX, localY, rects[index]))
            return true;
    }
    return false;
}

function claimsBodyInteraction(localX, localY, rects) {
    return pointInAnyRect(localX, localY, rects);
}

function resizeHandleContainsPoint(localX, localY, widthValue, heightValue, handleSize, collapsed) {
    if (collapsed)
        return false;
    var width = Number(widthValue);
    var height = Number(heightValue);
    var size = Number(handleSize);
    if (!isFinite(width) || !isFinite(height) || !isFinite(size) || size <= 0.0)
        return false;
    return localX >= width - size && localY >= height - size;
}
