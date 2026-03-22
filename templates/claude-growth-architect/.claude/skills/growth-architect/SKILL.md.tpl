---
name: growth-architect
description: Use when the repository needs a deep rescan and a detailed future roadmap that prioritizes user value, stronger core capability, safer iteration, and compounding improvement
---

# Growth Architect

## Overview

Use this skill before pushing more implementation when the project needs a better future arc.
It sits upstream of `/safe-grow`: first determine what will make the product materially better for users and stronger at its core job, then convert that into small safe next steps.

Always treat repository evidence as the source of truth.

## Required Reads

Read these first when present:

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

## Growth Scoring

Score each roadmap candidate from 1-5 on:

- user leverage
- core-capability leverage
- evidence strength
- compounding value
- validation ease

Score blast radius from 1-5, where 5 is highest risk.

Prefer candidates with:

`user leverage + core-capability leverage + evidence strength + compounding value + validation ease - blast radius`

## Output Contract

Write or update:

- `docs/plans/YYYY-MM-DD-<project-name>-growth-roadmap.md`

The roadmap must include:

- current system understanding
- strengths worth preserving
- top bottlenecks ordered by leverage
- phased roadmap items with evidence
- immediate next 3-5 `/safe-grow` candidates
- anti-goals and what not to do now
