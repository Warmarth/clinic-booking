# Clinic Booking

A small clinic appointment-booking app built with FastAPI, SQLAlchemy, and a lightweight static frontend. It lets patients view appointment slots, place a booking, list their bookings, and cancel existing ones while enforcing slot availability and basic API protections.

## Project overview

This project includes:

- A FastAPI backend for managing clinic slots and bookings
- SQLite by default, with PostgreSQL-compatible configuration via `DATABASE_URL`
- A static browser UI served from `/static`
- Booking protection rules:
  - only one confirmed booking per slot
  - idempotent retries with `Idempotency-Key`
  - API key authentication for non-public routes
  - per-IP rate limiting on booking attempts

## Repository layout

- `clinic/main.py` — FastAPI application and database setup
- `clinic/static/` — booking UI served by the app
- `clinic/frontend/` — frontend source (if present in your local checkout)
- `clinic/requirements.txt` — Python dependencies
- `clinic/.env` — local environment values (not committed in shared setups)

## Quick start

From the project directory:

```bash
cd clinic
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
API_KEY=secret uvicorn main:app --reload
```

The API will be available at:

- http://localhost:8000
- Swagger UI: http://localhost:8000/docs

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `API_KEY` | No | `dev-key` | API key required for protected routes |
| `DATABASE_URL` | No | `sqlite:///./clinic.db` | Database connection string |
| `RATE_LIMIT` | No | `10` | Max booking attempts in the rate-limiting window |
| `RATE_WINDOW` | No | `60` | Rate-limit window in seconds |

Example:

```bash
export API_KEY="change-me"
export DATABASE_URL="postgresql://user:pass@host:5432/clinic"
export RATE_LIMIT="10"
export RATE_WINDOW="60"
```

## Core API behavior

### Public endpoints

- `GET /` — serves the booking page
- `GET /slots` — lists available and taken slots
- `POST /bookings` — creates a confirmed booking for a selected slot
- `GET /bookings?limit=10&cursor=...` — returns `bookings` and `next_cursor` for cursor-based pages; optionally filter by email
- `GET /bookings/{booking_id}` — fetches a single booking
- `DELETE /bookings/{booking_id}` — cancels a booking
- `POST /reset` — clears and re-seeds appointment slots

### Request protections

- Protected endpoints expect the `X-API-Key` header.
- `POST /bookings` also supports `Idempotency-Key` to prevent duplicate processing on retries.
- Booking attempts are throttled per client IP using a sliding-window limiter.
- Database constraints ensure one confirmed booking per slot.

## Example requests

List slots:

```bash
curl -H "X-API-Key: secret" http://localhost:8000/slots
```

Create a booking:

```bash
curl -X POST \
  -H "X-API-Key: secret" \
  -H "Idempotency-Key: 123e4567-e89b-12d3-a456-426614174000" \
  -H "Content-Type: application/json" \
  -d '{
    "slot_id": "s1",
    "name": "Jane Doe",
    "email": "jane@example.com"
  }' \
  http://localhost:8000/bookings
```

List bookings for an email:

```bash
curl -H "X-API-Key: secret" "http://localhost:8000/bookings?email=jane@example.com&limit=10"
```

The response contains a `bookings` array and `next_cursor`. Send that cursor as the `cursor` query parameter to fetch the next page; it is `null` on the last page.

## Notes

- The app defaults to SQLite (`clinic.db`) for local development.
- For production or shared deployments, set `DATABASE_URL` to a PostgreSQL connection string.
- The project is intentionally lightweight and suitable for demonstration or small-clinic appointment workflows.
- The scheduled workflow in `.github/workflows/render-keepalive.yml` pings `/health` every 10 minutes. Add the Render service base URL as a GitHub repository Actions secret named `RENDER_URL` to enable it. Keeping a Render Free instance awake uses its monthly instance hours.
