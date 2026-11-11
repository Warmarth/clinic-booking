import os, concurrent.futures as cf

os.environ.update(API_KEY="k", DATABASE_URL="sqlite:///./t.db", RATE_LIMIT="1000")
from fastapi.testclient import TestClient
from main import app

c = TestClient(app)
H = {"X-API-Key": "k"}
assert c.get("/health").status_code == 200
assert c.get("/health").json() == {"status": "ok"}
missing_key = c.get("/slots")
assert missing_key.status_code == 401
assert missing_key.json()["error"] == "API key required"
invalid_key = c.get("/slots", headers={"X-API-Key": "wrong"})
assert invalid_key.status_code == 401
assert invalid_key.json()["error"] == "invalid API key"
c.post("/reset", headers=H)
assert len(c.get("/slots", headers=H).json()) == 16
good = {"slot_id": "s1", "name": "Ada", "email": "a@b.co"}
assert c.post("/bookings", headers=H, json={**good, "email": "x"}).status_code == 400
assert c.post("/bookings", headers=H, json={**good, "slot_id": "zz"}).status_code == 404


def go(i):
    return c.post(
        "/bookings", headers=H, json={**good, "slot_id": "s2", "name": f"p{i}"}
    ).status_code


with cf.ThreadPoolExecutor(10) as ex:
    codes = list(ex.map(go, range(10)))
print(sorted(codes))
assert codes.count(201) == 1 and codes.count(409) == 9
r1 = c.post("/bookings", headers={**H, "Idempotency-Key": "q"}, json=good).json()
r2 = c.post("/bookings", headers={**H, "Idempotency-Key": "q"}, json=good).json()
assert r1["id"] == r2["id"]
assert c.delete(f"/bookings/{r1['id']}", headers=H).json()["status"] == "cancelled"
assert c.get("/slots", headers=H).json()[0]["available"] is True
for i in range(5):
    c.post(
        "/bookings", headers={**H, "Idempotency-Key": f"n{i}"}, json={**good, "slot_id": f"s{i+3}"}
    )
p = c.get("/bookings?email=a@b.co&limit=2&offset=2", headers=H).json()
print(p["total"], len(p["items"]))
assert c.get("/bookings/nope", headers=H).status_code == 404
print("OK")
