import { api } from "./api.js";

const PAGE = 5;

export async function loadSlots(key) {
  localStorage.setItem("k", key);
  return api("/slots", { key });
}

export async function loadMine(key, email, cursor = null) {
  if (!email.trim()) throw new Error("Enter your email first");

  const params = new URLSearchParams({ email: email.trim(), limit: String(PAGE) });
  if (cursor) params.set("cursor", cursor);
  return api(
    `/bookings?${params}`,
    { key },
  );
}

export async function book(key, slot, form) {
  return api("/bookings", {
    key,
    method: "POST",
    body: { slot_id: slot, ...form },
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
}

export async function cancel(key, id) {
  return api(`/bookings/${id}`, { key, method: "DELETE" });
}
