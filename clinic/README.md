# Clinic Booking API

A lightweight clinic appointment-booking service built with FastAPI and SQLAlchemy. It exposes slot availability, booking creation, booking lookup, and cancellation logic for a small clinic workflow.

## Features

- Appointment slot listing with availability status
- One confirmed booking per slot enforced by the database
- Duplicate-safe booking retries using the `Idempotency-Key` header
- API-key authentication for protected routes
- Per-IP rate limiting on booking attempts
- Optional static frontend served from `/static`
- SQLite by default, with PostgreSQL support through `DATABASE_URL`

## Project structure

- `main.py` — application and middleware setup
- `routes.py` — HTTP endpoints and route-specific helpers
- `config.py` — environment-based application configuration
- `database.py` — database engine, schema initialization, and default slot seeding
- `models.py` — SQLAlchemy tables and Pydantic response models
- `middlewares.py` — API-key authentication, CORS, and rate-limiting helpers
- `static/` — browser UI for booking appointments
- `requirements.txt` — dependencies
- `.env` — local environment values for development

## Local setup

```bash
cd clinic
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
API_KEY=secret uvicorn main:app --reload
```

Open the app at:

- http://localhost:8000
- Swagger docs: http://localhost:8000/docs

## Environment variables

```bash
export API_KEY="secret"
export DATABASE_URL="sqlite:///./clinic.db"
export RATE_LIMIT="10"
export RATE_WINDOW="60"
```

- `API_KEY`: required for non-public API routes
- `DATABASE_URL`: database connection string; PostgreSQL is supported
- `RATE_LIMIT`: number of booking attempts allowed in the configured window
- `RATE_WINDOW`: rate-limit window in seconds

## API overview

### Public routes

- `GET /` — serves the booking page
- `GET /slots` — returns all slots with availability
- `POST /bookings` — creates a booking
- `GET /bookings?limit=10&cursor=...` — returns `bookings` and `next_cursor` for cursor-based pages; optionally filter by email
- `GET /bookings/{booking_id}` — fetches a single booking
- `DELETE /bookings/{booking_id}` — cancels a booking
- `POST /reset` — resets slots and clears booking data

### Important protections

- `X-API-Key` header required on protected endpoints
- `Idempotency-Key` header deduplicates retried booking requests
- Database unique index ensures no double booking on a confirmed slot
- Sliding-window IP rate limiting avoids abuse of booking creation

## Example

```bash
curl -X POST \
  -H "X-API-Key: secret" \
  -H "Idempotency-Key: test-123" \
  -H "Content-Type: application/json" \
  -d '{
    "slot_id": "s1",
    "name": "Jane Doe",
    "email": "jane@example.com"
  }' \
  http://localhost:8000/bookings
```

## Deployment note

For deployment, install dependencies and start the app with Uvicorn:

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set `API_KEY` and `DATABASE_URL` in the host environment before running.
