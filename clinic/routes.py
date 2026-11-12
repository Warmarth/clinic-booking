import base64
import binascii
import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import insert, or_, select, update
from sqlalchemy.exc import IntegrityError

from config import BASE_DIR, RATE_LIMIT, RATE_WINDOW
from database import default_slots, engine
from middlewares import clear_rate_limits, rate_limited
from models import (
    BookingPageResponse,
    BookingResponse,
    bookings_t,
    idempotency_t,
    slots_t,
)

router = APIRouter()


def err(status, message, headers=None):
    return JSONResponse({"error": message}, status_code=status, headers=headers)


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def to_dict(booking_row):
    data = dict(booking_row._mapping)
    created = data["created_at"]
    if created.tzinfo is None:
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


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/reset")
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
            isinstance(slot.get(field), str) and slot[field] for field in fields
        )
        if not valid:
            return err(400, "invalid slots")
        clean.append({field: slot[field] for field in fields})

    with engine.begin() as conn:
        conn.execute(idempotency_t.delete())
        conn.execute(bookings_t.delete())
        conn.execute(slots_t.delete())
        conn.execute(insert(slots_t), clean)
    clear_rate_limits()
    return {"ok": True, "slots": len(clean)}


@router.get("/slots")
def list_slots():
    with engine.connect() as conn:
        taken = {
            row[0]
            for row in conn.execute(
                select(bookings_t.c.slot_id).where(bookings_t.c.status == "confirmed")
            )
        }
        rows = conn.execute(select(slots_t).order_by(slots_t.c.start, slots_t.c.id)).all()
    return [{**dict(row._mapping), "available": row.id not in taken} for row in rows]


@router.post("/bookings")
async def create_booking(request: Request, idempotency_key: Optional[str] = Header(None)):
    wait = rate_limited(request, RATE_LIMIT, RATE_WINDOW)
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
        if idempotency_key:
            previous = booking_for_key(idempotency_key)
            if previous:
                return JSONResponse(to_dict(previous), status_code=201)
        return err(409, "slot already booked")

    with engine.connect() as conn:
        booking = conn.execute(select(bookings_t).where(bookings_t.c.id == booking_id)).first()
    return JSONResponse(to_dict(booking), status_code=201)


@router.get("/bookings", response_model=BookingPageResponse)
def list_bookings(
    email: Optional[str] = None,
    limit: int = 10,
    cursor: Optional[str] = None,
):
    if limit < 1 or limit > 100:
        return err(400, "invalid paging parameters")

    query = select(bookings_t)
    if email:
        query = query.where(bookings_t.c.email == email)

    if cursor:
        try:
            padding = "=" * (-len(cursor) % 4)
            cursor_data = json.loads(
                base64.urlsafe_b64decode(cursor + padding).decode("utf-8")
            )
            cursor_created_at = datetime.fromisoformat(cursor_data["created_at"])
            cursor_id = cursor_data["id"]
            if (
                cursor_created_at.tzinfo is None
                or not isinstance(cursor_id, str)
                or not cursor_id
            ):
                raise ValueError("invalid cursor id")
        except (
            binascii.Error,
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return err(400, "invalid cursor")
        query = query.where(
            or_(
                bookings_t.c.created_at > cursor_created_at,
                (bookings_t.c.created_at == cursor_created_at)
                & (bookings_t.c.id > cursor_id),
            )
        )

    with engine.connect() as conn:
        rows = conn.execute(
            query.order_by(bookings_t.c.created_at, bookings_t.c.id).limit(limit + 1)
        ).all()

    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = None
    if has_more:
        last = page_rows[-1]
        last_created_at = last.created_at
        if last_created_at.tzinfo is None:
            last_created_at = last_created_at.replace(tzinfo=timezone.utc)
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(
                {
                    "created_at": last_created_at.isoformat(),
                    "id": last.id,
                },
                separators=(",", ":"),
            ).encode("utf-8")
        ).decode("ascii").rstrip("=")

    return {
        "bookings": [to_dict(row) for row in page_rows],
        "next_cursor": next_cursor,
    }


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: str):
    with engine.connect() as conn:
        booking = conn.execute(select(bookings_t).where(bookings_t.c.id == booking_id)).first()
    return to_dict(booking) if booking else err(404, "booking not found")


@router.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: str):
    with engine.begin() as conn:
        booking = conn.execute(
            select(bookings_t).where(bookings_t.c.id == booking_id)
        ).first()
        if not booking:
            return err(404, "booking not found")
        if booking.status == "cancelled":
            return err(409, "already cancelled")
        conn.execute(
            update(bookings_t)
            .where(bookings_t.c.id == booking_id)
            .values(status="cancelled")
        )
        booking = conn.execute(
            select(bookings_t).where(bookings_t.c.id == booking_id)
        ).first()
    return to_dict(booking)


@router.get("/", include_in_schema=False)
def home():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))
