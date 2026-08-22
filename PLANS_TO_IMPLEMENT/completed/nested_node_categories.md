## Nested Node Categories (10-Level)

### Summary
- Feasible with a moderate refactor. This is mainly a spec/library/UI/test migration, not a project-file migration.
- Adopt a **path-only** category model with a maximum depth of 10.
- Parent category filtering is **descendant-inclusive**: selecting a parent returns everything below it.
- Keep the current library-pane architecture: a flat `ListView` fed by a pre-flattened tree model. Do not introduce `TreeView`.
- Ship one real nested family in the product catalog now: **Ansys DPF**. Leave the rest of the catalog effectively flat in this pass.

### Key Changes
- Replace `NodeTypeSpec.category: str` with `category_path: tuple[str, ...]`.
- Change `node_type(...)` authoring from `category=` to `category_path=`.
- Add category helpers and make them the single source of truth:
  - `category_display(path)` joins with ` > `
  - `category_key(path)` returns a stable string key from normalized segments
  - `category_matches(selected_path, candidate_path)` uses prefix matching
- Validate category paths as:
  - 1 to 10 segments
  - each segment is a non-empty trimmed string
  - existing labels like `Input / Output` remain a **single segment**
- Migrate all built-in node declarations to tuple paths.
- Migrate Ansys DPF nodes to nested paths:
  - compute nodes: `["Ansys DPF", "Compute", ...]`
  - viewer nodes: `["Ansys DPF", "Viewer", ...]`
- Keep most other built-in families as one-segment paths for now.
- Update the registry and library pipeline to operate on paths, not flat strings.
- Library item payloads should expose:
  - `category_path`
  - `category_key`
  - `category_display`
  - `root_category`
  - keep a derived read-only `category` text field equal to `category_display` for existing read-only consumers
- Rebuild grouped library rows from a category trie:
  - synthesize missing intermediate folders
  - flatten preorder
  - sort segment-by-segment
  - render category rows before direct node rows
- Add row metadata for QML:
  - `depth`
  - `ancestor_category_keys`
  - `category_key`
  - `label` as the final segment for category rows
- Keep `NodeLibraryPane` on `ListView`; use indentation and ancestor-collapse checks instead of a new tree widget.
- Collapse state must be keyed by `category_key`, not label text.
- Default all categories to collapsed on pane reset / project install, including nested ones.
- Use the **root segment** for graph-theme accent resolution so nested categories keep their current color family.
- Keep custom workflows at `["Custom Workflows"]` in this pass.
- Update README / plugin-author examples to the new `category_path` API.

### Test Plan
- Spec validation:
  - accepts 1-level and 10-level paths
  - rejects empty, whitespace-only, and 11-level paths
- Registry behavior:
  - parent path returns descendants
  - leaf path returns only that leaf bucket
  - stable sorting across mixed-depth categories
  - text search matches full displayed path text
- Library tree payload:
  - intermediate categories are synthesized
  - depth and ancestor keys are correct
  - duplicate leaf names under different parents do not collide
  - categories sort before nodes
- QML pane:
  - all category rows start collapsed
  - expanding a parent does not auto-expand children
  - descendants stay hidden until all ancestors are expanded
  - click/drag insert still works from node rows
- Adjacent surfaces:
  - quick insert shows full path text
  - inspector metadata shows full path text
  - theme accent follows root category
- Update current flat-category tests, especially DPF and library grouping assertions.

### Assumptions and Risks
- This is a **breaking authoring change** for node specs and external plugins because `category` becomes `category_path`.
- No saved-project serializer migration is expected because category data is not persisted on node instances.
- Full-path display uses ` > ` specifically to avoid ambiguity with existing labels like `Input / Output`.
- This change adds hierarchy support and one shipped nested family; a broader catalog re-taxonomy is out of scope for this pass.
