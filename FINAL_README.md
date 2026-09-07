# HawkerCredit Quantum — FINAL merged edition

This is the merged, audited result of two candidate submissions
(`HAWKERCREDIT_ULTIMATE_EDITION.zip` and `HawkerCredit-Ultimate-Edition.zip`),
produced by a file-by-file comparison rather than a blind merge. The two
projects were ~90% byte-identical (76 of 84 shared files were exact
matches); only 18 files genuinely differed, plus a handful of files unique
to one side. Every difference was read, and the better version — or a
hybrid of both — was kept.

---

## 1. What was merged, and why

| Area | Decision | Reason |
|---|---|---|
| `backend/app/api/v1/consent.py` | Kept version A | Version B auto-created a `granted=True` consent record the first time a vendor's consent page was **viewed**. That is a direct violation of "consent must never be granted merely by viewing a page." Confirmed by cross-checking `auth.py`'s registration flow, which already seeds explicit consent records at signup with a code comment specifically warning against lazy view-time creation — B's change contradicted the codebase's own documented design. |
| `frontend/app/vendor/credit-profile/page.tsx` | Kept version A | Version B removed the `<Suspense>` boundary around `useSearchParams()`. Next.js requires that boundary for this exact pattern during static export — its absence breaks `next build` in production. B also deleted the working inline loan-approve/reject panel; A keeps it. |
| `frontend/lib/api.ts` | Kept version A's `API_BASE` fallback (`/api/v1`, proxied via `next.config.js`) | Version B hardcoded `http://localhost:8000/api/v1` as the fallback. If `NEXT_PUBLIC_API_URL` isn't set on Vercel, B's version would silently call `localhost` from the browser in production and fail. |
| `backend/app/quantum/qaoa_solver.py` | Took version B | B computes the QUBO→Ising `h`/`J` coefficients **once**, before the (repeatedly-called, ~10–15x per optimization) circuit-building closure. A recomputed them on every call — same math, worse performance. Both versions use the identical, mathematically correct conversion formula (see §4). |
| `backend/app/main.py` | Took version B | Adds a `GET /` route returning basic service status, so stray platform/UptimeRobot hits against the bare root don't 404. |
| `render.yaml` | Took version B | B's blueprint provisions an actual managed Postgres `databases:` block and wires `DATABASE_URL` via `fromDatabase`, so Render can deploy the whole stack without a manual DB-URL paste. A left `DATABASE_URL` as `sync: false` (manual entry required). |
| `backend/.env.example`, `frontend/.env.example` | Took version B | Substantially more complete inline documentation of every variable, safe local-dev defaults, and explicit guidance for Render/Vercel. |
| `frontend/app/lender/benchmark/page.tsx`, `.../portfolio/optimizer/page.tsx`, `.../demo/page.tsx` | Took version B | B updates these pages to read the canonical `business_objective` field (expected monetary return) for the quantum-vs-classical comparison, instead of the raw QUBO penalty energy `objective_value`. This matches the requirement that both methods be compared on the same business metric, not a mix of full-QUBO energy vs. a narrower baseline. |
| `backend/app/demo_seed.py` | Kept version A | A caches the bcrypt hash of each of the three shared demo passwords once instead of re-hashing per account, cutting cold-start seeding time significantly (bcrypt is deliberately slow; this has no effect on real signups, which always hash at full cost with a random salt). |
| `backend/app/quantum/qubo_builder.py` | Hybrid | Kept A's hard 18-qubit safety ceiling (Aer statevector simulation cost grows sharply with qubit count; a single QAOA call executes the circuit ~10–15 times during optimization). Adopted B's higher-precision default slack-bit widths and `max_concentration_categories=4` — the ceiling automatically pares these back down for larger candidate pools, so this is strictly additive precision, not a new risk. |
| `max_risk_tolerance` default (0.45 → 0.25) | Took B's value, applied consistently | B changed this in every layer (DTO, QUBO builder, classical benchmark, quantum API, frontend). A more conservative default risk ceiling is more defensible for a lending product; keeping it consistent front-to-back avoids the constraint the QUBO optimizes against silently disagreeing with what the UI displays. |
| `package.json`, `vercel.json` (repo root) | Kept from A (B had none) | Required for a Vercel monorepo build (`cd frontend && npm ci && npm run build`). Without these, Vercel has no instruction for where the Next.js app actually lives. |
| `frontend/app/lender/review/page.tsx`, `.../lender/layout.tsx` | Kept from A (B had neither) | A dedicated, working 246-line underwriting queue page with real API calls — a materially larger feature than anything B offered in its place. |
| `frontend/app/voice-demo/page.tsx`, `frontend/components/HawkerCreditVoiceAlerts.tsx` | Brought in from B (A had neither) | Additive only. Uses the browser's native Web Speech API; correctly describes a connected Bluetooth speaker as just an audio output route, not "quantum hardware" or a special backend. Landing page now links to it.

Everything else (all backend AI/scoring/OCR/audit code, all database models, all authentication/authorization logic, the classical validator, the vast majority of frontend pages) was **byte-identical** between the two submissions, so there was nothing to choose — it was carried over unmodified.

---

## 2. Architecture

```
frontend/  (Next.js 14, App Router)
  app/            — pages, one per route (vendor, lender, admin, auth, demo)
  components/     — shared UI + HawkerCreditVoiceAlerts
  lib/api.ts      — single fetch client; every backend call goes through here
  lib/auth.ts     — client-side auth/session hooks (useRequireAuth)
  next.config.js  — rewrites /api/v1/* to BACKEND_URL server-side

backend/  (FastAPI + SQLAlchemy)
  app/api/v1/     — one router per resource (auth, vendors, loans, quantum, ...)
  app/core/       — config, JWT/security, rate limiting
  app/db/         — SQLAlchemy session/engine setup
  app/models/     — schema.py: User, Vendor, Loan, ConsentRecord, AuditLog, ...
  app/ai/         — scoring model, SHAP explainability, forecasting, OCR, NLP
  app/quantum/    — qubo_builder, qaoa_solver, classical_benchmark, classical_validator, portfolio_metrics
  app/schemas/    — Pydantic DTOs (single source of truth for API shapes)
  app/demo_seed.py — idempotent synthetic-data seeding (100 vendors, 10 lenders, 1 admin)
  app/main.py     — app assembly, CORS, health/root routes, startup seeding
  tests/          — pytest suite (auth, isolation, consent, quantum math, ...)
```

**Single source of truth per domain:** authentication and RBAC live only in
`app/core/security.py` (`get_current_user`, `require_roles`,
`verify_vendor_access`); every vendor-scoped router (`consent`, `credit`,
`expenses`, `inventory`, `loans`, `transactions`, `vendors`, `ai`) depends on
`verify_vendor_access`, which checks `Vendor.user_id == current_user.id` —
not a client-supplied ID — so a vendor cannot read another vendor's data by
editing a URL. Lenders/Admins are exempted from that check but every
lender-facing route is separately gated with `require_roles(["LENDER",
"ADMIN"])`, and admin-only routes (`/admin`, `/audit-logs`) require
`require_roles(["ADMIN"])`. The frontend's `useRequireAuth([...])` gates
mirror this 1:1 (verified route-by-route — see §5).

The quantum/classical portfolio pipeline has one canonical business metric:
`portfolio_metrics.business_objective()`, computed identically by both the
QAOA path (`qaoa_solver.py`) and the classical path
(`classical_benchmark.py`), and surfaced to the frontend as
`business_objective` alongside (not instead of) the raw QUBO energy
`objective_value`. The benchmark and optimizer pages display both, labeled,
so a viewer can see the canonical comparison and the underlying penalty
energy without conflating the two.

---

## 3. Deployment

### Vercel (frontend)
1. Import the repo into Vercel. Root `vercel.json` + `package.json` already
   tell Vercel this is a monorepo — no manual "root directory" override
   needed beyond what's in those two files.
2. Set environment variables (Project Settings → Environment Variables, for
   **both** Production and Preview):
   - `NEXT_PUBLIC_API_URL` = `https://<your-render-service>.onrender.com/api/v1`
   - `BACKEND_URL` = `https://<your-render-service>.onrender.com`
3. Deploy. `next.config.js` rewrites `/api/v1/*` to `BACKEND_URL` server-side,
   so the browser can also just call the relative path `/api/v1/...` if
   `NEXT_PUBLIC_API_URL` is left unset — but setting it explicitly is safer
   and is what's documented here.

### Render (backend)
1. New → Blueprint, point at this repo. `render.yaml` at the repo root
   defines both the web service and a managed free-tier Postgres database,
   and wires `DATABASE_URL` between them automatically.
2. Render auto-generates `JWT_SECRET` and `STAFF_BOOTSTRAP_SECRET` per the
   blueprint (`generateValue: true`). **Save the bootstrap secret** — you
   need it once, to create your first real ADMIN/LENDER account via
   `POST /api/v1/auth/staff/register` with header `X-Bootstrap-Secret`.
3. After the frontend is live on Vercel, update `CORS_ORIGINS` on the
   Render service (Environment tab) to your real Vercel URL(s),
   comma-separated. It defaults to `http://localhost:3000` in the blueprint.
4. `DEMO_SEED_ON_STARTUP=true` by default — on first boot with empty
   tables, the backend seeds ~100 synthetic vendors, 10 lenders, and 1
   admin. It is additive/idempotent: re-running it (e.g. on redeploy) does
   not duplicate or corrupt existing rows (`_ensure_user` and vendor-seed
   logic check for existing records first). Set it to `false` for a clean,
   non-demo production deployment.

### PostgreSQL
Handled by Render's managed database when using the blueprint (see above).
For a self-managed Postgres instance instead, set `DATABASE_URL` directly
to your connection string — SQLAlchemy/psycopg2 handle Postgres the same
way regardless of who's hosting it. Local development defaults to SQLite
(`sqlite:///./hawkercredit.db`) if `DATABASE_URL` is unset, so no local
Postgres setup is required to run the app locally.

### UptimeRobot
Point a monitor at `GET https://<your-render-service>.onrender.com/health`.
It returns HTTP 200 immediately (`{"status": "healthy", ...}`) and does
**not** touch the database or run any quantum computation, so it stays fast
and cheap to poll. The new `GET /` root route also returns 200, as a
fallback for anything that probes the bare domain instead of `/health`.

---

## 4. Required environment variables

**Backend** (`backend/.env.example` has full inline docs):
| Variable | Required? | Notes |
|---|---|---|
| `JWT_SECRET` | Required in production | Generate: `openssl rand -hex 32`. Startup **fails loudly** if unset and `ENVIRONMENT=production` — no silent fallback in prod. |
| `ENVIRONMENT` | Recommended | `production` on Render; `development` locally. |
| `STAFF_BOOTSTRAP_SECRET` | Required for first admin | One-time secret to bootstrap the first LENDER/ADMIN account. |
| `DATABASE_URL` | Required in production | Postgres connection string; defaults to local SQLite otherwise. |
| `CORS_ORIGINS` | Required in production | Comma-separated list of allowed frontend origins. |
| `PORT` | Set by Render automatically | Dockerfile CMD reads it, defaults to 10000. |
| `DEMO_SEED_ON_STARTUP` | Optional | `true`/`false`. Never wipes existing data. |

**Frontend** (`frontend/.env.example`):
| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_API_URL` | Full base URL incl. `/api/v1`, called directly by the browser. |
| `BACKEND_URL` | Base URL (no `/api/v1`) used by the server-side rewrite in `next.config.js`. |

Never commit a filled-in `.env` — both example files are templates only.

---

## 5. Demo credentials

Created automatically by `demo_seed.py` when `DEMO_SEED_ON_STARTUP=true`
(the default) and the relevant tables are empty:

| Role | Email | Password |
|---|---|---|
| Vendor | `vendor@hawkercredit.com` | `vendor123` |
| Lender | `lender@hawkercredit.com` | `lender123` |
| Admin | `admin@hawkercredit.com` | `admin123` |

Plus ~9 additional lender accounts (`lender2@hawkercredit.com` ...
`lender10@hawkercredit.com`, same password) and ~99 additional vendor
accounts, for a realistic-sized demo pool. **These are throwaway,
publicly-documented demo credentials, not real security boundaries** — the
same password is intentionally shared across every demo account of a given
role, as noted directly in `demo_seed.py`.

To create a real (non-demo) ADMIN/LENDER account, call
`POST /api/v1/auth/staff/register` with header `X-Bootstrap-Secret` set to
your `STAFF_BOOTSTRAP_SECRET` value.

---

## 6. Running locally

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit as needed; SQLite works out of the box
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env.local   # defaults point at localhost:8000
npm run dev
```
Visit `http://localhost:3000`.

---

## 7. Running tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```
`tests/test_backend.py` (452 lines, 22 test functions) covers: password
hashing/salting, authenticated-route enforcement, vendor data isolation
across two different vendors, role gating, consent revoke/grant effects on
AI features, consent ownership enforcement, QUBO/QAOA circuit construction,
QAOA parameter optimization (not hardcoded), classical-benchmark
exactness, QUBO/QAOA/classical agreement on a small feasible problem,
classical-validator constraint and concentration checks, and a full
auth register→login roundtrip.

**Environment limitation, stated plainly:** the sandbox this merge was
performed in has no network access, so `pip install` / `npm install` could
not fetch FastAPI, SQLAlchemy, Qiskit, or any other third-party package —
`pytest` and `next build` could not actually be executed here. What
**was** verified in this environment, without those dependencies:
- Every backend `.py` file passes `python -m py_compile` (no syntax errors).
- Every frontend `.ts`/`.tsx` file passes a `tsc --noEmit` parse check
  filtered to genuine syntax errors (TS1xxx) — zero found. (Errors from
  missing `node_modules` type declarations were expected and excluded.)
- Every `@/`-aliased import in the frontend resolves to a real file on
  disk — no stale imports.
- Every `api.<method>()` call used in a page has a matching definition in
  `lib/api.ts`.
- Frontend route-guard roles (`useRequireAuth([...])`) were checked
  against backend route-guard roles (`require_roles([...])`) for every
  protected page/router pair — they match.
- **The QUBO→Ising conversion was independently re-implemented and
  numerically verified** (see §8) — this is the one piece of core
  application logic that was actually executed and checked against real
  output in this session, using only `numpy` (which is available). The
  existing `test_qubo_qaoa_and_classical_agree_on_small_feasible_problem`
  in the repo's own pytest suite asserts the same property; it could not
  be run here (needs `qiskit`), but the standalone check above corroborates
  it independently.

Run `pytest` and `npm run build` yourself before deploying to get full
coverage this environment couldn't provide.

---

## 8. Quantum optimizer explanation

**What it is:** a QAOA (Quantum Approximate Optimization Algorithm)
prototype for lender portfolio allocation, run on Qiskit/Aer's classical
simulator (not real quantum hardware). It formulates vendor selection
subject to capital, risk, and category-concentration constraints as a QUBO
(`x^T Q x`), converts that QUBO into an Ising Hamiltonian, and runs a
parameterized quantum circuit to sample candidate solutions.

**QUBO → Ising conversion, verified.** For binary QUBO variables
`x ∈ {0,1}^N`, with `x_i = (1 - Z_i)/2`, the general (not-necessarily-
symmetric) conversion used in `qaoa_solver.py` is:

```
h_i  = -Q_ii/2 - (1/4) * Σ_{j≠i} (Q_ij + Q_ji)
J_ij =  (1/4) * (Q_ij + Q_ji)
```

which reduces to the standard symmetric-Q formula (`h_i = -Q_ii/2 -
(1/2)Σ_{j≠i}Q_ij`, `J_ij = Q_ij/2`) whenever `Q_ij = Q_ji`. This was
independently re-derived and numerically checked in this session: a real
QUBO was built from the merged project's own `qubo_builder.py` (16
qubits, capital + risk + concentration constraints), the Ising `h`/`J`
were computed with the formula above, and the QUBO energy `x^T Q x` was
compared against the Ising energy (plus a constant offset, which
contributes only a global phase and is expected to differ) across 200
random bitstrings. **Maximum discrepancy: ~1×10⁻¹³** — floating-point
noise, i.e. exact agreement.

**Reliability:** a hard 18-total-qubit ceiling in `qubo_builder.py`
prevents runaway Aer simulation time (empirically ~0.05s at 16 qubits vs.
~24s at 24 qubits, and a single optimization call executes the circuit
10–15 times). In practice the candidate-selection pipeline in
`api/v1/quantum.py` already caps the QAOA input to 10 consent-filtered
vendors drawn from a larger eligible pool (documented below), keeping
total qubit count well inside that ceiling. If Qiskit/Aer is unavailable
at runtime, the code degrades to the classical benchmark path rather than
crashing (see `classical_benchmark.py` and the try/except around Aer usage
in `qaoa_solver.py`).

**Every QAOA-produced portfolio is re-validated classically**
(`classical_validator.py`) against the *true* capital, risk, and
per-category concentration constraints — including categories that were
excluded from the QUBO's own penalty terms due to the qubit ceiling.
Infeasible results are detected and repaired or rejected; an invalid
portfolio is never displayed as valid.

**Honest wording used throughout the UI and API:** "Quantum optimization
prototype using QAOA, benchmarked against a classical optimizer." No claim
of quantum advantage or speedup is made anywhere in the merged codebase.

---

## 9. Classical vs. quantum comparison

Both paths are scored on the same canonical objective —
`portfolio_metrics.business_objective()` (expected monetary return) — not
a mix of raw QUBO energy vs. a differently-scoped classical baseline. The
benchmark and optimizer pages display, for both methods: selected vendors,
allocated capital, `business_objective`, the raw QUBO `objective_value`
(labeled separately, for transparency), runtime, and post-validation
feasibility. For small candidate pools the classical path uses exact
enumeration; for larger ones it uses a heuristic — see
`classical_benchmark.py`.

---

## 10. Known limitations

- **AI credit scoring uses synthetic demo data**, not real vendor banking
  records. This is disclosed in the model governance info the API
  returns and should be disclosed to any audience seeing the demo.
- **Audit logs are an append-only application-level log**, not a
  cryptographically immutable ledger — described that way throughout, not
  as "immutable."
- **QAOA runs on a classical simulator (Aer)**, not physical quantum
  hardware, and the qubit ceiling means large vendor pools are pre-filtered
  to a smaller candidate subset before QAOA runs (100-ish eligible pool →
  10-vendor QAOA subproblem, matching the eligibility → ranking → QUBO
  pipeline pattern).
- **OCR requires the Tesseract system binary**, installed in the provided
  Dockerfile. If it's ever missing at runtime, `ocr_receipt.py` falls back
  to a deterministic demo parser rather than failing the request.
- **Voice alerts use the browser's Web Speech API only** — there is no
  dedicated Bluetooth backend; a connected Bluetooth speaker is just the
  browser's normal audio output device.
- **This merge's test/build verification was static only** (see §7) — no
  network access meant `pytest`, `next build`, and a live Postgres/Qiskit
  run could not be executed in this session. Run them before deploying.

## 11. Honest claims vs. non-claims

**Claims made by this project:** a working, internally-consistent
prototype demonstrating AI-based alternative credit scoring with
explainability (SHAP), a QAOA-based portfolio optimizer benchmarked
honestly against a classical baseline on a shared business objective, role-
based access control with verified vendor data isolation, explicit opt-in
consent gating of AI features, and a deployment path to Vercel + Render +
Postgres with a health endpoint suitable for uptime monitoring.

**Claims NOT made:** no quantum advantage or speedup; no claim that the
credit model reflects real-world repayment accuracy; no claim of
cryptographic audit-log immutability; no claim that Bluetooth is a
quantum-hardware interface; no claim that every test in the repo's pytest
suite was executed in this session (see §7 for exactly what was and
wasn't verified here, and why).
