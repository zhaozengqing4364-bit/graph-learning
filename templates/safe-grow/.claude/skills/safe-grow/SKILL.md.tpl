---
name: safe-grow
description: Use when iterating from an audit, backlog, or review where each turn must handle one issue safely, preserve existing behavior and structure, and bias improvements toward better user outcomes and stronger core product capabilities
---

# Safe Grow

## Overview

Use single-issue, validated iteration. Improve `{{PROJECT_NAME}}` in ways that compound: easier to use, more reliable, easier to diagnose, and stronger at the project's main job.

The project-specific north star lives in `.claude/loop/PROJECT_GROWTH.md`. Read it before selecting work.

## Modes

### Stabilize
- Source of truth: `.claude/loop/GLM_AUDIT.md`
- Goal: close correctness, reliability, safety, and test gaps without destabilizing working flows

### Grow
- Source of truth: `.claude/loop/GROWTH_BACKLOG.md`
- Goal: keep improving the product after major fixes are done
- Constraint: improvements must still be single-issue, low-blast-radius, and verified immediately

## When to Use

Use this skill when:
- an auditor or reviewer has produced an issue list
- many possible optimizations exist and focus is needed
- code is already running and must not be destabilized
- the next step should improve user outcomes, not just code aesthetics

Do not use this skill for broad redesigns, speculative refactors, or open-ended brainstorming without a concrete issue list.

## Decision Gates

Before picking or keeping an issue, ask:
1. Does this help users complete a core task faster, more clearly, or with fewer failures?
2. Does this strengthen a core system capability instead of only polishing internals?
3. Does this improve future iteration safety through tests, contracts, logging, observability, or recovery?

If all three answers are no, defer the issue.

## Growth Scan

When `Stabilize` work is exhausted, do not stop. Build or refresh `Grow` candidates from evidence.

Prefer candidates from these sources:
- repeated friction in the main user journey
- unclear UI or weak feedback in core flows
- slow or fragile paths in the primary workflow
- missing diagnostics, schema guards, or recovery paths
- missing tests around high-value behavior
- repeated manual steps that should become smoother or safer

Each growth candidate must include:
- one-sentence user outcome
- one-sentence system-capability outcome
- concrete evidence or rationale
- smallest safe change
- explicit validation plan
- success signal

## Single-Issue Loop

1. Read `CLAUDE.md`, `.claude/loop/PROJECT_GROWTH.md`, `.claude/loop/GLM_AUDIT.md`, `.claude/loop/GROWTH_BACKLOG.md`, `.claude/loop/state.json`, and `.claude/loop/log.md`.
2. Continue any unfinished or failed issue before selecting a new one.
3. If audit items remain, stay in `Stabilize`.
4. If audit items are done, switch to `Grow`.
5. In the active mode, select exactly one highest-value unresolved item.
6. Define touched files, untouched areas, rollback point, validation plan, and success signal.
7. When practical, add or update the smallest failing test or check first.
8. Make the minimum code change required.
9. Verify immediately.
10. Update state and log before moving on.

## Hard Bans

- No multi-issue batches
- No architecture rewrites unless the issue explicitly requires it
- No dependency churn without a clear need
- No "while I'm here" cleanup
- No unverifiable completion claims
- No changes that drift from project style, structure, or product direction

## Output Contract

Every iteration should report:
- current issue and why it matters
- active mode: `Stabilize` or `Grow`
- exact files and code areas touched
- validation commands and results
- user-facing benefit
- system-capability benefit
- success signal status
- rollback note
