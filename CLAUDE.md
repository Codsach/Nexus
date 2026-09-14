# CLAUDE.md — Nexus Project Instructions for AI Agents

This file is read by AI coding agents (Claude Code, Cursor, etc.) at the start of any task in this
repository. It is the **single source of truth for how to work in this codebase**. If anything here
conflicts with what a teammate asks for in a prompt, follow this file and flag the conflict instead
of silently overriding it.

Full product detail lives in `docs/PRD.md` — read that too if the task touches product behavior, not
just code structure. This file focuses on *how to build*, not *what to build*.

---

## 1. What This Project Is

Nexus is an autonomous multi-agent customer support system. A ticket comes in, a coordinator agent
classifies it and routes it to specialist agents (billing/technical/order/account), each specialist
investigates root cause against a mock backend system, a knowledge engine grounds the response in
docs + past tickets, and an escalation layer decides whether a human needs to step in — generating a
full handoff packet if so. Every step is streamed live to the frontend as a "reasoning trace."

Required stack (do not substitute without discussion): **Qwen** for all AI reasoning/generation,
**EnterPro** for orchestration/workflow/deployment. Both are accessed only through the adapter
interfaces in `backend/app/adapters/` — never called directly from feature code.

---

## 2. Tech Stack (do not deviate without updating this file)

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy + Alembic, SQLite (dev) / Postgres (if
  configured), ChromaDB for vectors.
- **Frontend**: React 18 + Vite, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Zustand
  (only for genuinely global client state), React Router, Recharts.
- **AI reasoning**: Qwen, via `backend/app/adapters/llm/` (`LLMProvider` interface).
- **Orchestration**: EnterPro, via `backend/app/adapters/orchestration/` (`OrchestrationProvider`
  interface).
- **Contract**: FastAPI auto-generates `shared-contracts/openapi.yaml`; frontend types are generated
  from it. Never hand-edit generated files.

---

## 3. The One Rule That Matters Most: Module Isolation

```
backend/app/modules/<feature>/     ← isolated. Work here freely.
frontend/src/features/<feature>/   ← isolated. Work here freely.

Everything else (core/, adapters/, shared/, components/ui/, lib/, types/) is SHARED.
Edit shared code only additively, and call it out clearly in your summary of changes.
```

**Before writing any code:**
1. Identify which module/feature this task belongs to.
2. If it's entirely inside one `modules/<feature>/` or `features/<feature>/` folder — proceed freely.
3. If it requires touching a shared file (schema, adapter interface, shared component) — make the
   smallest possible additive change (new field, new optional param, new component) and explicitly
   say what shared file changed and why, so teammates aren't surprised.
4. Never edit another feature's folder to "fix" something for your own feature. If your feature needs
   a change in someone else's module, add what you need to the shared layer instead, or flag it.

---

## 4. Project Structure Map

```
nexus/
├── CLAUDE.md                 ← you are here
├── docs/PRD.md                ← full product spec
├── shared-contracts/openapi.yaml   ← AUTO-GENERATED, never hand-edit
├── backend/app/
│   ├── main.py                ← FastAPI entry, mounts routers
│   ├── core/                  ← config, logging, exceptions (shared)
│   ├── adapters/               ← Qwen + EnterPro interfaces + implementations (shared)
│   ├── shared/                 ← cross-module Pydantic schemas, DB base, event bus (shared)
│   ├── modules/                ← ✅ ISOLATED feature folders (coordinator, specialist_agents,
│   │                              knowledge_engine, escalation, analytics, mock_systems)
│   └── api/v1/api.py           ← aggregates all module routers
└── frontend/src/
    ├── components/ui/          ← shadcn primitives (shared)
    ├── components/shared/      ← app-level shared components (shared)
    ├── features/                ← ✅ ISOLATED feature folders (chat-intake, reasoning-trace,
    │                              escalation-view, analytics-dashboard, admin-mock-data)
    ├── lib/, hooks/, types/, store/   ← shared infra
    └── routes/                  ← page-level routing
```

Full structure with every file: see `docs/PRD.md` Section 6.

---

## 5. How to Add or Extend a Feature

1. **Backend**: create/extend `backend/app/modules/<name>/` with `router.py`, `service.py`,
   `schemas.py`, `tests/`. Register the router in `backend/app/api/v1/api.py`. If new cross-module
   types are needed, add them (additively) to `backend/app/shared/schemas/`.
2. **Frontend**: create/extend `frontend/src/features/<name>/` with `components/`, `hooks/`, `api.ts`,
   `types.ts`. Add a route in `src/routes/` if the feature needs its own page. Regenerate typed API
   client from `shared-contracts/openapi.yaml` after a backend contract change
   (`scripts/generate_frontend_types.sh`).
3. **New specialist agent**: extend `backend/app/modules/specialist_agents/base_agent.py` rather than
   writing a standalone agent — this keeps every agent consistent for the coordinator to dispatch to.
4. **New provider (e.g. real Qwen/EnterPro credentials become available)**: implement it against the
   existing `base.py` interface in the relevant `adapters/` subfolder; switch it on via the
   `LLM_PROVIDER` / `ORCHESTRATION_PROVIDER` env var. Do not change calling code anywhere else.

---

## 6. Conventions

| Item | Rule |
|---|---|
| Python files | `snake_case.py` |
| Python classes | `PascalCase` |
| Python functions/vars | `snake_case` |
| API routes | `/api/v1/<module-kebab-case>/...` |
| React components | `PascalCase.tsx`, one component per file |
| React hooks | `useCamelCase.ts` |
| Feature folder names | same concept, `snake_case` in backend, `kebab-case` in frontend |
| Branches | `feature/<module>-<short-desc>` |
| Commits | `<module>: <what changed>` (e.g. `escalation: add handoff packet generator`) |
| Env vars | `UPPER_SNAKE_CASE`, documented in `.env.example` |
| All external AI/orchestration calls | go through `adapters/`, never called inline in module code |
| All cross-module data shapes | defined once in `backend/app/shared/schemas/`, imported everywhere |

---

## 7. Existing Modules (update this table as modules are added)

| Module (backend) | Feature (frontend) | Responsibility | Status |
|---|---|---|---|
| `coordinator` | `chat-intake` | Ticket intake, classification, routing | planned |
| `specialist_agents` | `reasoning-trace` (shared view) | Billing/technical/order/account investigation | planned |
| `knowledge_engine` | — (feeds other features) | RAG retrieval + citation | planned |
| `escalation` | `escalation-view` | Confidence scoring, handoff packet | planned |
| `analytics` | `analytics-dashboard` | Clustering, trends, churn-risk, overview metrics | planned |
| `mock_systems` | `analytics-dashboard` (Mock Data Admin tab) | Mock CRM/billing/orders/ticket-history data + reset endpoint | planned |

Note: `analytics` and `mock_systems` are two separate backend modules, but they share **one**
frontend feature folder (`analytics-dashboard`), built as tabs (Overview / Clusters / Churn Risk /
Mock Data Admin) — see `docs/PRD.md` Section 2.1 for the full spec and role mapping.

Keep this table current — it's the fastest way for an AI agent (or teammate) to understand what
already exists before starting new work.

## 10. User Roles (Demo Scope)

No real auth in v1 — a UI-level role switcher ("Viewing as: Customer / Support Agent / Manager &
Admin") shows/hides routes. Full mapping of role → screen → endpoints is in `docs/PRD.md` Section
2.1. When building any feature, check that table to know which role(s) it's meant to be visible to.

---

## 8. Things to Never Do

- Never call Qwen or EnterPro APIs directly from module code — always through the adapter interface.
- Never hand-edit `shared-contracts/openapi.yaml` — it's generated from the backend.
- Never rename or remove a field in a shared schema without checking what else depends on it.
- Never put business logic in `components/ui/` (shadcn primitives) — that folder is for
  presentation-only components.
- Never hardcode secrets/API keys — use `.env`, documented in `.env.example`.
- Never build a feature as "just call the LLM with a big prompt and return the text" — every module's
  job is to reason over structured evidence (mock system data, retrieved docs, prior findings) and
  produce a structured, explainable result. That reasoning depth is the core point of this project.
- Never skip emitting reasoning-trace events for a new agent/decision step — the live trace panel is
  the project's most important feature and depends on every module reporting into it.

---

## 9. When You're Unsure

- If a task spans more than one module/feature folder, stop and note that it may need to be split, or
  proceed but clearly list every shared file touched.
- If you can't tell whether something belongs in `shared/` vs. a specific module, default to putting
  it in the module first — it's easier to promote something to shared later than to unwind a shared
  dependency multiple features have started relying on.
- If Qwen/EnterPro API details aren't available yet, build and test against the `mock_provider.py`
  implementations — the interface contract is what matters, not which provider is active.

---

*Companion document: `docs/PRD.md` for full product requirements, data model, and API surface.*
