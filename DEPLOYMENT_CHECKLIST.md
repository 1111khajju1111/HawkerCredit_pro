# HawkerCredit Quantum — Deployment Checklist

## Vercel
- [ ] Import repository
- [ ] Verify Next.js app under `frontend/`
- [ ] Set `BACKEND_URL=https://<render-service>.onrender.com`
- [ ] Optionally set `NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com/api/v1`
- [ ] Build succeeds with `npm run build`
- [ ] Landing page loads
- [ ] Login page loads
- [ ] Vendor routes load after authentication
- [ ] Lender routes load after authentication
- [ ] Decision trace route loads
- [ ] Voice demo route loads

## Render
- [ ] Docker runtime selected
- [ ] Dockerfile path `./backend/Dockerfile`
- [ ] Docker context `./backend`
- [ ] `ENVIRONMENT=production`
- [ ] `JWT_SECRET` configured
- [ ] `STAFF_BOOTSTRAP_SECRET` configured
- [ ] `DATABASE_URL` configured
- [ ] `CORS_ORIGINS` contains the real Vercel origin
- [ ] `DEMO_SEED_ON_STARTUP=true` for demo
- [ ] `/health` returns HTTP 200
- [ ] Container binds `${PORT:-10000}`
- [ ] Migration reaches `head`

## PostgreSQL
- [ ] Database exists and accepts the Render connection
- [ ] Tables are created by migration
- [ ] Foreign keys/relationships initialize
- [ ] Demo seed is idempotent
- [ ] 100 vendors are present after demo seeding
- [ ] Multiple categories are present
- [ ] Low/medium/high risk cases are present

## UptimeRobot
- [ ] HTTP monitor created
- [ ] Monitor URL is `/health`
- [ ] Expected status is 200
- [ ] No monitor targets expensive quantum endpoints

## Environment variables
- [ ] `DATABASE_URL`
- [ ] `JWT_SECRET`
- [ ] `CORS_ORIGINS`
- [ ] `ENVIRONMENT`
- [ ] `DEMO_SEED_ON_STARTUP`
- [ ] `STAFF_BOOTSTRAP_SECRET`
- [ ] `NEXT_PUBLIC_API_URL` if used
- [ ] `BACKEND_URL`
- [ ] No real secrets committed

## Application smoke test
- [ ] Database migration runs automatically from the Docker entrypoint (`alembic upgrade head`)
- [ ] Demo seed
- [ ] Vendor login
- [ ] Vendor dashboard
- [ ] Vendor profile
- [ ] Credit score
- [ ] SHAP/explainability
- [ ] Transaction history
- [ ] Forecast
- [ ] Anomaly detection
- [ ] AI coach
- [ ] Consent controls
- [ ] Loan request
- [ ] Lender login
- [ ] Vendor discovery
- [ ] Vendor profile from lender view
- [ ] Underwriting queue
- [ ] Approve/reject decision
- [ ] Audit entry
- [ ] Portfolio optimizer
- [ ] QUBO formulation
- [ ] QAOA/Aer execution when available
- [ ] Classical fallback when Qiskit/Aer unavailable
- [ ] Classical benchmark
- [ ] Quantum-vs-classical comparison
- [ ] Feasibility post-validation
- [ ] Persisted optimization run
- [ ] Decision trace
- [ ] Admin login
- [ ] Admin metrics/audit
