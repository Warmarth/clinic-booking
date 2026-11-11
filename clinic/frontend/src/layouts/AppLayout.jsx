import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  book as createBooking,
  cancel as cancelBooking,
  loadMine as fetchBookings,
  loadSlots as fetchSlots,
} from "../services/bookings.js";
import Message from "../components/Message.jsx";

export default function AppLayout() {
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
  const updateForm = (changes) => setForm((current) => ({ ...current, ...changes }));

  const loadSlots = useCallback(async () => {
    try { setSlots(await fetchSlots(key)); }
    catch (e) { setSlots([]); say(e.message); }
  }, [key]);

  const loadMine = useCallback(async (off = 0) => {
    try {
      const d = await fetchBookings(key, form.email, off);
      setMine(d); setOffset(off);
    } catch (e) { say(e.message); }
  }, [key, form.email]);

  useEffect(() => { loadSlots(); }, [loadSlots]);

  async function book() {
    if (!sel) return say("Pick a slot first");
    setBusy(true);
    try {
      const b = await createBooking(key, sel, form);
      setConfirmation(b); setSel(null); say("Booked!", true);
    } catch (e) { say(e.message); }
    setBusy(false); loadSlots(); if (mine) loadMine(0);
  }

  async function cancel(id) {
    try {
      const b = await cancelBooking(key, id);
      if (confirmation?.id === id) setConfirmation(b);
      say("Cancelled", true);
    } catch (e) { say(e.message); }
    loadSlots(); if (mine) loadMine(offset);
  }

  return (
    <main>
      <header className="app-header">
        <h1>Clinic booking</h1>
        <nav aria-label="Main navigation">
          <NavLink to="/" end>Book an appointment</NavLink>
          <NavLink to="/bookings">My bookings</NavLink>
        </nav>
      </header>

      <label>API key <input type="password" value={key} onChange={(e) => setKey(e.target.value)} /></label>
      <Message message={msg} />

      <Outlet context={{
        slots, sel, setSel, form, setForm, updateForm, book, busy, confirmation,
        cancel, mine, offset, loadMine,
      }} />
    </main>
  );
}
