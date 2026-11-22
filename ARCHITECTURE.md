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
├── .github/workflows/ci.yml             # Automated PR gates: contracts, pytest, ruff/mypy/bandit, OpenAPI, frontend
├── docker-compose.yml                   # Local/staging stack (Nginx, PG16, PgBouncer, Redis, MinIO, API, Workers)
├── infra/nginx/nginx.conf               # Edge reverse proxy: rate limits, TLS headers, X-Request-ID, 15MB upload cap
├── index.html                           # Existing interactive UI prototype
│
├── backend/                             # PYTHON / DJANGO MODULAR MONOLITH
│   ├── Makefile                         # test, lint, contracts, schema, migrate, run
│   ├── pyproject.toml                   # Dependencies, Ruff, Pytest & import-linter boundary rules
│   ├── .env.example                     # Server-side secret placeholders (DB, M-Pesa, USSD, S3)
│   ├── manage.py & Dockerfile           # Django CLI & non-root production image
│   ├── config/
│   │   ├── celery.py                    # Isolated task queues (payments_mpesa vs default)
│   │   ├── urls.py                      # /healthz/, /api/schema/, /api/docs/, /api/v1/{auth,corridor,welfare,ussd}/*
│   │   └── settings/{base,local,production}.py
│   └── apps/
│       ├── common/                      # Shared Kernel: UUID models, SoftDelete, RBAC, Idempotency, Events, Tracing
│       ├── audit/                       # Immutable SHA-256 AuditLog + PostgreSQL trigger migration (0002)
│       ├── identity/                    # Custom User (AUTH_USER_MODEL), DPA ID hashing, JWT + HttpOnly Refresh API
│       ├── corridor/                    # Reference Domain: Diaspora Mentors, Bio, Skill Similarity Engine + tests
│       ├── welfare/                     # Stipend State Machine, Redis Idempotency, M-Pesa B2C Celery + Beat + HMAC
│       ├── exit_workflow/               # Early Exit, Dismissal Defense, 4-Way Clearance, Exit Letters
│       ├── grievances/                  # Confidential Reporting, Escalation SLA, Post-Interaction Pulse
│       └── ussd_gateway/                # Stateless *384* USSD handler + Redis session store
│
└── frontend/                            # REACT + TYPESCRIPT + TAILWIND PWA
    ├── Makefile                         # dev, build, test, lint, codegen-api
    ├── package.json                     # React 19, TypeScript, Vite, TanStack Query, Zod, Vitest, Playwright
    ├── tsconfig.json & vite.config.ts   # Strict TS & Vite + Tailwind v4 configuration
    ├── .env.example                     # Public build-time vars ONLY (VITE_API_BASE_URL)
    ├── tests/frontend_core.test.ts      # Runnable RBAC, idempotency, and brand palette verification tests
    └── src/
        ├── app/                         # App.tsx shell, AuthProvider (401 refresh), OfflineSyncBanner, ErrorBoundary
        ├── design-system/
        │   └── tokens.ts                # Strict 5-color KNITAU palette & similarity badge tokens
        ├── lib/
        │   ├── api/client.ts            # Fetch wrapper: single-flight 401 refresh + X-Request-ID + X-Idempotency-Key
        │   ├── auth/rbac.ts             # Mirror of backend roles & admin sub-roles + route guards
        │   └── offline/
        │       ├── idempotency.ts       # Client UUID key generator & queued action payload builder
        │       └── indexedDbQueue.ts    # Real IndexedDB offline store + ordered reconnection flush
        └── features/
            └── corridor/                # Reference feature: OpenAPI types.ts + DiasporaMentorCard.tsx
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
3. **Production Deployment & Operations Checklist**:
   - **Secrets & DPA Compliance**: Load `DJANGO_SECRET_KEY`, DB/PgBouncer, Redis, M-Pesa Daraja keys, Africa's Talking API key, and S3 credentials from a cloud Secret Manager. Store National IDs via salted HMAC (`hash_national_id`) and issue short-lived pre-signed S3 URLs for KYC/Exit Letters.
   - **Database Immutability & Migration Order**: Run `python manage.py migrate identity` first (`AUTH_USER_MODEL = "identity.User"`), then apply all migrations (including `audit/0002_immutable_postgres_rules.py` PostgreSQL triggers).
   - **Automated Backups & DR**: Enable daily PostgreSQL logical snapshots + continuous WAL archiving (`pgBackRest`) to encrypted object storage with monthly restore verification drills (target RPO < 5 min, RTO < 30 min).
   - **Scaling**: Serve via `infra/nginx/nginx.conf` behind TLS 1.3 CDN/Load Balancer; isolate `worker_payments` (`-Q payments_mpesa`) on a dedicated high-reliability node with the 15-minute `reconcile_stale_disbursements` Celery Beat job active.
