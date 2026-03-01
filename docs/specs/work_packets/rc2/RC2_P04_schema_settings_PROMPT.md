Implement `RC2_P04_schema_settings.md`.

Constraints:
- Existing `.sfe` documents from schema v1 must load without manual user actions.
- New metadata keys must be normalized and deterministic in serializer output.
- Keep existing save/load/session behavior intact.

Deliverables:
1. Schema version bump + migration path.
2. Workflow settings modal and `open_workflow_settings()` API.
3. Tests for migration and modal persistence.
4. `settings_modal.png` artifact path.

