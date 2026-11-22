# KNITAU × KeNIP — Full-Stack Production System Architecture & Kick-Off Guide

## 1. End-to-End System Topology

```text
  [ React 19 + TypeScript PWA ]              [ Feature Phones (*384*...) ]
   - Memory JWT + HttpOnly Refresh            - Safaricom / Airtel via
   - IndexedDB Offline Sync Queue               Africa's Talking Gateway
   - Typed OpenAPI Client (SSOT)                        |
                 |                                      | HTTPS Webhook (HMAC)
                 v                                      v
        [ Nginx / Cloud Load Balancer + TLS 1.3 + WAF ]
                 |                                      |
                 +------------------+-------------------+
                                    |
                                    v
             [ Django 5 + DRF Modular Monolith (web_api) ]
              - Central RBAC (HasKnitauRole + Admin Sub-Roles)
              - OpenAPI Schema Generator (drf-spectacular)
              - SHA-256 Hash-Chained Audit Ledger (apps.audit)
              - Redis Idempotency Locks (X-Idempotency-Key)
                 |                  |                  |
       +---------+        +---------+--------+         +---------+
       v                  v                  v                   v
 [ PgBouncer ]       [ Redis 7 ]      [ worker_payments ]  [ worker_default ]
       |            (Cache + Locks)   (M-Pesa B2C Only)    (SMS, PDF, Matching)
       v                                     |                   |
 [ PostgreSQL 16 ]                           v                   v
  - Primary (Writes)               [ Safaricom Daraja ]  [ MinIO / S3 Vault ]
  - Read Replica (Analytics)                               (KYC, Exit Letters)
```

### Why This Architecture Fits KNITAU × KeNIP
- **High Reliability Under Rapid Growth**: Stateless Django `web_api` pods scale horizontally behind PgBouncer (`transaction` pooling), while heavy analytics read from a PostgreSQL Read Replica.
- **Zero Financial Race Conditions**: Stipends, Per-Diem, PPE payouts, 4-way Exit Clearances, and Audit Logs commit inside ACID `@transaction.atomic` blocks. Payment tasks run in an isolated `payments_mpesa` queue so SMS blasts or PDF exports can never delay disbursements.
- **Single Source of Truth (SSOT)**: Backend `drf-spectacular` generates `openapi-schema.yaml`; the React frontend generates its TypeScript interfaces (`schema.d.ts`) directly from that file. Backend and frontend never drift out of sync.
- **Kenya Connectivity Resilience**: The React PWA buffers critical forms (field check-ins, PPE receipts, grievances) in IndexedDB with a client-generated `X-Idempotency-Key` UUID, syncing safely on reconnect without duplicate records.

---

## 2. Full-Stack Repository Layout (Folder & File Map)

```text
├── ARCHITECTURE.md                      # This full-stack system & kick-off manual
├── docker-compose.yml                   # Local/staging stack (PG16, PgBouncer, Redis, MinIO, API, Workers)
├── index.html                           # Existing interactive UI prototype
│
├── backend/                             # PYTHON / DJANGO MODULAR MONOLITH
│   ├── Makefile                         # test, lint, contracts, schema, migrate, run
│   ├── pyproject.toml                   # Dependencies, Ruff, Pytest & import-linter boundary rules
│   ├── .env.example                     # Server-side secret placeholders (DB, M-Pesa, USSD, S3)
│   ├── manage.py & Dockerfile           # Django CLI & non-root production image
│   ├── config/
│   │   ├── celery.py                    # Isolated task queues (payments_mpesa vs default)
│   │   ├── urls.py                      # /healthz/, /api/schema/, /api/docs/, /api/v1/*
│   │   └── settings/{base,local,production}.py
│   └── apps/
│       ├── common/                      # Shared Kernel: UUID models, SoftDelete, RBAC, Idempotency, Events
│       ├── audit/                       # Immutable SHA-256 hash-chained AuditLog + PII redaction
│       ├── corridor/                    # Reference Domain: Diaspora Mentors, Bio, Skill Similarity Engine
│       ├── identity/                    # Users, KYC, Employers, TVET/Uni Institutions, Career Passport
│       ├── welfare/                     # Stipends, Per-Diem, PPE Claims, M-Pesa B2C Payouts
│       ├── exit_workflow/               # Early Exit, Dismissal Defense, 4-Way Clearance, Exit Letters
│       ├── grievances/                  # Confidential Reporting, Escalation SLA, Post-Interaction Pulse
│       └── ussd_gateway/                # Stateless *384* USSD handler + Africa's Talking webhooks
│
└── frontend/                            # REACT + TYPESCRIPT + TAILWIND PWA
    ├── Makefile                         # dev, build, test, lint, codegen-api
    ├── package.json                     # React 19, TypeScript, Vite, TanStack Query, Zod, Vitest, Playwright
    ├── .env.example                     # Public build-time vars ONLY (VITE_API_BASE_URL)
    └── src/
        ├── app/                         # App shell, Router, QueryClientProvider, AuthProvider
        ├── design-system/
        │   ├── tokens.ts                # Strict 5-color KNITAU palette & typography tokens
        │   └── components/              # Reusable UI primitives (Card, Badge, Modal, Table, Stepper)
        ├── lib/
        │   ├── api/
        │   │   ├── schema.d.ts          # AUTO-GENERATED from backend openapi-schema.yaml (SSOT)
        │   │   └── client.ts            # Fetch/Axios wrapper: injects Bearer JWT + auto-refresh + X-Idempotency-Key
        │   ├── auth/
        │   │   ├── rbac.ts              # Mirror of backend roles & admin sub-roles + route guards
        │   │   └── session.ts           # In-memory Access Token store (never stored in localStorage)
        │   └── offline/
        │       └── idempotency.ts       # Offline IndexedDB mutation queue + retry backoff + UUID keys
        └── features/                    # Vertical feature slices matching backend apps 1:1
            ├── auth/                    # Login, OTP/2FA, Role Switcher (if permitted)
            ├── passport/                # Career Passport, active skill toggles, verified credential badges
            ├── corridor/                # Global Corridor, Diaspora Mentor cards (Bio + Similarity %), Return/Jobs
            ├── welfare/                 # Stipend ledger, Per-Diem & PPE claims, M-Pesa PIN release confirmation
            ├── exit-workflow/           # 4-way clearance tracker, dismissal defense, Exit Letter PDF viewer
            ├── grievances/              # Confidential ticket submission, timeline, Post-Interaction Pulse survey
            └── admin/                   # Sub-role scoped Observatory (Executive, Case, Finance, Chapter Rep)
```

---

## 3. Frontend Architecture Deep Dive (React + TypeScript)

### A. Feature-Sliced Modularity (`src/features/<domain>/`)
Every business domain is isolated inside its own feature folder. Components from `features/welfare/` must **never** import internals of `features/corridor/` — shared primitives live strictly in `design-system/` or `lib/`.

Inside each feature folder (`e.g. features/corridor/`):
- `types.ts` — Re-exports exact types generated from `lib/api/schema.d.ts` (zero hand-written duplicate backend types).
- `api.ts` — TanStack Query hooks (`useMatchedMentorsQuery`, `useRegisterMentorMutation`).
- `components/` — Presentational components (e.g., `DiasporaMentorCard.tsx` showing `bio`, `similarity_score`, and `matched_tags`).
- `pages/` — Route entry views (`GlobalCorridorPage.tsx`).
- `__tests__/` — Component & hook tests using Vitest + Mock Service Worker (MSW).

### B. State Management Discipline (Three Clean Buckets)
Do **not** dump everything into one giant global store:
1. **Server State → TanStack Query**: All API data (mentors, stipends, exit clearances, grievances). Handles caching, background refetching, pagination, and optimistic updates.
2. **Auth & Session State → React Context (Memory Only)**: Holds current `user`, `role`, `admin_sub_role`, and short-lived `accessToken` in JavaScript memory (refresh happens via `HttpOnly; Secure; SameSite=None` cookie or secure rotation endpoint—never store tokens in `localStorage`).
3. **Offline Field Queue → IndexedDB (`lib/offline/`)**: When `navigator.onLine === false`, mutations like check-ins, PPE claims, and grievances serialize into IndexedDB with a unique `idempotencyKey = crypto.randomUUID()`. On `online`, the sync worker replays them sequentially with `X-Idempotency-Key` headers.

### C. Single Source of Truth (OpenAPI Codegen Workflow)
1. Backend developer modifies a serializer in `backend/apps/<module>/api/serializers.py`.
2. Backend runs `make schema` → updates `backend/openapi-schema.yaml`.
3. Frontend runs `make codegen-api` (`openapi-typescript ../backend/openapi-schema.yaml -o src/lib/api/schema.d.ts`).
4. TypeScript immediately flags any frontend component reading a renamed or removed field at compile time.

### D. Frontend RBAC & Route Guards (`src/lib/auth/rbac.ts`)
- Mirrors backend `KnitauRole` (`intern`, `employer`, `institution`, `admin`) and `AdminSubRole` (`executive`, `case_officer`, `finance_officer`, `chapter_rep`) from a single typed matrix.
- Route guards (`<RequireRole roles={['admin']} subRoles={['finance_officer', 'executive']} />`) control navigation visibility; **backend `HasKnitauRole` always enforces the authoritative security check**.

### E. Strict KNITAU Visual & Copy Standards (`src/design-system/tokens.ts`)
- **Strict 5-Color Palette Only**:
  - Charcoal `#231F20` (primary text, headers, dark panels)
  - Crimson `#C82128` (alerts, grievances, urgent actions)
  - Forest Green `#0F6B38` (verified status, M-Pesa payouts, active matches)
  - Gold `#F4C823` (highlights, pending reviews, diaspora badges)
  - White `#FFFFFF` (surfaces and clean cards)
- **Clean User Copy**: Never surface internal storage or engineering terms (`localStorage`, `IndexedDB`, `Mock`, `Simulation`) in visible UI strings.

---

## 4. Full-Stack Testing & Quality Matrix

| Layer | Tooling | What It Verifies | Command |
| :--- | :--- | :--- | :--- |
| **Backend Boundaries** | `import-linter` | Zero illegal cross-module model imports | `cd backend && make contracts` |
| **Backend Unit & DB** | `pytest` + `pytest-django` | Similarity math, `@transaction.atomic`, RBAC 403s, `AuditLog` hash chain | `cd backend && make test` |
| **Backend Security/Lint** | `ruff`, `mypy`, `bandit` | Type safety, SQL/secret hygiene, code style | `cd backend && make lint` |
| **Frontend Types & Build** | `tsc --noEmit` + `vite build` | OpenAPI contract compatibility & bundle health | `cd frontend && npm run lint && npm run build` |
| **Frontend Unit/UI** | `vitest` + React Testing Library + MSW | Component rendering (e.g. Mentor Bio, Similarity badge), RBAC hiding, offline queue | `cd frontend && npm test` |
| **End-to-End Journeys** | `playwright` | Intern login → Passport toggle → Global Corridor match → Welfare claim → Admin approval | `cd frontend && npm run test:e2e` |

---

## 5. Team Kick-Off Workflow (Day 1 to Production)

1. **Contract-First Kick-Off (Day 1)**:
   - Backend and Frontend leads agree on module endpoints and Pydantic/DRF serializer fields for Modules 1–4.
   - Backend generates `openapi-schema.yaml`; Frontend runs `make codegen-api` so both teams code in parallel on Day 1 without blocking each other.
2. **Feature Branch Rhythm**:
   - Every PR must pass **5 CI gates**: `make contracts` + `make test` + `make lint` (Backend) and `tsc --noEmit` + `vitest` (Frontend).
   - Database migrations must preserve backward compatibility (`SoftDeleteModel`, additive migrations) so zero-downtime rolling deploys work safely.
3. **Production Deployment Checklist**:
   - Configure server-only secrets (`DJANGO_SECRET_KEY`, DB/PgBouncer, Redis, M-Pesa Daraja keys, Africa's Talking API key, S3 credentials) via cloud secret manager — never in `.env` committed to Git or `VITE_*` variables.
   - Apply PostgreSQL `REVOKE UPDATE, DELETE` on `audit_auditlog` migration before go-live.
   - Scale `web_api` behind TLS 1.3 CDN/Load Balancer and run `worker_payments` on a dedicated high-reliability node.
