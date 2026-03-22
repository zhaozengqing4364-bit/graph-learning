---
name: growth-architect
description: Use when you need to deeply analyze the current repository and produce a detailed future development roadmap that prioritizes user value, core capability growth, safer iteration, and compounding improvement
---

# Growth Architect

## Overview

Use this when the project needs a better future arc, not just the next patch.
This skill sits upstream of `safe-grow`: first determine what will make the product materially better for users and stronger at its core job, then hand the result to single-item execution.

Always treat repository evidence as the source of truth.

## Required Reads

Read these first when present:

- `AGENTS.md`
- `CLAUDE.md`
- `.claude/roadmap/PROJECT_FUTURE.md`
- `.claude/loop/PROJECT_GROWTH.md`
- `.claude/loop/GLM_AUDIT.md`
- `.claude/loop/GROWTH_BACKLOG.md`
- `.claude/loop/state.json`
- `task_plan.md`
- `findings.md`
- `progress.md`
- the latest relevant files under `docs/audits/` and `docs/plans/`

Then scan the real product surface:

- `src/`
- `backend/`
- `src-tauri/`
- `scripts/`
- tests and critical docs

## When to Re-Plan

Use this skill when one or more are true:

- the current backlog is thin, stale, or low-signal
- audit items are mostly done and the project needs a stronger next arc
- the team can ship fixes but lacks a coherent future sequence
- users can technically use the product, but the main loop still feels fragmented, confusing, or weak
- new work should be selected by compounding product leverage, not by convenience

## Analysis Lenses

Evaluate the repo through these lenses:

1. User journey friction
   - Where do users hesitate, branch incorrectly, or lose confidence?
   - Which steps in the main loop are ambiguous, blank, slow, or unreliable?

2. Core capability strength
   - Does the system actually perform its core job end to end?
   - Which product promises exist in docs or UI but are not truly wired through?

3. Reliability and recovery
   - Where can writes partially fail, state drift, or recovery become manual?
   - Where is observability too weak to support safe iteration?

4. Learning quality and feedback quality
   - Are practice, diagnosis, summary, and review outputs useful enough to change learner behavior?
   - Are signals reused across later steps, or do they disappear after one screen?

5. Iteration leverage
   - Which changes create future speed through tests, contracts, visibility, or safer boundaries?
   - Which missing validations keep endangering high-value paths?

6. Architecture drag
   - Which structural gaps slow the main loop today?
   - Ignore neatness-only refactors that do not improve user outcomes or core capability.

## Growth Scoring

Score each candidate from 1-5 on:

- user leverage
- core-capability leverage
- evidence strength
- compounding value
- validation ease

Score blast radius from 1-5, where 5 is highest risk.

Prefer candidates with:

`user leverage + core-capability leverage + evidence strength + compounding value + validation ease - blast radius`

Do not promote candidates that are mostly cosmetic, speculative, or disconnected from the main value loop.

## Roadmap Rules

Every roadmap item must include:

- the user problem
- the desired user outcome
- the system-capability outcome
- evidence from code, docs, tests, or observed gaps
- exact likely files or modules
- the smallest credible slice
- dependencies
- a validation plan
- a success signal
- reasons not to do a broader refactor right now

## Output

Write the roadmap to:

- `docs/plans/YYYY-MM-DD-<project-name>-growth-roadmap.md`

The roadmap should contain:

- current system understanding
- strengths worth preserving
- top bottlenecks ordered by leverage
- 3 horizons or phases with concrete items
- immediate next 3-5 `safe-grow` candidates
- validation strategy for the roadmap itself
- explicit anti-goals and what not to do now

## Handoff to Safe Grow

Before finishing:

1. Name the next highest-leverage item that can be done safely in one turn.
2. If useful, add or refresh candidate entries in `.claude/loop/GROWTH_BACKLOG.md`.
3. Make sure the roadmap makes future single-item iteration easier, not harder.

## Hard Bans

- no roadmap that is just a folder summary
- no feature list without evidence or prioritization logic
- no platform rewrite as the default answer
- no optimizing for aesthetics over user success in the core loop
- no roadmap item that cannot explain why it helps users or strengthens the main system
