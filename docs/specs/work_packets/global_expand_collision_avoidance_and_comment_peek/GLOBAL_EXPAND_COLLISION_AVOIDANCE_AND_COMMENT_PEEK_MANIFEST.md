# GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK Work Packet Manifest

- Date: `2026-04-13`
- Integration base: `main`
- Published packet window: `P00` through `P03`
- Scope baseline: convert the global expand collision-avoidance and comment-peek plan into an execution-ready packet set that adds an app-wide persistent expand-time collision solver for collapsed items, keeps the expanded item fixed while nearby eligible objects move, leaves post-expand layout in place after re-collapse, and ships a collapsed-comment `Peek Inside` mode without reusing subnode scope-path architecture.
- Review baseline: [PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md](../../../../PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_bootstrap.md`
2. `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P01_preferences_and_graphics_settings.md`
3. `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P02_expand_collision_avoidance.md`
4. `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P03_comment_peek_mode.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/global-expand-collision-avoidance-and-comment-peek/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, source-of-truth linkage, and git tracking for the new packet set |
| P01 Preferences and Graphics Settings | `codex/global-expand-collision-avoidance-and-comment-peek/p01-preferences-and-graphics-settings` | Add the persistent preference schema, runtime application path, and Graphics Settings controls without changing collapse behavior yet |
| P02 Expand Collision Avoidance | `codex/global-expand-collision-avoidance-and-comment-peek/p02-expand-collision-avoidance` | Add the expand-time collision solver, grouped history wiring, and comment-backdrop occupied-bounds handling on top of the new settings surface |
| P03 Comment Peek Mode | `codex/global-expand-collision-avoidance-and-comment-peek/p03-comment-peek-mode` | Add the collapsed-comment `Peek Inside` entrypoint, transient peek state, and membership-filtered editable focused view |

## Locked Defaults

- `graphics.interaction.expand_collision_avoidance` is an app-wide persistent preference surface, not project data.
- Missing values for new users and upgraders normalize to enabled collision avoidance with `nearest` strategy, `all_movable` scope, `local` reach, `medium` local-radius preset, `normal` gap preset, and animation enabled.
- Collision avoidance runs only on `collapsed -> expanded` transitions. It does not run during drag, and it does not attempt restore-on-collapse behavior.
- The expanded item stays fixed. The solver moves nearby eligible objects and commits expand plus translation as one undoable history action.
- V1 has no lock, pin, or frozen-object exemptions because the repo has no existing persistent object immovability concept.
- Comment `Peek Inside` is a temporary comment-only mode, not reuse of subnode scope-path navigation.
- Comment peek shows direct current members only, remains fully editable, and exits by explicit control plus click-away dismissal.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- When a later packet changes an earlier packet's asserted seam, the later packet inherits and updates that earlier regression anchor inside its own write scope.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md`
- Spec contract: `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_bootstrap.md` through `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P03_comment_peek_mode.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P03`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P03_comment_peek_mode_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_QA_MATRIX.md`
- Status ledger: [GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md](./GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md)

## Standard Thread Prompt Shell

`Implement GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_PXX_<name>.md exactly. Before editing, read GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md, GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md, and GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
