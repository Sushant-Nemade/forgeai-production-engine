# ForgeAI — Autonomous Vibe-to-Production Micro-SaaS Engine

ForgeAI is a production-oriented Python control plane that converts a constrained product brief into a typed API contract, endpoint plan, security-gated execution result, and observable runtime. The repository demonstrates async orchestration, explicit state transitions, fail-closed QA, PostgreSQL persistence, JWT authentication, migration hooks, reverse-proxy hardening, and Prometheus/Grafana telemetry.

## System Architecture

```text
                         ┌──────────────────────┐
                         │   Product Brief/API   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      RECEIVED        │
                         └──────────┬───────────┘
                                    │ PM Agent
                                    ▼
                         ┌──────────────────────┐
                         │   SCHEMA_MAPPED      │
                         │ Pydantic contract +  │
                         │ relational mapping   │
                         └──────────┬───────────┘
                                    │ Developer Agent
                                    ▼
                         ┌──────────────────────┐
                         │   API_GENERATED      │
                         │ CRUD endpoint plan + │
                         │ JWT boundary         │
                         └──────────┬───────────┘
                                    │ QA Agent
                                    ▼
                         ┌──────────────────────┐
                         │     QA_SCANNED       │◄─────────┐
                         └──────────┬───────────┘          │
                                    │                      │
                        PASS ──────┴────── FAIL            │
                          │                    │            │
                          ▼                    ▼            │
                 ┌─────────────────┐   ┌──────────────┐   │
                 │   DEPLOYABLE    │   │ REMEDIATING  │───┘
                 └────────┬────────┘   └──────────────┘
                          │
                          ▼
          ┌──────────────────────────────────────┐
          │ FastAPI → Nginx → PostgreSQL        │
          │ Prometheus → Grafana                 │
          └──────────────────────────────────────┘

        Any unrecoverable exception ───────────► FAILED
```

## Repository Layout

```text
core_engine/        async PM / Developer / QA agents and state machine
dashboard/          FastAPI control plane, auth, persistence and migrations
monitoring/         Prometheus scrape config + Grafana dashboard
nginx/              hardened reverse proxy
tests/              deterministic async/unit API tests
.github/workflows/  GitHub Actions validation
Dockerfile          non-root production container image
docker-compose.yml  PostgreSQL + app + Nginx + observability stack
```

## Cloud Installation

### 1. Configure secrets

Create a deployment secret set rather than committing credentials:

```bash
export POSTGRES_PASSWORD="<random-32+-character-secret>"
export JWT_SECRET_KEY="<random-32+-character-secret>"
export GRAFANA_ADMIN_PASSWORD="<random-24+-character-secret>"
export DEMO_PASSWORD_HASH="<bcrypt-hash>"
```

`JWT_SECRET_KEY` must be high entropy and rotated through your secret manager. Never reuse the example CI values in production. `DATABASE_URL` is assembled from the PostgreSQL variables in Compose. For managed PostgreSQL, set `DATABASE_URL` directly in the deployment environment and remove the local `db` service.

### 2. Start the stack

```bash
docker compose up -d --build
docker compose ps
```

The application container runs `alembic upgrade head` before Uvicorn starts. This makes schema migration an explicit deployment gate instead of an implicit application side effect.

### 3. Validate

```bash
curl http://localhost/health
curl http://localhost/ready
```

FastAPI OpenAPI is available at `/docs` behind the reverse proxy. Prometheus is exposed on `:9090` and Grafana on `:3000` for the default Compose profile.

## Production Configuration & Security

| Variable | Purpose | Production guidance |
|---|---|---|
| `POSTGRES_PASSWORD` | database credential | secret-manager only; rotate periodically |
| `POSTGRES_USER` | database principal | use a least-privileged service user |
| `POSTGRES_DB` | database name | isolate per environment |
| `DATABASE_URL` | external PostgreSQL connection | prefer TLS (`sslmode=require`) with managed DBs |
| `JWT_SECRET_KEY` | JWT signing key | 256-bit+ random secret; rotate with token policy |
| `JWT_ACCESS_MINUTES` | access-token lifetime | keep short; use refresh-token infrastructure for long sessions |
| `DEMO_USER` | demonstration principal | replace with a real identity provider in production |
| `DEMO_PASSWORD_HASH` | demonstration password hash | bcrypt hash only; never store plaintext |
| `GRAFANA_ADMIN_PASSWORD` | Grafana bootstrap credential | rotate after bootstrap and protect Grafana ingress |

The reference Nginx layer disables server tokens, caps request bodies, applies security headers, and rate-limits `/api/`. Production TLS should terminate at an ingress/load balancer and forward only trusted proxy headers. PostgreSQL is isolated on a private Docker network and is not published to the host.

## API Contract

`POST /api/auth/token` accepts JSON credentials and returns a short-lived JWT. Authenticated factory requests use `Authorization: Bearer <token>`.

`POST /api/runs` accepts a product brief such as:

```text
resource: invoice; fields: customer_id(string), amount(number), paid(boolean)
```

The PM agent produces a validated schema; the Developer agent produces a CRUD endpoint plan; the QA agent scans Python source and the orchestrator transitions the run through an explicit state machine.

## Database & Migration Hooks

Alembic is wired through `alembic.ini` and `dashboard/migrations/env.py`. The container entrypoint executes `alembic upgrade head`, while migration files remain reviewable and reversible. The initial schema stores factory runs, state, structured artifacts, and timestamps in PostgreSQL JSONB for queryable execution metadata.

## CI/CD Validation

`.github/workflows/production-test.yml` installs pinned dependencies, runs pytest, validates the Compose model, builds the production image, starts PostgreSQL, inspects service health, and tears the stack down. The workflow uses read-only repository permissions for pull-request and main-branch validation.

## Advanced AI Engineering Patterns Implemented

### Async multi-agent loops

The orchestrator is an async state machine rather than a collection of synchronous callbacks. Specialist agents expose `async run(...)` contracts, allowing I/O-bound model/tool adapters to be introduced without redesigning the control plane. State transitions are persisted as an ordered trace so an execution can be audited independently of the final artifact.

### Structured data parsing

The Product Manager agent converts free-form intent into Pydantic models with regex-constrained identifiers, bounded field counts, primitive type enums, and explicit authentication semantics. This creates a typed intermediate representation that downstream agents can consume deterministically instead of passing fragile natural-language prompts between stages.

### Auto-remediation execution loops

QA returns structured findings rather than a boolean-only gate. The orchestrator permits bounded remediation cycles and then fails closed when the maximum cycle count is exhausted. This pattern supports future patch-generating agents while preserving a critical invariant: security findings cannot silently disappear merely because an autonomous loop ran out of time.

### OWASP-aligned security engineering

The QA agent maps deterministic AST checks to OWASP-style categories including injection/dynamic execution, unsafe components/serialization, and source-integrity failures. The runtime additionally uses JWT verification, bcrypt password hashing, rate limiting, request-size limits, secure response headers, non-root containers, private database networking, and short-lived access tokens.

### Cloud-native observability

FastAPI instrumentation emits Prometheus metrics; a versioned Grafana dashboard captures request rate and latency. The deployment separates application, data, ingress, and telemetry concerns into independently restartable containers while retaining a single reproducible Compose definition for local/CI parity.

## Engineering Trade-offs

The included developer agent generates an endpoint plan rather than arbitrary source-code mutation. That is intentional: unrestricted autonomous code execution is difficult to secure and reproduce. The repository establishes a deterministic intermediate representation and security gate that can safely wrap a model-backed code generator later.

For a true multi-tenant SaaS deployment, replace the demonstration credential endpoint with OIDC, add tenant-scoped authorization, use a managed PostgreSQL service, store secrets in a cloud secret manager, add distributed tracing, and place the application behind a managed TLS ingress/WAF.

## License

MIT
