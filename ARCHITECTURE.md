# KNITAU × KeNIP — Production System Architecture & Team Engineering Guide

## 1. Architectural Pattern: Modular Monolith + Isolated Async Workers

This codebase uses a **Modular Monolith** on **Django 5 + PostgreSQL 16 + Redis + Celery**, paired with an **OpenAPI Single Source of Truth (SSOT)** feeding a **React + TypeScript PWA** frontend.

Why this topology scales reliably without microservices failure modes:
- **ACID Financial Integrity**: Stipends, per-diem claims, PPE reimbursements, Exit Clearances, and Audit Logs commit inside single PostgreSQL transactions (`@transaction.atomic`) — zero distributed saga bugs.
- **Traffic & Blast-Radius Isolation**:
  - `web_api` (Gunicorn) serves fast REST calls (`< 200ms`).
  - `worker_payments` processes **only** `payments_mpesa` tasks at controlled concurrency so bulk SMS or PDF generation never stalls M-Pesa B2C disbursements.
  - `worker_default` handles `notifications`, `matching`, and `exports`.
  - `pgbouncer` multiplexes up to 1,000 concurrent client/worker sessions into a safe PostgreSQL connection pool.
  - `PrimaryReplicaRouter` splits analytics/reporting reads onto a PostgreSQL read replica while keeping mutations on `default` (primary).
- **Zero-Drift API Contract (SSOT)**: `drf-spectacular` generates `/api/schema/` directly from Django serializers; the React frontend generates typed TypeScript clients/hooks from that schema.

---

## 2. Repository Structure & File Responsibilities

```text
├── ARCHITECTURE.md                  # This team architecture & onboarding handbook
├── docker-compose.yml               # Local/staging stack: PG16, PgBouncer, Redis, MinIO, API, isolated Celery workers
├── index.html                       # Interactive KNITAU x KeNIP frontend prototype (current preview)
└── backend/
    ├── Dockerfile                   # Non-root Python 3.12 production container
    ├── Makefile                     # Standard dev commands (test, lint, contracts, schema, migrate, run)
    ├── pyproject.toml               # Dependencies, Ruff, Pytest, and import-linter boundary contracts
    ├── .env.example                 # Required server-side environment variable placeholders (never commit real secrets)
    ├── manage.py                    # Django CLI entrypoint
    ├── config/
    │   ├── __init__.py              # Loads Celery app on Django boot
    │   ├── celery.py                # Isolated queues: payments_mpesa, notifications, matching, exports, default
    │   ├── urls.py                  # /healthz/, /api/schema/, /api/docs/, and /api/v1/* routes
    │   ├── wsgi.py                  # Production WSGI entrypoint
    │   └── settings/
    │       ├── base.py              # Shared settings: Fail-closed SECRET_KEY, PgBouncer, DRF, JWT, OpenAPI SSOT
    │       ├── local.py             # Developer local overrides (DEBUG=True)
    │       └── production.py        # Strict TLS, HSTS, secure cookies, reverse-proxy headers
    └── apps/
        ├── common/                  # Shared Kernel (safe for all domain modules to import)
        │   ├── models.py            # UUIDTimeStampedModel & SoftDeleteModel (no destructive hard deletes)
        │   ├── permissions.py       # Central KNITAU RBAC: intern, employer, institution, admin + sub-roles
        │   ├── exceptions.py        # Unified error JSON envelope & DomainError
        │   ├── idempotency.py       # Redis atomic lock preventing duplicate M-Pesa payouts or offline sync replays
        │   ├── events.py            # In-process DomainEvent bus decoupling modules cleanly
        │   └── db_router.py         # PrimaryReplicaRouter for read-scaling
        ├── audit/                   # Compliance & Non-Repudiation Ledger
        │   ├── models.py            # Append-only SHA-256 hash-chained AuditLog (blocks update & delete)
        │   └── services.py          # record_audit_event() with PII/PIN/token redaction
        ├── corridor/                # Reference Domain Module (Modules 1-4 blueprint)
        │   ├── models.py            # DiasporaMentor (with bio & expertise_tags) + MentorMatchRequest
        │   ├── selectors.py         # Pure read queries + Career Passport <-> Mentor Tag similarity engine
        │   ├── services.py          # Transactional write workflows + audit + domain events
        │   ├── api/
        │   │   ├── serializers.py   # OpenAPI request/response contracts
        │   │   ├── views.py         # Thin RBAC-protected views (no business logic)
        │   │   └── urls.py          # /api/v1/corridor/*
        │   └── tests/
        │       └── test_matching.py # Unit + transactional DB & audit verification tests
        ├── identity/                # Module: Auth, KYC, Institutions, Employers, Career Passport
        ├── welfare/                 # Module: Stipends, Per-Diem, PPE Claims, M-Pesa Payouts
        ├── exit_workflow/           # Module: Early Exit, Dismissal, 4-Way Clearance, Exit Letters
        ├── grievances/              # Module: Anonymous Reporting, Escalation, Post-Interaction Pulse
        └── ussd_gateway/            # Edge Adapter: Stateless USSD session handler (*384*...)
```

---

## 3. Golden Engineering Rules (Backend & Frontend)

### Backend Rules (Enforced by CI)
1. **No Cross-Module Model Imports**: A module (e.g., `welfare`) must **never** import `models.py` from another module (e.g., `corridor` or `identity`). Enforce automatically via `lint-imports` (`pyproject.toml`).
2. **Selectors vs. Services Separation**:
   - **`selectors.py`**: Read-only queries, filtering, and scoring (e.g., `rank_mentors_for_passport_skills`).
   - **`services.py`**: All writes wrapped in `@transaction.atomic`, raising `DomainError`, writing to `record_audit_event(...)`, and emitting `publish_event(...)`.
   - **`api/views.py`**: Thin controllers only — validate input with Serializer, verify `HasKnitauRole`, call a single Selector or Service, return response.
3. **Idempotency on Financial & Offline Endpoints**: Every M-Pesa trigger or offline-sync mutation must pass through `acquire_idempotency_lock(...)` using `X-Idempotency-Key`.
4. **Immutable Audit Trail**: Never delete financial, clearance, or grievance records; inherit `SoftDeleteModel` and log state transitions via `record_audit_event(...)`.

### Frontend Rules (React + TypeScript)
1. **Consume OpenAPI Types Only**: Run the schema export (`make schema`) and generate TypeScript types (`openapi-typescript`) rather than hand-writing API interfaces.
2. **Keep Secrets Off the Client**: Only short-lived JWT access tokens in memory / secure refresh flows; M-Pesa, USSD, S3, and DB secrets live strictly on the backend.
3. **Offline Queue Safety**: Attach a client-generated UUID (`X-Idempotency-Key`) to queued offline forms (e.g., PPE receipts, grievances, field check-ins) before syncing on reconnect.

---

## 4. Quick Verification Commands

Run inside `backend/`:

```bash
# 1. Enforce module boundaries (Modular Monolith guardrails)
make contracts

# 2. Run unit + DB + audit ledger test suite
make test

# 3. Static analysis, type check, and security scan
make lint

# 4. Export OpenAPI Single Source of Truth schema for Frontend
make schema
```

Run the full containerized stack from project root (after copying `backend/.env.example` to `backend/.env` and filling secrets):

```bash
docker compose up --build
```
