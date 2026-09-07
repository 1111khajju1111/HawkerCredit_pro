# CHANGELOG — FINAL merge

Base: `HAWKERCREDIT_ULTIMATE_EDITION.zip` (referred to below as "A"), with
specific files/values taken from `HawkerCredit-Ultimate-Edition.zip`
("B") where B was independently verified to be better. Rationale for each
decision is in `FINAL_README.md` §1; this file is the flat list of every
change actually made.

## Bug fixes (chose A over B, or fixed directly)

- **`backend/app/api/v1/consent.py`** — kept A. B auto-created a
  `granted=True` `ConsentRecord` the first time a vendor's consent
  endpoint was viewed with no existing record — a silent consent grant on
  view, contradicting the explicit "no consent without positive action"
  requirement. Confirmed against `auth.py`'s registration flow, which
  already seeds real consent records at signup for this exact reason (see
  its own in-code comment).
- **`frontend/app/vendor/credit-profile/page.tsx`** — kept A. B had removed
  the `<Suspense>` boundary around `useSearchParams()`, which breaks
  `next build` for this route (a real, previously-encountered Next.js
  production issue, per A's code comment). B also dropped the inline
  loan approve/reject panel present in A; kept.
- **`frontend/lib/api.ts`** — kept A's `API_BASE` fallback of `/api/v1`
  (server-proxied via `next.config.js`'s `rewrites()`). B fell back to a
  hardcoded `http://localhost:8000/api/v1`, which would silently break
  every API call from a deployed Vercel frontend if `NEXT_PUBLIC_API_URL`
  were ever left unset.

## Performance / reliability improvements (chose B over A)

- **`backend/app/quantum/qaoa_solver.py`** — took B. Hoists the QUBO→Ising
  `h`/`J` coefficient computation out of the `build_circuit` closure (which
  is called ~10–15 times per optimization run) so it's computed once
  instead of on every call. Both A's and B's versions use the identical,
  independently-verified-correct conversion formula — this is a pure
  performance fix, not a math change.
- **`backend/app/main.py`** — took B. Adds `GET /` returning a basic
  service-status JSON body, so platform health probes or stray browser
  hits against the bare domain root don't 404.
- **`render.yaml`** — took B. Provisions a managed Postgres database
  (`databases:` block) and wires `DATABASE_URL` to it automatically via
  `fromDatabase`, instead of A's `sync: false` placeholder requiring a
  manual paste after deploy.
- **`backend/.env.example`, `frontend/.env.example`** — took B's versions:
  materially more complete inline documentation per variable.

## Correctness / consistency improvements (chose B over A)

- **`frontend/app/lender/benchmark/page.tsx`**,
  **`frontend/app/lender/portfolio/optimizer/page.tsx`**,
  **`frontend/app/demo/page.tsx`** — took B. Updated to read the
  canonical `business_objective` field (shared expected-monetary-return
  metric, already returned identically by both backends) for the
  quantum-vs-classical comparison, instead of comparing raw QUBO penalty
  energy across differently-scoped runs.
- **`max_risk_tolerance` default: `0.45` → `0.25`**, applied consistently
  across `backend/app/schemas/dto.py`, `backend/app/quantum/qubo_builder.py`,
  `backend/app/quantum/classical_benchmark.py`, `backend/app/api/v1/quantum.py`,
  and `frontend/lib/api.ts`. B had already changed this in every one of
  these layers together; adopted B's more conservative value and confirmed
  no layer was left mismatched against the others.

## Hybrid change (neither A nor B alone)

- **`backend/app/quantum/qubo_builder.py`** — kept A's hard 18-total-qubit
  safety ceiling (which B had removed), since a single QAOA call rebuilds
  and executes the circuit multiple times during optimization and Aer
  simulation cost grows sharply with qubit count. On top of that
  mechanism, adopted B's higher-precision default slack-bit widths
  (`capital_slack_bits`/`risk_slack_bits`: 2→3, `concentration_slack_bits`:
  1→2) and `max_concentration_categories` (2→4). Because the ceiling
  mechanism dynamically reduces the effective category count for larger
  candidate pools, this is additional precision on typical (small)
  candidate pools with no new risk of exceeding the qubit budget — verified
  numerically for pool sizes 5–15 vendors (see verification note below).

## Kept from A only (B had no equivalent)

- Root `package.json` and `vercel.json` — required for Vercel to build the
  Next.js app from the monorepo root; B's zip had neither.
- `frontend/app/lender/review/page.tsx` and `frontend/app/lender/layout.tsx`
  — a complete, working 246-line underwriting queue page with real API
  wiring; B had no equivalent feature.
- `backend/app/demo_seed.py`'s bcrypt-hash-caching optimization for the
  shared demo passwords (reduces cold-start seed time; has zero effect on
  real user signups, which always hash fresh with a random salt).

## Brought in from B only (A had no equivalent, purely additive)

- `frontend/app/voice-demo/page.tsx` and
  `frontend/components/HawkerCreditVoiceAlerts.tsx` — browser Web Speech
  API voice alerts demo. Correctly describes a connected Bluetooth speaker
  as ordinary browser audio output, not a quantum-hardware or special
  backend interface. Linked from the landing page (new link added; see
  below).

## Direct edits made during this merge (not simply "take A" or "take B")

- `frontend/app/page.tsx` — added a "VOICE ALERTS" link to `/voice-demo`
  next to the existing dashboard links, since that route was newly brought
  in from B and had no entry point from the landing page.
- Renamed `backend/.gitignore.txt` → `backend/.gitignore` and
  `frontend/.gitignore.txt` → `frontend/.gitignore` (both were valid
  gitignore content that had been given a `.txt` suffix, likely by
  whatever process produced the zip, which would have made them inert).
- Removed `backend/app/ai/models/credit_rf_model.joblib.backup` (stale
  backup of the trained model artifact; the live `.joblib` is unaffected).
- Removed the pre-merge `README.md`, `CHANGELOG.md`, `DEPLOY_ONE_SHOT.md`,
  and `ULTIMATE_EDITION.md` at the repo root — superseded by
  `FINAL_README.md`, `DEPLOYMENT_CHECKLIST.md`, and this file, to avoid
  shipping duplicate/conflicting documentation.
- Removed all `__pycache__/`, `.pytest_cache/`, `node_modules/`, `.next/`,
  and stray `*.db` files from both source trees before packaging.

## Everything else

76 of the 84 files common to both zips were byte-for-byte identical,
including: all authentication/JWT/security code, all SQLAlchemy models,
all vendor/lender/admin routers not listed above, the classical validator,
portfolio metrics, all AI/SHAP/OCR/forecasting/anomaly-detection modules,
all database migration/session setup, and nearly the entire frontend
(dashboards, coach, receipt-entry, voice-entry, decision-trace, login,
theming, and all shared components). These were carried over unmodified —
there was nothing to reconcile.

## Independent verification performed during this merge

- `python -m py_compile` on every backend `.py` file in the final tree:
  **all pass**.
- `tsc --noEmit`, filtered to genuine parse errors (TS1xxx), on every
  frontend `.ts`/`.tsx` file: **zero syntax errors** across 24 files.
  (Type-resolution errors from the absence of `node_modules` were expected
  and excluded from this check — they are not evidence of a real bug.)
- Static check that every `@/`-aliased frontend import resolves to a real
  file: **no stale imports found**.
- Static check that every `api.<method>()` call used in a page has a
  matching definition in `frontend/lib/api.ts`: **all resolved**.
- Cross-check of frontend `useRequireAuth([...])` role gates against
  backend `require_roles([...])` gates, route by route: **consistent**.
- Independent numerical re-verification of the QUBO→Ising conversion:
  built a real 16-qubit QUBO from the merged project's own
  `qubo_builder.py`, computed Ising energy with the same formula
  `qaoa_solver.py` uses, and compared against the QUBO's own `x^T Q x`
  energy (plus constant offset) across 200 random bitstrings. **Maximum
  discrepancy ≈ 1×10⁻¹³** (floating-point noise — exact agreement).
- Verified the 18-qubit safety ceiling holds for vendor-pool sizes 5–15
  fed directly to `build_portfolio_qubo`, and confirmed the real API
  candidate-selection pipeline (`api/v1/quantum.py`) never sends more than
  10 vendors to it in the first place.
- Grep-based static audit for hardcoded `localhost`/`127.0.0.1` outside
  config defaults, hardcoded secret-like strings, and `TODO`/`FIXME`
  markers: **none found**.

## Not verified in this session (no network access)

`pytest`, `npm install` / `next build`, and any live database or Qiskit
execution could not be run — the environment this merge was performed in
has no network access, so neither `pip` nor `npm` could fetch dependencies.
See `FINAL_README.md` §7 for exactly what this means and what to run
yourself before deploying.
