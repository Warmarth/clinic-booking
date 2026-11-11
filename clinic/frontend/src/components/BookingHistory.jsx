export default function BookingHistory({
  bookings,
  canGoBack,
  onLoad,
  onNext,
  onPrevious,
  onCancel,
}) {
  return (
    <>
      <button onClick={() => onLoad(null)}>Show bookings</button>
      {bookings && (
        <>
          {bookings.bookings.length === 0 && <p>No bookings found.</p>}
          {bookings.bookings.map((booking) => (
            <div key={booking.id} className="slot">
              <span>Slot {booking.slot_id} — {booking.name} — <b>{booking.status}</b></span>
              {booking.status === "confirmed" && (
                <button onClick={() => onCancel(booking.id)}>Cancel</button>
              )}
            </div>
          ))}
          <button disabled={!canGoBack} onClick={onPrevious}>Prev</button>
          <button disabled={!bookings.next_cursor} onClick={onNext}>Next</button>
        </>
      )}
    </>
  );
}
