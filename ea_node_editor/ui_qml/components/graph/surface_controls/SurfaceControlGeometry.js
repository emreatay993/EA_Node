.pragma library

function _number(value, fallback) {
    var numeric = Number(value);
    return isFinite(numeric) ? numeric : (fallback === undefined ? 0 : fallback);
}

function normalizedRect(rectLike) {
    if (!rectLike)
        return null;
    var width = _number(rectLike.width, 0);
    var height = _number(rectLike.height, 0);
    if (!(width > 0) || !(height > 0))
        return null;
    return {
        "x": _number(rectLike.x, 0),
        "y": _number(rectLike.y, 0),
        "width": width,
        "height": height
    };
}

function rectFromItem(item, hostItem) {
    if (!item || !hostItem || !item.visible)
        return null;
    var width = _number(item.width, 0);
    var height = _number(item.height, 0);
    if (!(width > 0) || !(height > 0))
        return null;
    var topLeft = item.mapToItem(hostItem, 0, 0);
    return normalizedRect({
        "x": topLeft.x,
        "y": topLeft.y,
        "width": width,
        "height": height
    });
}

function rectList(rectLike) {
    var rect = normalizedRect(rectLike);
    return rect ? [rect] : [];
}

function collectVisibleItemRects(items, hostItem) {
    var rects = [];
    if (!items || !hostItem)
        return rects;
    for (var index = 0; index < items.length; index++) {
        var rect = rectFromItem(items[index], hostItem);
        if (rect)
            rects.push(rect);
    }
    return rects;
}

function combineRectLists(rectLists) {
    var combined = [];
    if (!rectLists)
        return combined;
    for (var index = 0; index < rectLists.length; index++) {
        var list = rectLists[index];
        if (!list)
            continue;
        for (var rectIndex = 0; rectIndex < list.length; rectIndex++) {
            var rect = normalizedRect(list[rectIndex]);
            if (rect)
                combined.push(rect);
        }
    }
    return combined;
}
