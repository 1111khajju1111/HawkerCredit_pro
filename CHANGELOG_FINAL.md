# Final Merge Changelog

## Architecture
- Established the security-hardened edition as the canonical backend/frontend baseline.
- Kept one canonical SQLAlchemy model set, DTO set, API router set, AI pipeline, quantum pipeline, and audit/consent model.
- Restored the companion edition's standalone voice-demo page/component because it added useful presentation functionality without duplicating core logic.

## Security
- Preserved JWT authentication and role-based access controls.
- Preserved strict vendor isolation and removed any unauthenticated fallback identity behavior.
- Kept public self-registration vendor-only.
- Kept lender/admin creation behind bootstrap/admin authorization.
- Added password length bounds and optimizer/loan input bounds.
- Added frontend cleanup/redirect on API 401 session expiry.
- Fixed loan-request audit attribution to the authenticated user.

## Data and deployment
- Added deterministic synthetic seed initialization.
- Changed application default demo seeding to opt-in (`false`) while Render demo configuration explicitly enables it.
- Added Alembic migration infrastructure with the Docker entrypoint running `alembic upgrade head` before Uvicorn.
- Kept PostgreSQL configuration deployment-ready and `/health` inexpensive.
- Cleaned repository ignore artifacts and temporary/development outputs.

## AI
- Preserved persisted Random Forest scoring.
- Preserved deterministic feature engineering, SHAP explainability, data-quality, forecasting, anomaly detection, OCR, and voice functionality.
- Preserved explicit synthetic/demo disclosure.

## Quantum
- Preserved the mathematically correct QUBO→Ising conversion and QAOA gate mapping.
- Added exhaustive small-QUBO verification during final review.
- Standardized the default risk tolerance to 25% across the optimizer stack/UI.
- Added deterministic candidate selection from the full eligible pool to a 10-vendor QAOA subproblem.
- Ensured candidate categories are bounded to the QUBO concentration representation instead of silently omitting categories.
- Preserved deterministic QAOA fallback to the classical benchmark.
- Preserved post-QAOA feasibility validation and classical repair.
- Reused persisted benchmark results when the optimization constraints match.
- Kept quantum-vs-classical reporting based on expected monetary return rather than incomparable raw energies.

## Frontend
- Preserved Suspense protection around `useSearchParams` routes required for Next.js production builds.
- Preserved lender review and decision-trace workflows.
- Preserved vendor/lender/admin dashboards.
- Added the companion voice demo.
- Added automatic frontend logout/redirect behavior on expired/invalid API sessions.

## Testing and review
- Python compileall executed successfully.
- Exhaustive QUBO→Ising energy equivalence verification passed on the final builder for a small problem.
- Static scans were performed for localhost references, imports, secrets, fake-live language, and conflicting implementations.
- Full dependency-based pytest and Next.js production build were attempted but could not be executed because the environment had no network access and required packages were not cached. This limitation is explicitly documented rather than being reported as a pass.

## Deployment hardening follow-up — 2026-09-07
- Fixed the backend Docker image so `alembic.ini` and the complete `alembic/` migration tree are included in the image.
- Changed the Docker entrypoint to run `alembic upgrade head` before starting Uvicorn, avoiding dependency on Render's paid pre-deploy feature on the Free plan.
- Removed the obsolete SQLite URL from `alembic.ini`; the Alembic environment derives the database URL from application settings.
- Fixed `CORS_ORIGINS` parsing so Render can supply either a plain URL, comma-separated URLs, or a JSON array without Pydantic settings JSON-decoding failures.
- Removed duplicate migration execution from `app.main`.
- Corrected `vercel.json` so Vercel's `frontend` Root Directory is not prefixed by a second `cd frontend`.
- Revalidated Alembic migration execution against a temporary SQLite database and re-ran Python/static deployment checks.
- Confirmed that Docker build execution itself could not be run in this environment because the Docker CLI is unavailable.
