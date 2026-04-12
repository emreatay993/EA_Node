# Plan Template

Use this template for new entries under `PLANS_TO_IMPLEMENT/` when the scope may later be split into work packets.
Keep the plan outcome-oriented, but make the execution breakdown explicit enough that a later packetization pass can lift tasks into `P00`, `P01`, and onward without reslicing the entire document.

This file is meant to be portable. A repo may pair it with a thin local overlay that maps the same plan shape onto that repo's packet docs, ownership rules, branch conventions, and verification defaults. In this repo, that local layer lives in `PLANS_TO_IMPLEMENT/PLAN_REPO_OVERLAY.md`.

## Required Authoring Rules

- Keep the high-level contract sections: `Summary`, `Key Changes`, `Public Interface Changes`, `Execution Tasks`, `Work Packet Conversion Map`, `Test Plan`, and `Assumptions`.
- Add `Execution Tasks` as ordered task slices named `T01`, `T02`, `T03`, and so on.
- Every task must be narrow enough that it can become one work packet or one tightly related adjacent packet pair without reopening unrelated seams.
- Every task must state:
  - goal
  - preconditions or dependencies
  - conservative write scope
  - deliverables
  - verification
  - non-goals
  - packetization notes
- `Work Packet Conversion Map` must name the likely `P00` bootstrap packet and the likely follow-on packet boundaries.
- If a section has no substantive content, keep the section and write `none` instead of omitting it.
- Prefer explicit file or subsystem names over generic phrases such as "UI changes" or "backend work".
- Keep task dependencies forward-only. If two tasks can land independently, say so explicitly in the packetization notes.
- Keep the core format portable. Put repo-specific links, packet index references, branch rules, and local verification defaults in a separate repo overlay instead of baking them into the shared template.

## Template Skeleton

# <Plan Title>

## Summary
- <one-paragraph outcome summary>

## Key Changes
- <major scope slice>
- <major scope slice>

## Public Interface Changes
- `none`, or list the user-facing / API-facing additions and changes

## Execution Tasks

### T01 <Short Task Title>
- Goal: <what this task delivers>
- Preconditions: `none` or prior baseline / required contract
- Conservative write scope: <target files, modules, or subsystems only>
- Deliverables: <artifacts, code paths, docs, tests>
- Verification: <tests, commands, or manual checks>
- Non-goals: <what this task explicitly does not absorb>
- Packetization notes: <likely `P01` boundary, bootstrap dependency, merge/split notes>

### T02 <Short Task Title>
- Goal: <what this task delivers>
- Preconditions: <prior tasks or contracts>
- Conservative write scope: <target files, modules, or subsystems only>
- Deliverables: <artifacts, code paths, docs, tests>
- Verification: <tests, commands, or manual checks>
- Non-goals: <what this task explicitly does not absorb>
- Packetization notes: <likely `P02` boundary, merge/split notes>

## Work Packet Conversion Map
1. `P00 Bootstrap`: manifest, ledger, prompts, index registration, and tracking-only docs if this plan becomes a packet set.
2. `P01 <Packet Title>`: derived primarily from `T01`.
3. `P02 <Packet Title>`: derived primarily from `T02`.
4. Add later packets in task order, or explicitly note why two tasks would merge into one packet.

## Test Plan
- <unit / integration / smoke / manual verification anchors>

## Assumptions
- <confirmed defaults, locked decisions, known constraints>
