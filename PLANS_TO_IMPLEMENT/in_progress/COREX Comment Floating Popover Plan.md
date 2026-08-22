# COREX Comment Floating Popover Plan

## Summary

Retain the floating comment-popover concept, but retire its former Group-body integration. No implementation packet is currently valid.

## Change

- `Group` is `passive.annotation.group_backdrop`, has no body/rich-text content or Inspector-editable properties, and is not a node-comment store.
- A future floating comment popover requires independent durable comment storage and a non-Group anchor contract before implementation can be planned.
- `Peek Inside` remains the separate Group-focused view.

## Verification

- Keep this plan document-only until an independent comment-storage contract exists.
- When revived, add focused persistence, graph-action, QML popover, and Markdown/traceability checks for that separate comment feature.

## Assumptions

- The floating comment-popover concept remains unimplemented.
- Group title, membership, collapse, and Peek behavior stay outside this plan.
