# Plan Template

Use the smallest plan shape that makes the work clear. Ordinary fixes should not inherit task and packet ceremony intended for larger changes.

This file is portable. Repository-specific ownership and verification rules belong in `PLANS_TO_IMPLEMENT/PLAN_REPO_OVERLAY.md`.

## Required Authoring Rules

- Use the focused-change shape for one behavior seam with one primary source owner and one primary regression owner, unless the work changes a public interface or schema.
- Use the expanded task shape when work crosses stable owners, has ordered dependencies, changes an API/schema or migration, needs separate performance acceptance, or contains independently landable slices.
- Every verification command must appear exactly once and say when it runs: during implementation, after the related task group, or at conditional closeout.
- Start with the smallest changed or new test module, class, or node ID. Add one route-owned suite after the last related task only when it proves adjacent behavior.
- The expanded `Test Plan` lists only checks not already named by a task; it must not repeat task commands.
- Add a `Work Packet Conversion Map` only when the user explicitly requests packetization. A normal plan has no `P00`.
- Prefer exact files, modules, or subsystems over generic labels such as "UI changes" or "backend work".
- Keep the core format portable. Put repo-specific commands, ownership rules, and escalation thresholds in the repo overlay.

## Focused Change Skeleton

# <Plan Title>

## Summary
- <outcome and success condition>

## Change
- <exact behavior and conservative write scope>
- <important non-goals, if any>

## Verification
- During implementation: `<smallest affected test module, class, or node ID>`
- After the related task group: `<one owning route suite, or none>`
- Conditional closeout: `<broader integration check and its trigger, or none>`

## Assumptions
- <confirmed defaults and constraints>

## Expanded Task Skeleton

# <Plan Title>

## Summary
- <outcome and success condition>

## Key Changes
- <major scope slice>
- <major scope slice>

## Public Interface Changes
- `none`, or list the user-facing or API-facing changes

## Execution Tasks

### T01 <Short Task Title>
- Goal: <what this task delivers>
- Preconditions: `none` or required prior contract
- Conservative write scope: <target files, modules, or subsystems only>
- Deliverables: <behavior, code paths, docs, and tests>
- Verification: <one exact command and whether it runs now or after a named task group>
- Non-goals: <what this task does not absorb>

### T02 <Short Task Title>
- Goal: <what this task delivers>
- Preconditions: <prior tasks or contracts>
- Conservative write scope: <target files, modules, or subsystems only>
- Deliverables: <behavior, code paths, docs, and tests>
- Verification: <one exact command and whether it runs now or after a named task group>
- Non-goals: <what this task does not absorb>

## Test Plan
- <only additional group-level or conditional closeout checks; write `none beyond task checks` when there are none>

## Assumptions
- <confirmed defaults and constraints>

## Work Packet Conversion Map (only when explicitly requested)

Insert this section before `Test Plan` only for an explicitly requested packet set:

1. `P00 Bootstrap`: packet tracking and setup only.
2. `P01 <Packet Title>`: derived from the first execution slice.
3. Add later packets only where ownership, dependency, or verification boundaries require them.
