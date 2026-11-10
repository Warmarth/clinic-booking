import { useState, useEffect, useCallback } from "react";
import { api } from "./api.js";

const fmt = (s) =>
  new Date(s).toLocaleString([], { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }) + " UTC";
const PAGE = 5;

export default function App() {
  const [key, setKey] = useState(import.meta.env.VITE_API_KEY || localStorage.getItem("k") || "");
  const [slots, setSlots] = useState([]);
  const [sel, setSel] = useState(null);
  const [form, setForm] = useState({ name: "", email: "" });
  const [msg, setMsg] = useState(null);
  const [confirmation, setConfirmation] = useState(null);
  const [mine, setMine] = useState(null);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);

  const say = (text, ok = false) => setMsg({ text, ok });

  const loadSlots = useCallback(async () => {
    localStorage.setItem("k", key);
    try { setSlots(await api("/slots", { key })); }
    catch (e) { setSlots([]); say(e.message); }
  }, [key]);

  const loadMine = useCallback(async (off = 0) => {
    if (!form.email.trim()) return say("Enter your email first");
    try {
      const d = await api(`/bookings?email=${encodeURIComponent(form.email.trim())}&limit=${PAGE}&offset=${off}`, { key });
      setMine(d); setOffset(off);
    } catch (e) { say(e.message); }
  }, [key, form.email]);

  useEffect(() => { loadSlots(); }, [loadSlots]);

  async function book() {
    if (!sel) return say("Pick a slot first");
    setBusy(true);
    try {
      const b = await api("/bookings", {
        key, method: "POST", body: { slot_id: sel, ...form },
        headers: { "Idempotency-Key": crypto.randomUUID() },
      });
      setConfirmation(b); setSel(null); say("Booked!", true);
    } catch (e) { say(e.message); }
    setBusy(false); loadSlots(); if (mine) loadMine(0);
  }

  async function cancel(id) {
    try {
      const b = await api(`/bookings/${id}`, { key, method: "DELETE" });
      if (confirmation?.id === id) setConfirmation(b);
      say("Cancelled", true);
    } catch (e) { say(e.message); }
    loadSlots(); if (mine) loadMine(offset);
  }

  return (
    <main>
      <h1>Book an appointment</h1>
      <label>API key <input type="password" value={key} onChange={(e) => setKey(e.target.value)} /></label>
      {msg && <div className={msg.ok ? "msg ok" : "msg bad"}>{msg.text}</div>}

      <h2>Available slots</h2>
      {slots.map((s) => (
        <div key={s.id} className={`slot ${s.available ? "" : "taken"} ${sel === s.id ? "sel" : ""}`}>
          <span><b>{s.provider}</b> — {fmt(s.start)}</span>
          <button disabled={!s.available} onClick={() => setSel(s.id)}>
            {s.available ? (sel === s.id ? "Selected" : "Select") : "Taken"}
          </button>
        </div>
      ))}

      <h2>Your details</h2>
      <input placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      <input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
      <button disabled={busy} onClick={book}>Book selected slot</button>

      <h2>Confirmation</h2>
      {confirmation ? (
        <div className="card">
          <b>Booking {confirmation.id}</b><br />
          Status: {confirmation.status}<br />
          {confirmation.name} ({confirmation.email})<br />
          Slot: {confirmation.slot_id}
          {confirmation.status === "confirmed" && <div><button onClick={() => cancel(confirmation.id)}>Cancel booking</button></div>}
        </div>
      ) : "Nothing booked yet."}

      <h2>My bookings</h2>
      <button onClick={() => loadMine(0)}>Show bookings for the email above</button>
      {mine && (
        <>
          {mine.items.length === 0 && <p>No bookings found.</p>}
          {mine.items.map((b) => (
            <div key={b.id} className="slot">
              <span>Slot {b.slot_id} — {b.name} — <b>{b.status}</b></span>
              {b.status === "confirmed" && <button onClick={() => cancel(b.id)}>Cancel</button>}
            </div>
          ))}
          <button disabled={offset === 0} onClick={() => loadMine(Math.max(0, offset - PAGE))}>Prev</button>
          <button disabled={!mine.has_more} onClick={() => loadMine(offset + PAGE)}>Next</button>
        </>
      )}
    </main>
  );
}
