# AxonClone — Codex Project Instructions
使用中文回复！
## Product North Star

AxonClone is not a generic chat app and not a passive knowledge browser.
It is a desktop AI learning operating system built around this value loop:

1. content intake
2. knowledge network construction
3. expression practice
4. ability diagnosis
5. summary and asset capture
6. spaced review

Prefer changes that make this loop clearer, faster, safer, and more useful.

## Fixed Stack

- Desktop shell: Tauri v2
- Frontend: React + TypeScript + Vite + Tailwind CSS
- Frontend state: Zustand for UI state, React Query for server state
- Graph UI: React Flow
- Backend: FastAPI + Python 3.12 + Pydantic
- AI: OpenAI Responses API with structured schema output
- Graph store: Neo4j
- Vector store: LanceDB
- Business state: SQLite

Do not replace these technologies unless the user explicitly asks.

## Architecture Rules

- Keep AI generation and business state management separated.
- React Query owns server data; Zustand owns transient UI state.
- Backend responses use `{ success, data, meta, error }`.
- Backend writes follow SQLite -> Neo4j -> LanceDB order.
- AI outputs must be schema-validated before persistence.
- Keep Tutor / Diagnoser / Explorer / Synthesizer responsibilities separated.

## Coding Rules

- Preserve the existing structure, naming, dependencies, and style.
- Prefer the smallest direct change that solves the current problem.
- Do not batch unrelated fixes.
- Do not refactor broadly while addressing a local issue.
- Make assumptions explicit; do not present guesses as facts.

## Validation Rules

- Every code change must be followed by immediate verification.
- Prefer existing tests, type checks, builds, or narrow runtime checks.
- If no automated check exists, run the smallest manual or scripted verification that proves the change.
- Do not claim success without command output or other concrete evidence.

## Safe Grow Workflow

When iterating from audit findings or growth backlog items:

- Use the repository-local skill at `.agents/skills/safe-grow/SKILL.md`.
- Read `.claude/loop/PROJECT_GROWTH.md`, `.claude/loop/GLM_AUDIT.md`, `.claude/loop/GROWTH_BACKLOG.md`, `.claude/loop/state.json`, and `.claude/loop/log.md`.
- Process exactly one item per turn.
- Continue unfinished work before selecting a new item.
- After audit items are complete, continue in growth mode instead of stopping.

## Growth Planning Workflow

When the repository needs a deeper rescan, a better future roadmap, or a reset of growth priorities:

- Use the repository-local skill at `.agents/skills/growth-architect/SKILL.md`.
- Read `.claude/roadmap/PROJECT_FUTURE.md` and the latest roadmap under `docs/plans/`.
- Use `.claude/loop/PROJECT_GROWTH.md`, `.claude/loop/GLM_AUDIT.md`, `.claude/loop/GROWTH_BACKLOG.md`, and `.claude/loop/state.json` as evidence inputs when they exist.
- Optimize only for improvements that help users use the system better or strengthen the product's core learning loop.
- Translate roadmap conclusions into small, safe next items for `safe-grow`, not broad speculative rewrites.

## Anti-Goals

- Do not turn the product into a generic chatbot.
- Do not prioritize cosmetic churn over core learning outcomes.
- Do not introduce multi-user/cloud/enterprise features unless explicitly requested.
- Do not break the main learning loop for the sake of internal cleanliness.
