"""Clinic booking API (FastAPI + SQLAlchemy)."""

import hmac
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import (
    Column,
    DateTime,
    Index,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

load_dotenv()

# ---------------------------------------------------------------- config
API_KEY = os.environ.get("API_KEY", "dev-key")
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./clinic.db")
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "10"))  # booking attempts...
RATE_WINDOW = int(os.environ.get("RATE_WINDOW", "60"))  # ...per N seconds
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------------------------------------------- database
engine = create_engine(DB_URL, pool_pre_ping=True)
metadata = MetaData()

slots_t = Table(
    "slots",
    metadata,
    Column("id", String, primary_key=True),
    Column("provider", String, nullable=False),
    Column("start", String, nullable=False),
    Column("end", String, nullable=False),
)

bookings_t = Table(
    "bookings",
    metadata,
    Column("id", String, primary_key=True),
    Column("slot_id", String, nullable=False),
    Column("name", String, nullable=False),
    Column("email", String, nullable=False, index=True),
    Column("status", String, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    # The database itself guarantees one confirmed booking per slot,
    # even when requests arrive at the exact same moment.
    Index(
        "uq_one_confirmed_per_slot",
        "slot_id",
        unique=True,
        postgresql_where=text("status = 'confirmed'"),
        sqlite_where=text("status = 'confirmed'"),
    ),
)

idempotency_t = Table(
    "idempotency",
    metadata,
    Column("key", String, primary_key=True),
    Column("booking_id", String, nullable=False),
)

metadata.create_all(engine)


def default_slots():
    base = datetime(2026, 12, 10, 9, 0, tzinfo=timezone.utc)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    slots = []
    for i, provider in enumerate(["Dr Ade", "Dr Bello"]):
        for j in range(8):
            start = base + timedelta(minutes=30 * j)
            slots.append(
                {
                    "id": f"s{i * 8 + j + 1}",
                    "provider": provider,
                    "start": start.strftime(fmt),
                    "end": (start + timedelta(minutes=30)).strftime(fmt),
                }
            )
    return slots


def seed_if_empty():
    with engine.begin() as conn:
        count = conn.execute(select(func.count()).select_from(slots_t)).scalar()
        if count == 0:
            conn.execute(insert(slots_t), default_slots())


seed_if_empty()

# ------------------------------------------------------------------- app
app = FastAPI(title="Clinic booking API")


def err(status, message, headers=None):
    return JSONResponse({"error": message}, status_code=status, headers=headers)


@app.exception_handler(RequestValidationError)
async def on_validation_error(request, exc):
    return err(400, "invalid request")


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request, exc):
    return err(exc.status_code, str(exc.detail))


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    path = request.url.path
    is_open = (
        request.method == "OPTIONS"  # CORS preflight carries no key
        or path in ("/", "/docs", "/openapi.json")
        or path.startswith("/static")
    )
    if is_open:
        return await call_next(request)
    key = request.headers.get("x-api-key", "")
    if not key:
        return err(401, "API key required")
    if not hmac.compare_digest(key.encode(), API_KEY.encode()):
        return err(401, "invalid API key")
    return await call_next(request)


# Added AFTER the auth middleware so it wraps it (outermost).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)

# --------------------------------------------------------- rate limiting
_hits = defaultdict(deque)
_lock = threading.Lock()


def rate_limited(request: Request) -> int:
    """Sliding window per client IP. Returns seconds to wait, or 0 if allowed."""
    forwarded = request.headers.get("x-forwarded-for")
    ip = (forwarded or request.client.host or "?").split(",")[0].strip()
    now = time.time()
    with _lock:
        window = _hits[ip]
        while window and now - window[0] > RATE_WINDOW:
            window.popleft()
        if len(window) >= RATE_LIMIT:
            return max(1, int(RATE_WINDOW - (now - window[0])) + 1)
        window.append(now)
    return 0


# --------------------------------------------------------------- helpers
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def to_dict(booking_row):
    data = dict(booking_row._mapping)
    created = data["created_at"]
    if created.tzinfo is None:  # SQLite returns naive datetimes
        created = created.replace(tzinfo=timezone.utc)
    data["created_at"] = created.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return data


def booking_for_key(key: str):
    with engine.connect() as conn:
        return conn.execute(
            select(bookings_t)
            .join(idempotency_t, idempotency_t.c.booking_id == bookings_t.c.id)
            .where(idempotency_t.c.key == key)
        ).first()


# ---------------------------------------------------------------- routes
@app.post("/reset")
async def reset(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = None
    if isinstance(body, dict):
        items = body.get("slots")
    elif isinstance(body, list):
        items = body
    else:
        items = None
    items = items or default_slots()

    fields = ("id", "provider", "start", "end")
    clean = []
    for slot in items:
        valid = isinstance(slot, dict) and all(
            isinstance(slot.get(f), str) and slot[f] for f in fields
        )
        if not valid:
            return err(400, "invalid slots")
        clean.append({f: slot[f] for f in fields})

    with engine.begin() as conn:
        conn.execute(idempotency_t.delete())
        conn.execute(bookings_t.delete())
        conn.execute(slots_t.delete())
        conn.execute(insert(slots_t), clean)
    with _lock:
        _hits.clear()
    return {"ok": True, "slots": len(clean)}


@app.get("/slots")
def list_slots():
    with engine.connect() as conn:
        taken = {
            r[0]
            for r in conn.execute(
                select(bookings_t.c.slot_id).where(bookings_t.c.status == "confirmed")
            )
        }
        rows = conn.execute(select(slots_t).order_by(slots_t.c.start, slots_t.c.id)).all()
    return [{**dict(r._mapping), "available": r.id not in taken} for r in rows]


@app.post("/bookings")
async def create_booking(request: Request, idempotency_key: Optional[str] = Header(None)):
    wait = rate_limited(request)
    if wait:
        return err(429, "too many requests", {"Retry-After": str(wait)})

    try:
        body = await request.json()
    except Exception:
        return err(400, "body must be valid JSON")
    if not isinstance(body, dict):
        return err(400, "body must be a JSON object")

    slot_id, name, email = body.get("slot_id"), body.get("name"), body.get("email")
    if not isinstance(slot_id, str) or not slot_id.strip():
        return err(400, "slot_id is required")
    if not isinstance(name, str) or not name.strip():
        return err(400, "name is required")
    if not isinstance(email, str) or not EMAIL_RE.match(email.strip()):
        return err(400, "a valid email is required")
    slot_id, name, email = slot_id.strip(), name.strip(), email.strip()

    # A retried request returns the original booking instead of a new one.
    if idempotency_key:
        previous = booking_for_key(idempotency_key)
        if previous:
            return JSONResponse(to_dict(previous), status_code=201)

    booking_id = uuid.uuid4().hex
    try:
        with engine.begin() as conn:
            slot = conn.execute(select(slots_t.c.id).where(slots_t.c.id == slot_id)).first()
            if not slot:
                return err(404, "slot not found")
            conn.execute(
                insert(bookings_t).values(
                    id=booking_id,
                    slot_id=slot_id,
                    name=name,
                    email=email,
                    status="confirmed",
                    created_at=datetime.now(timezone.utc),
                )
            )
            if idempotency_key:
                conn.execute(
                    insert(idempotency_t).values(key=idempotency_key, booking_id=booking_id)
                )
    except IntegrityError:
        if idempotency_key:  # the same key raced in: return the winner's booking
            previous = booking_for_key(idempotency_key)
            if previous:
                return JSONResponse(to_dict(previous), status_code=201)
        return err(409, "slot already booked")

    with engine.connect() as conn:
        booking = conn.execute(select(bookings_t).where(bookings_t.c.id == booking_id)).first()
    return JSONResponse(to_dict(booking), status_code=201)


@app.get("/bookings")
def list_bookings(
    email: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    page: Optional[int] = None,
):
    if limit < 1 or limit > 100 or offset < 0 or (page is not None and page < 1):
        return err(400, "invalid paging parameters")
    if page is not None:
        offset = (page - 1) * limit

    query = select(bookings_t)
    count_query = select(func.count()).select_from(bookings_t)
    if email:
        query = query.where(bookings_t.c.email == email)
        count_query = count_query.where(bookings_t.c.email == email)

    with engine.connect() as conn:
        total = conn.execute(count_query).scalar()
        rows = conn.execute(
            query.order_by(bookings_t.c.created_at, bookings_t.c.id).limit(limit).offset(offset)
        ).all()

    return {
        "items": [to_dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(rows) < total,
    }


@app.get("/bookings/{booking_id}")
def get_booking(booking_id: str):
    with engine.connect() as conn:
        booking = conn.execute(select(bookings_t).where(bookings_t.c.id == booking_id)).first()
    return to_dict(booking) if booking else err(404, "booking not found")


@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: str):
    with engine.begin() as conn:
        conn.execute(
            update(bookings_t).where(bookings_t.c.id == booking_id).values(status="cancelled")
        )
        booking = conn.execute(select(bookings_t).where(bookings_t.c.id == booking_id)).first()
    return to_dict(booking) if booking else err(404, "booking not found")


# ------------------------------------------------- optional static page
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))
