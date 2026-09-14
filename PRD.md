# Nexus — Product Requirements Document

**Autonomous Multi-Agent Customer Support Orchestrator**
Track: Customer Support | Required stack: Qwen (reasoning) + EnterPro (orchestration)

Status: Draft v1.0 — ready for build
Doc owner: Team (shared)
Companion file: `CLAUDE.md` (root AI-agent instruction file — read alongside this doc)

---

## 1. Overview

Nexus resolves customer support tickets the way a strong senior agent would: it classifies the
issue, investigates root cause across the systems that actually hold the answer (billing, orders,
account, product knowledge), drafts a grounded response, and — only when it genuinely should —
hands off to a human with full context attached instead of a blank slate.

The system is built as a set of independent, composable **feature modules** (coordinator, specialist
agents, knowledge engine, escalation intelligence, analytics, mock backend systems) that communicate
through typed contracts. This PRD defines *what* to build, *how it's organized*, and *the rules that
keep the codebase clean* when multiple contributors (human or AI agent) are working in it at once.

### 1.1 Goals

- Demonstrate genuine cross-source reasoning and autonomous action, not a single-prompt chatbot.
- Use Qwen and EnterPro as load-bearing infrastructure, not decoration.
- Ship a full-stack, demo-ready product: frontend + backend + live reasoning visibility + analytics.
- Keep the codebase modular enough that any contributor can own one feature end-to-end without
  stepping on anyone else's files.

### 1.2 Non-Goals (out of scope for v1)

- Real integrations with actual CRM/billing/order systems — mocked data layer only.
- Multi-tenant support / authentication beyond a simple demo login.
- Voice or phone channel support.
- Production-grade horizontal scaling, rate limiting, or multi-region deployment.

---

## 2. Users & Personas

| Persona | Needs |
|---|---|
| **Customer** | Submit an issue in natural language, get a fast, accurate, non-repetitive resolution. |
| **Support Agent (human)** | When a ticket is escalated, receive full context instantly instead of re-investigating from scratch. |
| **Support Manager / Analyst** | See recurring issues, churn-risk signals, and resolution trends across all tickets. |
| **Judge / Demo viewer** | Needs to *see* the system reason, not just read a final answer. |

### 2.1 User Roles & Access (Demo Scope)

**No real authentication/authorization is built for v1** (see Non-Goals) — building real login,
sessions, and permission checks costs time that's better spent on the actual reasoning system, and
nobody will be attacking a hackathon demo. Instead, roles are handled **at the UI level only**: a
simple role switcher (a dropdown — "Viewing as: Customer / Support Agent / Manager & Admin") shows
or hides the relevant nav links and routes. This keeps the four user types conceptually clean for
the build, and doubles as a nice live demo moment (switch persona in front of judges to show the
same ticket from every side).

| Role | Sees / Can Do | Frontend Route(s) | Backend Endpoints Used |
|---|---|---|---|
| **Customer** | Submit a ticket, view their own conversation and its live reasoning trace. | `/` (chat-intake) | `coordinator` endpoints |
| **Support Agent** | View escalated tickets and their handoff packets. | `/escalation` (escalation-view) | `escalation` endpoints |
| **Manager / Analyst + Admin** | Everything on the **Dashboard** — analytics *and* mock-data administration, combined into one screen (see full spec below). Merged into one role because both are "internal/back-office" users and, for the demo, the same teammate builds both. | `/dashboard` (analytics-dashboard) | `analytics` + `mock_systems` endpoints |

> Real auth (login, per-user permissions, protected API routes) is explicitly deferred — flagged as
> a "Future / Out of Scope" item, not forgotten.

#### Dashboard — Full Feature Spec (assign this whole section to one teammate)

The Dashboard is one screen with tabs, combining the Analytics Engine and Mock Systems Admin so one
person can own the entire "back-office" side of the product end-to-end. It's built as a single
frontend feature (`frontend/src/features/analytics-dashboard/`) backed by two backend modules
(`analytics` + `mock_systems`), which stay separate on the backend even though they share one UI.

| Tab | Purpose | Data Shown | Backend Source |
|---|---|---|---|
| **Overview** | At-a-glance health of the support system | Total tickets, resolution rate, avg. resolution time, escalation rate, tickets-over-time chart | `analytics` module (new aggregate endpoint) |
| **Recurring Issues / Clusters** | Surfaces systemic problems before they snowball | List of issue clusters, ticket count per cluster, trend chart, Qwen-generated plain-language narrative per cluster | `GET /api/v1/analytics/clusters` |
| **Churn Risk** | Flags customers likely to leave | Table of at-risk customers, severity score, complaint frequency/sentiment trend | `GET /api/v1/analytics/churn-risk` |
| **Mock Data Admin** | Lets the team control demo state | View/edit CRM, billing, order, and ticket-history fixture records; one-click **reset to seed data** so the demo can be re-run cleanly | `GET /api/v1/mock/crm/{id}`, `/billing/{id}`, `/orders/{id}`, plus new `POST /api/v1/mock/reset` |

This addition to the API surface should be added to Section 9:

| Method | Path | Module | Purpose |
|---|---|---|---|
| POST | `/api/v1/mock/reset` | mock_systems | Reset all mock/fixture data back to seed state (for repeatable demos) |
| GET | `/api/v1/analytics/overview` | analytics | Aggregate health metrics for the Overview tab |

The teammate building the Dashboard owns, end-to-end: `backend/app/modules/analytics/`,
`backend/app/modules/mock_systems/`, and `frontend/src/features/analytics-dashboard/` (with its four
tabs as sub-components inside that one feature folder). No other module needs to be touched to build
this — it only *reads* ticket/trace data that other modules produce.

---

## 3. Functional Requirements

Requirements are grouped by **feature module** — this grouping is intentional and maps 1:1 to the
project's folder structure in Section 6, so each module can be built, tested, and owned
independently.

### 3.1 Module: Coordinator & Intake

- Accept a new customer ticket (text) via API and/or chat widget.
- Classify **intent**, **urgency**, and **sentiment** using Qwen.
- Decide which specialist agent(s) to invoke (single or parallel dispatch).
- Own the final routing decision and emit every step to the shared reasoning-trace event stream.
- Maintain conversation state across multiple turns for a given ticket/customer.
- Recognize returning customers and reuse prior context (conversation memory).

### 3.2 Module: Specialist Agents & Investigation

- Four specialist agents, each independently invocable: **Billing**, **Technical**, **Order**,
  **Account**.
- Each agent queries its relevant mock backend system (Section 3.6) and reasons over the result to
  find **root cause**, not just a surface category.
- Each agent returns a structured finding: `{summary, evidence, confidence, actions_available}`.
- Agents must be able to run in parallel when a ticket spans more than one domain (e.g. billing +
  order).
- New specialist agents can be added later without modifying existing ones (plugin-style registration
  — see Section 7.3).

### 3.3 Module: Knowledge Reasoning Engine (RAG)

- Ingest and index company documentation, product info, and past resolved tickets.
- Retrieve relevant grounding context for any given ticket.
- Every generated customer-facing response must cite which document/ticket informed it.
- Provide a simple ingestion endpoint/script so the knowledge base can be seeded/updated for the demo.

### 3.4 Module: Escalation Intelligence

- Aggregate confidence across all specialist agents that touched a ticket.
- Decide whether to auto-resolve or escalate to a human, with a **written justification**, not just a
  number.
- On escalation, auto-generate a structured **handoff packet**: issue summary, systems already
  checked, actions already attempted, customer sentiment trend, recommended next step.
- Push escalated tickets into a human queue (simulated) via the orchestration layer.

### 3.5 Module: CX Analytics Engine

- Aggregate resolved/escalated ticket data into recurring-issue clusters.
- Surface churn-risk signals (complaint severity + frequency + sentiment trend per customer).
- Provide a dashboard-ready API: trend over time, top clusters, escalation rate, avg. resolution time.
- Generate short plain-language narratives explaining *why* a cluster is trending (Qwen-generated).

### 3.6 Module: Mock Backend Systems

- Four mock systems, each with realistic seeded data and a small query API:
  - **CRM** — customer_id, tier, account status, contact history.
  - **Billing Ledger** — transactions, subscription state, refund history.
  - **Order Database** — order_id, status, shipping events, fulfillment issues.
  - **Ticket History** — prior tickets per customer, resolution notes, sentiment over time.
- These stand in for real enterprise systems so the "investigation across systems" story is credible
  without real integrations.
- Must be realistic (real-looking names, dates, amounts) — no obvious placeholder data.

### 3.7 Cross-Cutting: Reasoning Trace

- Every module emits structured events (`agent_started`, `agent_finished`, `decision_made`,
  `escalation_triggered`, etc.) to a shared, append-only trace store per ticket.
- Frontend subscribes to this stream and renders it live — this is the single highest-value demo
  feature and must never be cut from scope.

### 3.8 Frontend-Facing Features

- **Chat/Intake UI** — submit a ticket, see the conversation.
- **Live Reasoning Trace panel** — real-time visual log of what the system is doing, per ticket.
- **Escalation / Handoff view** — what a human agent would see when a ticket is escalated.
- **CX Analytics Dashboard** — clusters, trends, churn-risk, resolution metrics.
- **(Optional) Mock Data Admin view** — inspect/edit the seeded mock systems for demo control.

---

## 4. Tech Stack

The problem statement mandates two specific components — both are used as **first-class,
load-bearing infrastructure**, never bypassed:

| Requirement | Choice | Role |
|---|---|---|
| **AI reasoning engine (required)** | **Qwen** | All classification, root-cause reasoning, RAG-grounded generation, escalation justification, and analytics narratives. |
| **Orchestration / workflow (required)** | **EnterPro** | Routes tickets between agents, triggers the escalation workflow, schedules the analytics pipeline, handles deployment. |

Because we don't yet have confirmed API access/docs for either, **both sit behind a clean adapter
interface** (Section 7.2) so the rest of the codebase never talks to Qwen or EnterPro directly — it
talks to an interface that a Qwen/EnterPro implementation (or a local mock, for offline development)
fulfills. This means development is never blocked waiting on credentials, and swapping in the real
SDK later is a one-file change.

| Layer | Choice | Why |
|---|---|---|
| **Backend framework** | **Python + FastAPI** | Async-native (needed for parallel agent calls), automatic OpenAPI schema generation (which doubles as the frontend/backend contract), Pydantic for strict typed schemas everywhere, easiest language for AI-agent-written code to stay consistent in. |
| **Backend package/dep mgmt** | `uv` or `poetry` (pick one, document in `CLAUDE.md`) | Reproducible envs per contributor. |
| **Database** | **PostgreSQL** (or **SQLite** for local/demo simplicity) via **SQLAlchemy + Alembic** | Relational data (tickets, agent findings, escalation packets) with clear migrations; SQLite is a drop-in for a fast hackathon demo, Postgres if you want it closer to production. |
| **Vector store (for RAG)** | **ChromaDB** (local, embedded, zero infra) | Fastest to stand up for a hackathon; swappable later for a hosted vector DB. |
| **Embeddings** | Via the Qwen adapter if it exposes embeddings, else a small local sentence-embedding model as fallback | Keeps the knowledge engine functional even if only LLM (not embedding) access is available. |
| **Task/event handling** | In-process async event bus (Python `asyncio` pub/sub) for the reasoning trace; EnterPro handles cross-module workflow triggers | Keeps trace latency low for the live demo panel. |
| **API contract** | **OpenAPI**, auto-generated from FastAPI, exported to `shared-contracts/openapi.yaml` | Single source of truth consumed by the frontend's typed API client. |

### 4.1 Frontend Stack — Recommendation

**Your instinct (React + shadcn/ui) is the right call — confirmed as the recommendation**, with a
few additions that matter specifically for this project:

| Layer | Choice | Why |
|---|---|---|
| **Framework** | **React 18 + Vite** | Fast dev server, no framework lock-in overhead, easiest for AI agents to generate correct code for (huge ecosystem/training data). |
| **Language** | **TypeScript** | Non-negotiable for a multi-contributor project — type errors catch cross-module contract breaks before runtime. |
| **UI components** | **shadcn/ui + Tailwind CSS** | shadcn gives you owned, editable component source (not a black-box npm package) — ideal when AI agents need to modify component internals; Tailwind keeps styling consistent across contributors without a shared CSS file everyone edits. |
| **Data fetching / server state** | **TanStack Query (React Query)** | Handles polling/streaming ticket + trace updates, caching, and loading states with minimal boilerplate — important since multiple features (chat, trace panel, dashboard) all read overlapping server state. |
| **Live trace updates** | **Server-Sent Events (SSE)** from FastAPI, consumed via a small typed hook | Simpler and more reliable than WebSockets for a one-directional live trace feed; FastAPI supports SSE natively and it demos well. |
| **Client-side global state** (if needed beyond server state) | **Zustand** | Minimal, avoids Redux boilerplate, easy for any contributor to extend without touching others' slices. |
| **Charts (analytics dashboard)** | **Recharts** | Pairs cleanly with shadcn's design language, simple declarative API. |
| **Routing** | **React Router** | Standard, minimal-surprise choice. |
| **Typed API client** | Generated from `shared-contracts/openapi.yaml` via `openapi-typescript` (+ a thin fetch wrapper) | Frontend and backend can never silently drift out of sync — regenerate the client, get a compile error if something changed. |

This stack was chosen specifically because it optimizes for **AI-agent-generated code quality and
low merge-conflict risk**: TypeScript + generated API types catch contract mismatches immediately,
shadcn's copy-into-your-repo model means component code is inspectable/editable rather than opaque,
and TanStack Query removes the need for hand-rolled state-sync logic that tends to sprawl across
files and cause conflicts.

---

## 5. System Architecture

### 5.1 Request Flow

```
Customer message
      │
      ▼
Intake API (Coordinator module)
      │  Qwen: classify intent / urgency / sentiment
      ▼
EnterPro: route to specialist agent(s)   ──► parallel dispatch if multi-domain
      │
      ▼
Specialist Agent(s)  ──► query Mock Backend System(s)  ──► Qwen: root-cause reasoning
      │
      ▼
Knowledge Reasoning Engine (RAG retrieval over docs + past tickets)
      │
      ▼
Response Generator (Qwen, grounded in agent findings + RAG context)
      │
      ▼
Escalation Intelligence ──► confidence below threshold? ──► EnterPro: trigger human handoff workflow
      │                                                              │
      ▼                                                              ▼
Reply sent to customer                                    Handoff packet generated (Qwen)
      │
      ▼
Every step logged to Reasoning Trace store (streamed live to frontend via SSE)
      │
      ▼
CX Analytics Engine (batch/scheduled via EnterPro) ──► clusters, trends, churn signals
```

### 5.2 Adapter Pattern for Qwen & EnterPro

Because neither integration is confirmed yet, both are defined as **interfaces first**:

```
adapters/
├── llm/
│   ├── base.py            # abstract LLMProvider: complete(), classify(), embed()
│   ├── qwen_provider.py   # real implementation — fill in once API access confirmed
│   └── mock_provider.py   # deterministic stub for offline dev + tests
└── orchestration/
    ├── base.py                 # abstract OrchestrationProvider: route(), trigger_workflow(), schedule()
    ├── enterpro_provider.py    # real implementation
    └── mock_provider.py        # local in-process stand-in for offline dev + tests
```

Every module depends on `LLMProvider` / `OrchestrationProvider` (the interface), **never** on a
concrete provider class. The active implementation is selected once, in config, via an environment
variable (`LLM_PROVIDER=qwen|mock`, `ORCHESTRATION_PROVIDER=enterpro|mock`). This means:

- Development is never blocked waiting on credentials.
- Swapping in real Qwen/EnterPro access later touches exactly two files.
- Unit tests run fully offline against the mock providers.

---

## 6. Project Structure

Full repository layout. **Section 7 explains the ownership rules that make this safe for multiple
simultaneous contributors (human or AI agent).**

```
nexus/
├── CLAUDE.md                          # root AI-agent instruction file — READ FIRST
├── README.md                          # human-facing quickstart
├── .env.example
├── .gitignore
├── docker-compose.yml                 # optional: postgres + backend + frontend for local dev
│
├── docs/
│   ├── PRD.md                         # this document
│   ├── architecture.md                # architecture diagrams, expanded
│   ├── api-contracts.md               # human-readable endpoint summary (generated OpenAPI is source of truth)
│   └── decisions/                     # short ADRs (architecture decision records) — one per notable choice
│
├── shared-contracts/
│   └── openapi.yaml                   # AUTO-GENERATED from backend — never hand-edit
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic/                       # DB migrations
│   ├── app/
│   │   ├── main.py                    # FastAPI app entry — mounts all module routers
│   │   │
│   │   ├── core/                      # ⚠ SHARED — changes need a quick heads-up to the team
│   │   │   ├── config.py              # settings, env var loading
│   │   │   ├── logging.py
│   │   │   ├── exceptions.py          # shared exception types + FastAPI handlers
│   │   │   └── security.py            # demo auth if any
│   │   │
│   │   ├── adapters/                  # ⚠ SHARED — interfaces are shared; providers can be edited freely
│   │   │   ├── llm/
│   │   │   │   ├── base.py
│   │   │   │   ├── qwen_provider.py
│   │   │   │   └── mock_provider.py
│   │   │   └── orchestration/
│   │   │       ├── base.py
│   │   │       ├── enterpro_provider.py
│   │   │       └── mock_provider.py
│   │   │
│   │   ├── shared/                    # ⚠ SHARED — cross-module types/utilities, additive changes only
│   │   │   ├── schemas/               # Pydantic models used across modules: Ticket, Message, AgentFinding, TraceEvent...
│   │   │   ├── db/                    # SQLAlchemy base, session management
│   │   │   ├── events/                # reasoning-trace pub/sub bus
│   │   │   └── utils/
│   │   │
│   │   ├── modules/                   # ✅ ISOLATED — one folder per feature, own it end-to-end
│   │   │   │
│   │   │   ├── coordinator/           # Feature: intake, classification, routing
│   │   │   │   ├── router.py          # FastAPI routes for this module
│   │   │   │   ├── service.py         # business logic
│   │   │   │   ├── agent.py           # coordinator agent logic (Qwen calls)
│   │   │   │   ├── schemas.py         # module-local Pydantic models
│   │   │   │   ├── prompts.py         # prompt templates, kept separate from logic
│   │   │   │   └── tests/
│   │   │   │
│   │   │   ├── specialist_agents/     # Feature: billing / technical / order / account investigation
│   │   │   │   ├── base_agent.py      # shared base class all four specialists extend
│   │   │   │   ├── billing/
│   │   │   │   │   ├── agent.py
│   │   │   │   │   └── prompts.py
│   │   │   │   ├── technical/
│   │   │   │   ├── order/
│   │   │   │   ├── account/
│   │   │   │   ├── router.py
│   │   │   │   └── tests/
│   │   │   │
│   │   │   ├── knowledge_engine/      # Feature: RAG — ingestion + retrieval + citation
│   │   │   │   ├── ingest.py
│   │   │   │   ├── retriever.py
│   │   │   │   ├── embeddings.py
│   │   │   │   ├── router.py
│   │   │   │   └── tests/
│   │   │   │
│   │   │   ├── escalation/            # Feature: confidence scoring + handoff packet generation
│   │   │   │   ├── scorer.py
│   │   │   │   ├── handoff.py
│   │   │   │   ├── router.py
│   │   │   │   └── tests/
│   │   │   │
│   │   │   ├── analytics/             # Feature: CX analytics — clustering, trends, churn signals
│   │   │   │   ├── aggregator.py
│   │   │   │   ├── clustering.py
│   │   │   │   ├── narratives.py      # Qwen-generated explanations
│   │   │   │   ├── router.py
│   │   │   │   └── tests/
│   │   │   │
│   │   │   └── mock_systems/          # Feature: mock CRM / billing / orders / ticket history
│   │   │       ├── crm.py
│   │   │       ├── billing_ledger.py
│   │   │       ├── orders.py
│   │   │       ├── ticket_history.py
│   │   │       ├── fixtures/          # seed data (JSON/CSV)
│   │   │       ├── router.py
│   │   │       └── tests/
│   │   │
│   │   └── api/
│   │       └── v1/
│   │           └── api.py             # aggregates every module's router into one prefix
│   │
│   └── tests/
│       └── integration/               # cross-module end-to-end tests
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes/                    # route-level page components
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                    # ⚠ SHARED — shadcn-generated primitives (Button, Card, Dialog...)
│   │   │   └── shared/                # ⚠ SHARED — app-level shared components (Layout, Navbar, ErrorBoundary)
│   │   │
│   │   ├── features/                  # ✅ ISOLATED — one folder per feature, mirrors backend modules
│   │   │   ├── chat-intake/           # ticket submission UI + conversation view
│   │   │   │   ├── components/
│   │   │   │   ├── hooks/
│   │   │   │   ├── api.ts
│   │   │   │   └── types.ts
│   │   │   ├── reasoning-trace/       # live agent trace panel (SSE consumer)
│   │   │   ├── escalation-view/       # handoff packet display
│   │   │   ├── analytics-dashboard/   # CX analytics charts + tables
│   │   │   └── admin-mock-data/       # optional: inspect/edit mock system data
│   │   │
│   │   ├── lib/                       # ⚠ SHARED — API client (generated), query client, generic utils
│   │   ├── hooks/                     # ⚠ SHARED — cross-feature hooks only (e.g. useSSE, useDebounce)
│   │   ├── types/                     # ⚠ SHARED — generated types from shared-contracts/openapi.yaml
│   │   └── store/                     # zustand slices — one file per feature if global state is needed
│   │
│   └── tests/
│
└── scripts/
    ├── seed_mock_data.py              # populate mock systems + vector store for a fresh demo run
    └── generate_frontend_types.sh     # regenerate frontend/src/types from shared-contracts/openapi.yaml
```

---

## 7. Module Boundaries & Ownership Rules

The structure above is designed around one rule: **`modules/*` (backend) and `features/*` (frontend)
are isolated; everything else is shared and requires more care when editing.**

### 7.1 Isolated zones — safe to build independently

- `backend/app/modules/<feature_name>/` — a contributor (or AI agent) working here should never
  need to edit another module's folder. Cross-module communication happens only through:
  - shared Pydantic schemas in `app/shared/schemas/`
  - the shared event bus in `app/shared/events/`
  - the adapter interfaces in `app/adapters/`
- `frontend/src/features/<feature_name>/` — same rule. A feature folder owns its own components,
  hooks, and API-calling code. It may import from `components/ui`, `lib`, `types`, and `hooks`, but
  never reaches into another feature folder.

### 7.2 Shared zones — edit with care, keep changes additive

- `app/shared/schemas/`, `app/adapters/*/base.py`, `frontend/src/types/`, `frontend/src/lib/` —
  these are contracts other modules depend on. Rule of thumb: **add new fields/types, don't rename or
  remove existing ones** without checking who else uses them. If a shared schema must change in a
  breaking way, say so explicitly in the PR/commit message.
- `components/ui/` (shadcn primitives) — safe to add new shadcn components; avoid editing the
  internals of a component another feature already depends on unless the change is visual-only.

### 7.3 How to add a new feature/module (for future extension)

1. Backend: create `backend/app/modules/<name>/` with `router.py`, `service.py`, `schemas.py`,
   `tests/`. Register the router in `backend/app/api/v1/api.py`. Add any new shared types to
   `app/shared/schemas/` (additive only).
2. Frontend: create `frontend/src/features/<name>/` with `components/`, `hooks/`, `api.ts`,
   `types.ts`. Add a route in `src/routes/` if it needs its own page.
3. If the module needs a new specialist agent specifically, extend `specialist_agents/base_agent.py`
   rather than duplicating logic — this keeps all agents consistent for the coordinator to dispatch to.

### 7.4 Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Python files/modules | `snake_case` | `billing_ledger.py` |
| Python classes | `PascalCase` | `class BillingAgent` |
| Python functions/vars | `snake_case` | `def investigate_charge()` |
| Pydantic schema files | `schemas.py` inside each module | — |
| FastAPI route prefixes | `/api/v1/<module-kebab>` | `/api/v1/specialist-agents/billing` |
| TS/React components | `PascalCase.tsx` | `ReasoningTracePanel.tsx` |
| TS hooks | `useCamelCase.ts` | `useReasoningTrace.ts` |
| Feature folders (both FE/BE) | `kebab_case` (FE) / `snake_case` (BE), same concept name | `reasoning-trace` / `escalation` |
| Branches | `feature/<module-name>-<short-desc>` | `feature/escalation-handoff-packet` |
| Commits | `<module>: <what changed>` | `analytics: add churn-risk scoring` |
| Env vars | `UPPER_SNAKE_CASE` | `LLM_PROVIDER`, `ORCHESTRATION_PROVIDER` |

---

## 8. Data Model (Core Entities)

| Entity | Key Fields | Owned by module |
|---|---|---|
| `Ticket` | id, customer_id, status, created_at, messages[] | coordinator (shared schema) |
| `Message` | id, ticket_id, role, content, timestamp | coordinator (shared schema) |
| `AgentFinding` | id, ticket_id, agent_name, summary, evidence, confidence | specialist_agents |
| `TraceEvent` | id, ticket_id, event_type, payload, timestamp | shared/events |
| `EscalationPacket` | id, ticket_id, justification, actions_attempted, sentiment_trend, recommended_next_step | escalation |
| `KnowledgeChunk` | id, source, content, embedding | knowledge_engine |
| `AnalyticsSnapshot` | id, period, cluster_label, ticket_count, trend_narrative | analytics |
| Mock: `CRMRecord`, `BillingRecord`, `OrderRecord`, `TicketHistoryRecord` | (see mock_systems fixtures) | mock_systems |

All entities are defined once as Pydantic models in `app/shared/schemas/` and reused everywhere —
no module redefines another module's entity shape.

---

## 9. API Surface (Summary)

Full contract lives in the auto-generated `shared-contracts/openapi.yaml`. Human-readable summary:

| Method | Path | Module | Purpose |
|---|---|---|---|
| POST | `/api/v1/coordinator/tickets` | coordinator | Submit a new ticket |
| GET | `/api/v1/coordinator/tickets/{id}` | coordinator | Get ticket + conversation state |
| GET | `/api/v1/coordinator/tickets/{id}/trace` (SSE) | coordinator/shared | Live reasoning trace stream |
| POST | `/api/v1/specialist-agents/{domain}/investigate` | specialist_agents | Invoke a specialist agent |
| GET | `/api/v1/knowledge/search` | knowledge_engine | RAG retrieval for a query |
| POST | `/api/v1/knowledge/ingest` | knowledge_engine | Ingest a new document |
| POST | `/api/v1/escalation/evaluate` | escalation | Score confidence, decide escalate y/n |
| GET | `/api/v1/escalation/{ticket_id}/packet` | escalation | Get generated handoff packet |
| GET | `/api/v1/analytics/clusters` | analytics | Recurring-issue clusters |
| GET | `/api/v1/analytics/churn-risk` | analytics | Churn-risk-flagged customers |
| GET | `/api/v1/analytics/overview` | analytics | Aggregate health metrics for the Dashboard Overview tab |
| GET | `/api/v1/mock/crm/{customer_id}` | mock_systems | Mock CRM lookup |
| GET | `/api/v1/mock/billing/{customer_id}` | mock_systems | Mock billing lookup |
| GET | `/api/v1/mock/orders/{customer_id}` | mock_systems | Mock order lookup |
| POST | `/api/v1/mock/reset` | mock_systems | Reset all mock/fixture data to seed state (repeatable demos) |

---

## 10. Non-Functional Requirements

- **Latency**: reasoning trace events must appear in the UI within ~1s of occurring (SSE, not polling).
- **Resilience**: if a specialist agent's mock backend call fails, the coordinator must degrade
  gracefully (partial findings + lower confidence) rather than crash the ticket.
- **Config-driven providers**: no module ever hardcodes "we're using Qwen" or "we're using EnterPro"
  directly — always through the adapter interface + env var.
- **Test coverage**: every module ships with unit tests runnable fully offline against mock providers.
- **Secrets**: all API keys/config in `.env` (gitignored); `.env.example` documents every required var.

---

## 11. Build Phases (capability-based, not person-based)

| Phase | Deliverable |
|---|---|
| 1 — Foundation | Repo scaffold, adapters (mock providers working), mock backend systems + seed data, shared schemas, OpenAPI pipeline. |
| 2 — Core Loop | Coordinator + one specialist agent (Billing) working end-to-end with real Qwen/EnterPro calls (or best available access). |
| 3 — Full Agent Set | Remaining specialist agents, knowledge engine (RAG), parallel dispatch for multi-domain tickets. |
| 4 — Escalation + Trace UI | Escalation intelligence, handoff packet, live reasoning-trace panel on frontend (do not cut this). |
| 5 — Analytics | CX analytics engine + dashboard. |
| 6 — Polish | Error states, realistic seed data pass, demo rehearsal. |

---

## 12. Open Questions / Assumptions to Confirm

- Exact Qwen API surface (chat completion only, or also embeddings?) — affects `embeddings.py` fallback.
- Exact EnterPro capabilities (workflow triggers, scheduling, deployment?) — affects how much of
  orchestration logic lives in `orchestration/enterpro_provider.py` vs. application code.
- Auth requirements for the demo (likely none needed beyond a mock customer_id).
- Database choice for the actual build: SQLite (fastest to start) vs. Postgres (closer to prod) —
  default to SQLite unless the team prefers otherwise.

---

*See `CLAUDE.md` in the project root for the AI-agent operating instructions that accompany this PRD.*
