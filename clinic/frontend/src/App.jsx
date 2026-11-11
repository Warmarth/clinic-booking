import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
  useOutletContext,
} from "react-router-dom";
import BookingConfirmation from "./components/BookingConfirmation.jsx";
import BookingForm from "./components/BookingForm.jsx";
import BookingHistory from "./components/BookingHistory.jsx";
import SlotPicker from "./SlotPicker.jsx";
import AppLayout from "./layouts/AppLayout.jsx";

function BookingRoute() {
  const { slots, sel, setSel, form, setForm, book, busy, confirmation, cancel } =
    useOutletContext();

  return (
    <section>
      <SlotPicker slots={slots} selectedSlot={sel} onSelect={setSel} />
      <BookingForm
        form={form}
        onChange={setForm}
        onSubmit={book}
        busy={busy}
      />
      <BookingConfirmation booking={confirmation} onCancel={cancel} />
    </section>
  );
}

function BookingsRoute() {
  const {
    form, updateForm, mine, cursorHistory, loadMine, nextBookingsPage,
    previousBookingsPage, cancel,
  } = useOutletContext();

  return (
    <section>
      <h2>My bookings</h2>
      <label>
        Email
        <input
          type="email"
          value={form.email}
          onChange={(event) => updateForm({ email: event.target.value })}
        />
      </label>
      <BookingHistory
        bookings={mine}
        canGoBack={cursorHistory.length > 0}
        onLoad={loadMine}
        onNext={nextBookingsPage}
        onPrevious={previousBookingsPage}
        onCancel={cancel}
      />
    </section>
  );
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <BookingRoute /> },
      { path: "bookings", element: <BookingsRoute /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
