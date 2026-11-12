from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, func, insert, select

from config import DB_URL
from models import metadata, slots_t

engine = create_engine(DB_URL, pool_pre_ping=True)
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
