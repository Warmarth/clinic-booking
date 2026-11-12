from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Index, MetaData, String, Table, text

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
    # Enforce one confirmed booking per slot, including concurrent requests.
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


class BookingResponse(BaseModel):
    id: str
    slot_id: str
    name: str
    email: str
    status: str
    created_at: str


class BookingPageResponse(BaseModel):
    bookings: list[BookingResponse]
    next_cursor: Optional[str]
