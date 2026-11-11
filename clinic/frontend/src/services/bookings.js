import { api } from "./api.js";

const PAGE = 5;

export async function loadSlots(key) {
  localStorage.setItem("k", key);
  return api("/slots", { key });
}

export async function loadMine(key, email, offset = 0) {
  if (!email.trim()) throw new Error("Enter your email first");

  return api(
    `/bookings?email=${encodeURIComponent(email.trim())}&limit=${PAGE}&offset=${offset}`,
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
