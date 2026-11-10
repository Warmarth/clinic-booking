# Clinic booking API (FastAPI)
Run locally: `pip install -r requirements.txt && API_KEY=secret uvicorn main:app`
Env: `API_KEY`, `DATABASE_URL` (Postgres), `RATE_LIMIT` (default 10), `RATE_WINDOW` (default 60s)
Deploy (Render): Web Service, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`.
Add env vars API_KEY and DATABASE_URL (Neon connection string).
Design: a partial unique index (one confirmed booking per slot) enforces no double booking in the DB;
Idempotency-Key header dedupes retries; per-IP sliding-window rate limit on POST /bookings.
