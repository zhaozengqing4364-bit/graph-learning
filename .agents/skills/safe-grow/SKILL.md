---
name: safe-grow
description: Use when iterating from an audit, backlog, or review where each turn must handle exactly one issue safely, preserve existing behavior and structure, and keep pushing the product toward stronger user outcomes and core capability growth
---

# Safe Grow

## Overview

This is the Codex-native equivalent of a safe Claude `/loop` workflow.
Use it for single-issue, validated iteration driven by repository state files instead of long-lived chat memory.

Always treat `.claude/loop/state.json` as the source of truth.

## Required Reads

Read these before picking work:

- `AGENTS.md`
- `.claude/loop/PROJECT_GROWTH.md`
- `.claude/loop/GLM_AUDIT.md`
- `.claude/loop/GROWTH_BACKLOG.md`
- `.claude/loop/state.json`
- `.claude/loop/log.md`

Read `CLAUDE.md` too when it exists, because some projects keep deeper architecture detail there.

## Modes

### Stabilize

- Source of truth: `.claude/loop/GLM_AUDIT.md`
- Goal: close correctness, reliability, safety, and test gaps without destabilizing working flows

### Grow

- Source of truth: `.claude/loop/GROWTH_BACKLOG.md`
- Goal: keep improving the product after major fixes are done
- Constraint: improvements must remain low-blast-radius, one item at a time, and immediately verified

## Decision Gates

Before picking or keeping an item, ask:

1. Does this help users complete a core task faster, more clearly, or with fewer failures?
2. Does this strengthen a core system capability instead of only polishing internals?
3. Does this improve future iteration safety through tests, contracts, observability, or recovery?

If all three answers are no, defer the item.

## Growth Scan

When `Stabilize` work is exhausted, do not stop. Refresh growth candidates from evidence.

Prefer candidates from these sources:

- repeated friction in the main user journey
- unclear UI or weak feedback in core flows
- slow or fragile paths in the primary workflow
- missing diagnostics, schema guards, or recovery paths
- missing tests around high-value behavior
- repeated manual steps that should become safer or smoother

Each growth candidate must include:

- one-sentence user outcome
- one-sentence system-capability outcome
- concrete evidence or rationale
- smallest safe change
- explicit validation plan
- success signal

## Single-Issue Loop

1. Continue unfinished or failed work before selecting anything new.
2. If audit items remain, stay in `Stabilize`.
3. If audit items are done, switch to `Grow`.
4. In the active mode, select exactly one highest-value unresolved item.
5. Define touched files, untouched areas, rollback point, validation plan, and success signal.
6. When practical, add or update the smallest failing test or check first.
7. Make the minimum code change required.
8. Verify immediately.
9. Update `.claude/loop/state.json` and `.claude/loop/log.md`.
10. Stop after one item, even if time remains.

## For `codex exec`

When invoked from automation:

- do not depend on chat history
- reconstruct context from files every run
- keep changes atomic
- leave the repository in a state that the next fresh run can resume safely
- return a concise structured summary when the caller provides an output schema

## Hard Bans

- No multi-issue batches
- No broad refactors unless the current item explicitly requires it
- No dependency churn without a clear need
- No "while I'm here" cleanup
- No unverifiable completion claims
- No changes that drift from project style, structure, or product direction

## Output Contract

Every iteration should report:

- current item and why it matters
- active mode: `stabilize` or `grow`
- exact files and code areas touched
- validation commands and results
- user-facing benefit
- system-capability benefit
- success signal status
- rollback note
