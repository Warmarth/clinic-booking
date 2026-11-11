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
  const [keyInput, setKeyInput] = useState("");
  const [key, setKey] = useState(null);
  const [slots, setSlots] = useState([]);
  const [sel, setSel] = useState(null);
  const [form, setForm] = useState({ name: "", email: "" });
  const [msg, setMsg] = useState(null);
  const [confirmation, setConfirmation] = useState(null);
  const [mine, setMine] = useState(null);
  const [cursor, setCursor] = useState(null);
  const [cursorHistory, setCursorHistory] = useState([]);
  const [busy, setBusy] = useState(false);

  const say = (text, ok = false) => setMsg({ text, ok });
  const updateForm = (changes) => setForm((current) => ({ ...current, ...changes }));

  const loadSlots = useCallback(async () => {
    if (!key) {
      setSlots([]);
      return;
    }
    try { setSlots(await fetchSlots(key)); }
    catch (e) { setSlots([]); say(e.message); }
  }, [key]);

  const loadMine = useCallback(async (nextCursor = null) => {
    try {
      const d = await fetchBookings(key, form.email, nextCursor);
      setMine(d); setCursor(nextCursor);
    } catch (e) { say(e.message); }
  }, [key, form.email]);

  function showBookings() {
    setCursorHistory([]);
    loadMine(null);
  }

  function nextBookingsPage() {
    if (!mine?.next_cursor) return;
    setCursorHistory((history) => [...history, cursor]);
    loadMine(mine.next_cursor);
  }

  function previousBookingsPage() {
    if (cursorHistory.length === 0) return;
    const previousCursor = cursorHistory[cursorHistory.length - 1];
    setCursorHistory((history) => history.slice(0, -1));
    loadMine(previousCursor);
  }

  useEffect(() => { loadSlots(); }, [loadSlots]);

  async function book() {
    if (!sel) return say("Pick a slot first");
    setBusy(true);
    try {
      const b = await createBooking(key, sel, form);
      setConfirmation(b); setSel(null); say("Booked!", true);
    } catch (e) { say(e.message); }
    setBusy(false); loadSlots(); if (mine) showBookings();
  }

  async function cancel(id) {
    try {
      const b = await cancelBooking(key, id);
      if (confirmation?.id === id) setConfirmation(b);
      say("Cancelled", true);
    } catch (e) { say(e.message); }
    loadSlots(); if (mine) loadMine(cursor);
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

      <label>API key <input type="password" value={keyInput} onChange={(e) => setKeyInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") setKey(keyInput.trim() || null); }} placeholder="api-secret-key" /></label>
      <button type="button" onClick={() => setKey(keyInput.trim() || null)}>Use API key</button>
      <Message message={msg} />

      <Outlet context={{
        slots, sel, setSel, form, setForm, updateForm, book, busy, confirmation,
        cancel, mine, cursorHistory, loadMine: showBookings,
        nextBookingsPage, previousBookingsPage,
      }} />
    </main>
  );
}
