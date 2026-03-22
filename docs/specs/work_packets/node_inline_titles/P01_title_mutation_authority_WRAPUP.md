# P01 Title Mutation Authority Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/node-inline-titles/p01-title-mutation-authority`
- Commit Owner: `worker`
- Commit SHA: `79f21e0093adb91ec97552da82391b7add85376f`
- Changed Files: `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `tests/test_inspector_reflection.py`, `tests/graph_track_b/scene_and_model.py`, `docs/specs/work_packets/node_inline_titles/P01_title_mutation_authority_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/node_inline_titles/P01_title_mutation_authority_WRAPUP.md`, `tests/test_inspector_reflection.py`, `tests/graph_track_b/scene_and_model.py`

`GraphSceneMutationHistory` is now the packet-owned title authority seam for inline title commits. `set_node_property(node_id, "title", value)` intercepts title writes before registry property normalization and routes them through `_normalized_title_update(...)` plus `_apply_title_update(...)`, which reuse the existing `set_node_title(...)` normalization, empty-title rejection, mutation-boundary rename, and passive-family title synchronization rules.

`set_node_properties(node_id, values)` now treats `"title"` as a title mutation instead of a registry-backed property requirement. Title-only batches record `ACTION_RENAME_NODE`, while mixed property batches keep `ACTION_EDIT_PROPERTY` and still apply the title through the same helper. Passive flowchart/planning/annotation families continue to synchronize both `node.title` and `properties["title"]`; standard executable nodes and subnode shells keep `node.title` canonical without introducing a synthetic `properties["title"]` entry.

Focused regressions now cover standard-node single and batched title commits, passive-family batch synchronization, subnode shell batch title updates, whitespace rejection, and rename-vs-property history classification.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest tests/test_inspector_reflection.py --ignore=venv -k "title" -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/graph_track_b/scene_and_model.py --ignore=venv -k "title or titles_synced" -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Too soon for manual testing.

- Blocker: `P01` only changes the mutation-layer authority; the shared header rollout that exposes non-flowchart inline title editing on the live canvas is deferred to `P02`.
- Blocker: there is no new packet-owned desktop gesture in this branch that exercises the standard-node or subnode-shell title path directly.
- Next condition: once `P02` lands, manually edit a standard node title and a subnode shell title from the shared header and confirm the canvas title updates without creating a synthetic `properties["title"]`, while passive families still keep both title stores synchronized.

## Residual Risks

- `P01` intentionally leaves the shared header gating unchanged, so standard/media/subnode inline title editing is still not user-exposed until later packets land.
- Verification is focused on mutation-layer regressions; no broader desktop smoke run was performed on this packet branch.

## Ready for Integration

- Yes: the mutation layer now owns title normalization and synchronization for both direct and property-routed title edits, the packet stayed inside its assigned scope, and the required verification commands passed.
