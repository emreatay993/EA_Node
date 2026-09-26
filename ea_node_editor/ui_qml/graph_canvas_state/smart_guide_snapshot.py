# Purpose: Pure smart-guide snapshot for a node drag or resize: the moving nodes' drawn rects and the candidates they may snap to, without the moving nodes, their Group contents or the Groups that contain them, capped to the most relevant candidates around the moving rects, with how far the nearest left-out candidate lies along each axis.
# Map: docs/agent_maps/feature_routes/graph_canvas_input_layers.md
# Tests: tests/test_graph_canvas_smart_guide_snapshot.py
from __future__ import annotations

import heapq
import math
from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Any

from ea_node_editor.ui_qml.graph_canvas_viewport_index import SceneRect, normalize_node_id, payload_scene_rect

# Group backdrop payload keys that list a Group's direct members (backdrop_partitioner).
_MEMBER_KEYS = ("member_node_ids", "member_backdrop_ids")

# Most candidates a snapshot holds. The engine indexes them in JS once per snapshot, and zoomed out a
# viewport can hold over a thousand: on the 1200-node stress fixture, 1199 candidates cost about 50 ms
# to index plus garbage-collection stalls of several hundred ms. Measured in the app, the index costs
# about 9 us a candidate up to 160 (1.1 ms at 128, 1.4-1.6 ms at 160), then jumps: 3.4-4.2 ms at 192,
# 8.4-9 ms at 256. 128 stays clear of that jump; with it the first drag frame zoomed out to 0.25 and
# 0.12 costs about 6-8 ms more than without guides, down from 17-40 ms, without the GC stalls.
SMART_GUIDE_CANDIDATE_LIMIT = 128


def smart_guide_query_rect(payload: object) -> SceneRect | None:
    """``payload`` as ``(x, y, width, height)`` when every value is finite and the size is positive."""
    if not isinstance(payload, Mapping):
        return None
    try:
        x, y, width, height = (float(payload[key]) for key in ("x", "y", "width", "height"))
    except (KeyError, TypeError, ValueError):
        return None
    if width <= 0.0 or height <= 0.0:
        return None
    if not all(math.isfinite(value) for value in (x, y, width, height, x + width, y + height)):
        return None
    return x, y, width, height


def smart_guide_offset(options: object) -> tuple[float, float]:
    """The ``offset_x`` / ``offset_y`` of the snapshot options; a missing or non-finite value is 0."""
    offset = [0.0, 0.0]
    if isinstance(options, Mapping):
        for axis, key in enumerate(("offset_x", "offset_y")):
            try:
                value = float(options.get(key, 0.0))
            except (TypeError, ValueError):
                continue
            if math.isfinite(value):
                offset[axis] = value
    return offset[0], offset[1]


def smart_guide_rect(payload: object) -> dict[str, Any] | None:
    """Compact ``{node_id, x, y, width, height}`` of a node payload, sized like ``payload_scene_rect``."""
    if not isinstance(payload, dict):
        return None
    rect = payload_scene_rect(payload)
    node_id = normalize_node_id(payload.get("node_id"))
    if rect is None or not node_id:
        return None
    x, y, width, height = rect
    return {"node_id": node_id, "x": x, "y": y, "width": width, "height": height}


def _owner_id(payload: object) -> str:
    """The Group that directly holds a node payload (its ``owner_backdrop_id``), or ""."""
    return normalize_node_id(payload.get("owner_backdrop_id")) if isinstance(payload, Mapping) else ""


def _listed_owners(backdrops: Iterable[object]) -> dict[str, str]:
    """Member id -> the first of ``backdrops`` whose member lists name it."""
    owners: dict[str, str] = {}
    for backdrop in backdrops:
        backdrop_id = normalize_node_id(backdrop.get("node_id")) if isinstance(backdrop, Mapping) else ""
        if not backdrop_id:
            continue
        for key in _MEMBER_KEYS:
            members = backdrop.get(key)
            if isinstance(members, (list, tuple)):
                for member in members:
                    owners.setdefault(normalize_node_id(member), backdrop_id)
    return owners


class _OwnerChains:
    """Direct owners along ``owner_backdrop_id`` chains, read from node payloads.

    A node without a payload is a hidden member of a collapsed Group, and only the Groups' member lists
    name its owner. So member lists are read the first time such a node comes up, never on the usual
    path: first those of the moving Groups (a dragged collapsed Group moves its hidden members along),
    then, for a node none of them lists, those of the scope's collapsed Groups, the only Groups that hide
    their members.
    """

    def __init__(
        self,
        payload_for: Callable[[str], object],
        moving_ids: Iterable[str],
        backdrop_payloads: Iterable[object],
    ) -> None:
        self._payload_for = payload_for
        self._moving_ids = moving_ids
        self._backdrop_payloads = backdrop_payloads
        self._moving_owners: dict[str, str] | None = None
        self._collapsed_owners: dict[str, str] | None = None

    def owner(self, node_id: str) -> str:
        payload = self._payload_for(node_id)
        if isinstance(payload, Mapping):
            return _owner_id(payload)
        if self._moving_owners is None:
            self._moving_owners = _listed_owners(self._payload_for(moving_id) for moving_id in self._moving_ids)
        owner = self._moving_owners.get(node_id)
        if owner is not None:
            return owner
        if self._collapsed_owners is None:
            self._collapsed_owners = _listed_owners(
                backdrop
                for backdrop in self._backdrop_payloads
                if isinstance(backdrop, Mapping) and bool(backdrop.get("collapsed"))
            )
        return self._collapsed_owners.get(node_id, "")

    def ancestors(self, node_ids: Iterable[str]) -> set[str]:
        """Every Group that transitively holds one of ``node_ids``; hand-edited data can form a cycle."""
        reached: set[str] = set()
        for node_id in node_ids:
            walked = {node_id}
            owner = self.owner(node_id)
            while owner and owner not in walked and owner not in reached:
                walked.add(owner)
                reached.add(owner)
                owner = self.owner(owner)
        return reached

    def held_by(self, owner: str, holders: set[str], memo: dict[str, bool]) -> bool:
        """Whether the Group ``owner`` is one of ``holders`` or sits inside one, remembering each Group walked."""
        path: list[str] = []
        held = False
        while owner:
            if owner in holders:
                held = True
                break
            known = memo.get(owner)
            if known is not None:
                held = known
                break
            if owner in path:
                break
            path.append(owner)
            owner = self.owner(owner)
        for group_id in path:
            memo[group_id] = held
        return held


def _moved_union(rects: list[dict[str, Any]], offset: tuple[float, float]) -> tuple[float, float, float, float] | None:
    """``(left, top, right, bottom)`` around compact rects moved by ``offset``, or None without rects."""
    if not rects:
        return None
    offset_x, offset_y = offset
    return (
        min(rect["x"] for rect in rects) + offset_x,
        min(rect["y"] for rect in rects) + offset_y,
        max(rect["x"] + rect["width"] for rect in rects) + offset_x,
        max(rect["y"] + rect["height"] for rect in rects) + offset_y,
    )


def _relevance_keys(
    candidates: list[dict[str, Any]], union: tuple[float, float, float, float]
) -> Iterator[tuple[int, float, int]]:
    """``(tier, squared distance, position)`` per candidate, smallest most relevant.

    Tier 0 holds the candidates in the moving rect's row band (they overlap it vertically) or column band
    (they overlap it horizontally): the ones equal spacing measures and the nearest alignments. There the
    distance is the gap along the other axis, since the overlapping axis has none. Tier 1 holds every
    other candidate, by rect-to-rect distance. The position breaks ties in input order.
    """
    left, top, right, bottom = union
    for position, rect in enumerate(candidates):
        rect_left = rect["x"]
        rect_top = rect["y"]
        rect_right = rect_left + rect["width"]
        rect_bottom = rect_top + rect["height"]
        gap_x = max(0.0, rect_left - right, left - rect_right)
        gap_y = max(0.0, rect_top - bottom, top - rect_bottom)
        in_band = (rect_top < bottom and rect_bottom > top) or (rect_left < right and rect_right > left)
        yield (0 if in_band else 1, gap_x * gap_x + gap_y * gap_y, position)


def _axis_gaps(rect: dict[str, Any], union: tuple[float, float, float, float]) -> tuple[float, float]:
    """``(x gap, y gap)`` from a compact rect to ``union`` along each axis, 0 where they overlap or touch."""
    left, top, right, bottom = union
    rect_left = rect["x"]
    rect_top = rect["y"]
    return (
        max(0.0, rect_left - right, left - (rect_left + rect["width"])),
        max(0.0, rect_top - bottom, top - (rect_top + rect["height"])),
    )


def _most_relevant(
    candidates: list[dict[str, Any]],
    moving: list[dict[str, Any]],
    offset: tuple[float, float],
    limit: int,
) -> tuple[list[dict[str, Any]], float, float]:
    """The ``limit`` candidates most relevant to the moving rects moved by ``offset``, in input order, and
    the smallest x gap and y gap from that union to a candidate left out.

    O(n log limit): one bounded heap over the candidates, then a sort of the ``limit`` kept positions and
    one pass over the rest for the gaps. Without a moving rect there is nothing to rank around, so the
    first ``limit`` stay, and both gaps are 0: any of the others may matter.
    """
    union = _moved_union(moving, offset)
    if union is None:
        return candidates[:limit], 0.0, 0.0
    kept = heapq.nsmallest(limit, _relevance_keys(candidates, union))
    positions = sorted(key[2] for key in kept)
    kept_positions = set(positions)
    drop_gap_x = drop_gap_y = math.inf
    for position, rect in enumerate(candidates):
        if position in kept_positions:
            continue
        gap_x, gap_y = _axis_gaps(rect, union)
        drop_gap_x = min(drop_gap_x, gap_x)
        drop_gap_y = min(drop_gap_y, gap_y)
    return [candidates[position] for position in positions], drop_gap_x, drop_gap_y


def build_smart_guide_snapshot(
    node_ids: Iterable[object],
    *,
    payload_for: Callable[[str], object],
    candidate_payloads: Iterable[object],
    backdrop_payloads: Iterable[object],
    offset: tuple[float, float] = (0.0, 0.0),
    candidate_limit: int | None = SMART_GUIDE_CANDIDATE_LIMIT,
) -> dict[str, Any]:
    """``{"moving": [...], "candidates": [...], "trimmed": bool}`` of compact rects for a smart-guide gesture.

    ``moving`` follows ``node_ids`` and skips ids without a payload (hidden members of a collapsed Group
    have none); its rects stay at their stored positions. ``candidates`` keeps ``candidate_payloads``
    order, deduped by node id. It leaves out the moving nodes, every Group that transitively holds one,
    and every candidate whose owner chain reaches a moving Group. Chains follow ``owner_backdrop_id``
    through ``payload_for``, costing each candidate its depth once per Group. ``backdrop_payloads`` (the
    scope's Group backdrops) are only read when a moving node has no payload and no moving Group lists
    it, and then only the collapsed ones.

    More than ``candidate_limit`` candidates (None: no limit) keep only the most relevant to the moving
    rects' union moved by ``offset`` (the drag's current offset): first those sharing its row or column
    band, nearest along the other axis first, then the others by rect-to-rect distance, ties in input
    order. The kept ones stay in input order. Such a snapshot is ``trimmed`` and also holds ``dropGapX``
    and ``dropGapY``: the smallest gap along x, and along y, from that union to a candidate it left out
    (rect to rect, 0 where they overlap). Equal spacing along x only reads the candidates that overlap
    the moving rect along y, and along y those that overlap it along x, so until the union has moved
    ``dropGapY`` along y, or ``dropGapX`` along x, no left-out candidate can join either.
    """
    if isinstance(node_ids, str):
        node_ids = [node_ids]
    moving_ids = list(dict.fromkeys(node_id for value in node_ids if (node_id := normalize_node_id(value))))
    holders = set(moving_ids)
    chains = _OwnerChains(payload_for, moving_ids, backdrop_payloads)
    excluded = holders | chains.ancestors(moving_ids)
    held: dict[str, bool] = {}
    moving = [rect for node_id in moving_ids if (rect := smart_guide_rect(payload_for(node_id))) is not None]
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for payload in candidate_payloads:
        rect = smart_guide_rect(payload)
        if rect is None or rect["node_id"] in excluded or rect["node_id"] in seen:
            continue
        if chains.held_by(_owner_id(payload), holders, held):
            continue
        seen.add(rect["node_id"])
        candidates.append(rect)
    if candidate_limit is None or len(candidates) <= candidate_limit:
        return {"moving": moving, "candidates": candidates, "trimmed": False}
    kept, drop_gap_x, drop_gap_y = _most_relevant(candidates, moving, offset, max(0, int(candidate_limit)))
    return {"moving": moving, "candidates": kept, "trimmed": True, "dropGapX": drop_gap_x, "dropGapY": drop_gap_y}


__all__ = [
    "SMART_GUIDE_CANDIDATE_LIMIT",
    "build_smart_guide_snapshot",
    "smart_guide_offset",
    "smart_guide_query_rect",
    "smart_guide_rect",
]
