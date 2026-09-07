# HawkerCredit Quantum — Final Release

## 1. What was merged

The two supplied editions were structurally very similar. The final release uses the stronger security/deployment-oriented backend as the canonical base and selectively restores the useful voice-demo assets from the other edition. Duplicate implementations were not retained.

Key retained capabilities: FastAPI + PostgreSQL/SQLAlchemy, JWT/RBAC, vendor isolation, consent, synthetic 100-vendor seeding, persisted Random Forest scoring, SHAP explainability, OCR/voice input, QUBO/QAOA, classical benchmark, post-validation/repair, lender underwriting, audit logging, Next.js dashboards, Vercel/Render configuration.

## 2. Major fixes

- Removed unauthenticated fallback identity behavior; protected APIs require JWTs.
- Public registration is vendor-only; lender/admin creation is bootstrap/admin protected.
- Added bounded Pydantic validation for loan and optimizer inputs.
- Fixed loan-request audit attribution to the authenticated user.
- Added session cleanup/redirect on frontend HTTP 401 responses.
- Made synthetic seeding deterministic and idempotent.
- Canonicalized quantum/classical business comparison around expected monetary return.
- Preserved mathematically correct QUBO → Ising conversion for symmetric and general Q matrices.
- Added deterministic 100-vendor → consent-filtered → ranked/diversified → 10-vendor QAOA candidate selection.
- Removed silent category omission from the QUBO builder: the QUBO now rejects a candidate set whose category count exceeds its configured concentration representation.
- Reused persisted optimization results on the benchmark screen when all relevant constraints match, avoiding unnecessary second QAOA runs.
- Added Alembic migration infrastructure and startup migration execution.
- Added the missing voice-demo UI from the companion edition.
- Kept `/health` lightweight and independent of database/quantum execution.
- Removed development/backup artifacts from the final package.

## 3. Architecture

`Next.js (Vercel)` → `FastAPI (Render)` → `PostgreSQL`

Backend layers:
- `api/v1`: authentication, vendors, transactions, expenses, inventory, loans, AI, credit, consent, audit, admin, quantum, portfolio.
- `ai`: deterministic feature engineering, persisted Random Forest, SHAP explanations, anomaly detection, forecasting, OCR, voice parsing.
- `quantum`: QUBO builder, QAOA/Aer solver, classical exact/heuristic benchmark, feasibility validator, portfolio metrics.
- `models/schema.py`: canonical SQLAlchemy data model.
- `schemas/dto.py`: canonical API request/response validation.

## 4. Vercel deployment

1. Import the repository into Vercel.
2. Set the project root to the repository root, or use the included `vercel.json`.
3. Set `BACKEND_URL` to the Render backend origin, for example `https://<service>.onrender.com`.
4. Optionally set `NEXT_PUBLIC_API_URL` to `https://<service>.onrender.com/api/v1`. Leaving it empty uses the Vercel `/api/v1` rewrite.
5. Build with `npm run build`.
6. After deployment, add the final Vercel origin to Render `CORS_ORIGINS`.

## 5. Render deployment

1. Create a Render Web Service using Docker.
2. Docker context: `backend/`; Dockerfile: `backend/Dockerfile`.
3. Set `ENVIRONMENT=production`.
4. Provide `DATABASE_URL`, `CORS_ORIGINS`, `JWT_SECRET`, and `STAFF_BOOTSTRAP_SECRET`.
5. Set `DEMO_SEED_ON_STARTUP=true` for the hackathon demo. Use `false` for a clean non-demo deployment.
6. Render exposes `/health` for health checks.
7. The container runs Alembic to `head` before application initialization. The app also keeps a defensive startup warning rather than crashing solely because migration tooling is temporarily unavailable.

## 6. PostgreSQL

Use any managed PostgreSQL 14+ service. Render Postgres can be used when available; alternatively supply an external PostgreSQL connection string. The backend normalizes legacy `postgres://` URLs.

## 7. UptimeRobot

Create an HTTP monitor for:

`https://<render-service>.onrender.com/health`

Expected status: HTTP 200. The endpoint intentionally performs no quantum computation.

## 8. Environment variables

Backend:
- `ENVIRONMENT`
- `DATABASE_URL`
- `JWT_SECRET`
- `CORS_ORIGINS`
- `STAFF_BOOTSTRAP_SECRET`
- `DEMO_SEED_ON_STARTUP`

Frontend:
- `NEXT_PUBLIC_API_URL` (optional)
- `BACKEND_URL` (used by the Next.js rewrite)

Never commit real secrets. See `backend/.env.example` and `frontend/.env.example`.

## 9. Demo credentials / account creation

When `DEMO_SEED_ON_STARTUP=true`, the deterministic demo seed creates:

- Vendor: `vendor@hawkercredit.com` / `vendor123`
- Lender: `lender@hawkercredit.com` / `lender123`
- Admin: `admin@hawkercredit.com` / `admin123`

These are throwaway hackathon credentials only. Change/remove them for any non-demo deployment. Additional staff accounts require the configured bootstrap secret or an authenticated admin.

## 10. Local run

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set DATABASE_URL/JWT_SECRET/etc. as needed
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

For a local demo, set `DEMO_SEED_ON_STARTUP=true` and use a local PostgreSQL database or the documented development SQLite fallback.

## 11. Tests

Run backend tests with:

```bash
cd backend
pytest -q
```

Run Python compilation with:

```bash
python -m compileall -q app tests
```

Run the frontend production build with:

```bash
cd frontend
npm ci
npm run build
```

In the supplied execution environment, dependency installation was network-blocked, so the complete pytest suite and Next.js production build could not be executed here. Python bytecode compilation and an exhaustive QUBO→Ising mathematical verification were executed successfully. Do not interpret the unexecuted dependency-based suites as passed.

## 12. Quantum optimizer

The platform constructs a constrained QUBO over a bounded lender candidate subproblem. The production/demo flow is:

`100-vendor eligible pool → consent/data-quality eligibility → deterministic ranking/diversification → 10-vendor QAOA candidate subproblem → QUBO → Ising Hamiltonian → QAOA/Aer → measured bitstring → classical feasibility validation → repair/rejection → persisted run`

For `x_i=(1-Z_i)/2`, the implementation uses the general symmetric-equivalent conversion:

- `h_i = -Q_ii/2 - 1/4 * Σ(j≠i)(Q_ij + Q_ji)`
- `J_ij = 1/4 * (Q_ij + Q_ji)`

For a symmetric Q, this is exactly:

- `h_i = -Q_ii/2 - 1/2 * Σ(j≠i)Q_ij`
- `J_ij = Q_ij/2`

The circuit applies `RZ(2γh_i)` and `RZZ(2γJ_ij)`; it does not treat raw QUBO entries as gate angles.

Qiskit/Aer is used when available. If quantum execution fails, the system falls back to a deterministic classical benchmark and explicitly marks the run as a classical fallback.

## 13. Classical vs quantum

Both are evaluated with the same lender-facing business objective: expected monetary portfolio return, subject to the same capital, risk, and concentration rules.

- QAOA: quantum optimization experiment.
- Classical exact: exhaustive enumeration for small candidate sets.
- Classical heuristic: deterministic greedy baseline when exact enumeration is too large.

No quantum advantage or speedup is claimed. Runtime and objective differences are reported as measurements, not promises.

## 14. Known limitations

- QAOA is a simulator-backed prototype, not proof of quantum advantage.
- The QAOA candidate subproblem is intentionally bounded to 10 vendor decision qubits for hackathon reliability.
- The seeded credit model and all seeded financial histories are synthetic and must not be represented as real-world credit performance.
- The classical exact benchmark is practical only for small N; larger problems use a clearly labeled heuristic.
- OCR depends on the Tesseract system binary and falls back gracefully when it is unavailable.
- Browser voice uses the Web Speech API; Bluetooth speakers are ordinary browser audio outputs, not quantum hardware.
- The application audit log is an append-oriented application log, not a cryptographically immutable ledger.

## 15. Honest claims vs non-claims

### Claims supported by this prototype
- AI-assisted alternative credit intelligence.
- Persisted Random Forest scoring with explainability.
- SHAP-based technical explanations where the model path is available.
- Constrained portfolio optimization prototype.
- QUBO formulation and QAOA simulation using Qiskit/Aer where available.
- Classical benchmark using the same business objective and feasibility rules.
- Deterministic fallback when the quantum simulator is unavailable.
- Human lender approval remains separate from automated decision support.

### Claims explicitly not made
- No claim of real-world credit accuracy.
- No claim of training on real banking data.
- No claim of quantum advantage.
- No claim of quantum speedup.
- No claim that QAOA is globally optimal.
- No claim of immutable/cryptographically tamper-proof audit logs.
- No claim that Bluetooth hardware is quantum hardware.
