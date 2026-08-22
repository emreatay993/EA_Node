# Reusable Rich Text Blocks Plan

## Summary

Create a planning baseline for reusing the current text annotation Markdown/style capability across prose-oriented graph surfaces.

Use a replace-in-place strategy: promote the existing text annotation style/render/edit path into the canonical shared rich-text path, and remove duplicated logic from adopters as they migrate. Do not create parallel workflows, duplicate style schemas, second commit paths, or temporary adapter classes.

## Key Changes

- Treat `passive.annotation.text` as the seed implementation, not a separate special case.
- Keep the existing node-property commit flow, scene payload projection, and `.cxproj` persistence path.
- Centralize text-style defaults and normalization through the existing `ea_node_editor/text_style.py` authority.
- Extract reusable QML rendering/editing behavior from `GraphBareTextSurface.qml` only by moving logic into one canonical shared component path; leave no duplicated markdown/style toolbar implementation behind.
- Adopt rich text only for user-authored prose fields first: annotation note body/subtitle, planning card body, then flowchart body/cube text. Groups remain title-only and are not adopters.
- Keep labels, titles, chips, metadata, ports, execution text, and compact graph chrome plain unless a later plan explicitly expands scope.

## Execution Tasks

- `T01 Stabilize Current Contract`: confirm `center` remains the canonical bare text alignment default and keep source, QML, docs, and tests aligned.
- `T02 Promote Current Renderer`: move the existing markdown/plain rendering, style mapping, source editor, and toolbar behavior into the single canonical reusable rich-text implementation; do not leave a duplicate copy in `GraphBareTextSurface.qml`.
- `T03 Define Rich Text Slot Contract`: add one shared slot convention for existing fields such as `text`, `body`, `subtitle`, `body_top`, and `body_right`, using explicit `plain` or `markdown` format fields and existing node-property commits.
- `T04 Adopt Annotation Notes`: migrate sticky note, callout, and section-header prose fields to the canonical renderer/editor; titles stay plain.
- `T05 Adopt Planning Cards`: migrate planning card body only; status chips and metadata stay plain.
- `T06 Adopt Flowchart Text`: migrate normal flowchart body first, then cube-face body fields; timestamp/live text stays plain unless separately redesigned.
- `T07 Closeout`: update affected agent maps, specs/index links if needed, and verification evidence.

## Work Packet Conversion Map

- `P00 Bootstrap`: preserve this plan as the source baseline and register any future packet set under `docs/specs/work_packets/` if packetization is requested.
- `P01 Current Contract + Shared Owner`: cover `T01` and `T02`.
- `P02 Slot Contract + Node Specs`: cover `T03`.
- `P03 Annotation + Planning Adoption`: cover `T04` and `T05`.
- `P04 Flowchart Adoption`: cover `T06`.
- `P05 Verification Closeout`: cover `T07`.

## Public Interface Changes

- Add one canonical reusable rich-text field contract for graph prose surfaces.
- Existing documents must default old prose fields to `plain`, not `markdown`, to avoid changing literal `#`, `*`, `_`, and URL text.
- New rich-text-first annotation text may continue defaulting to `markdown`.
- No new persistence workflow, no second graph mutation bridge, no separate markdown save path, and no compatibility shim for duplicate old/new rich-text implementations.

## Test Plan

- Add or update normalization tests for the shared style defaults and per-field slot defaults.
- Add serializer round-trip coverage for new prose format/style fields.
- Add scene payload tests proving rich-text-capable fields project through the existing property payload.
- Add QML surface tests for markdown preview, plain source editing, toolbar commits, and format toggling.
- Add focused adopter tests for annotation notes, planning card body, and flowchart body.
- Run focused graph surface checks first, then `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`.

## Assumptions

- Target save path is `PLANS_TO_IMPLEMENT/in_progress/reusable_rich_text_blocks.md`.
- "No parallel workflows/classes/methods" means replace-in-place: new shared code is allowed only when it becomes the single canonical owner and old duplicate logic is removed.
- This plan is the source baseline for a later packetization or implementation pass; it does not itself implement reusable rich text behavior.
