export default function BookingHistory({ bookings, offset, pageSize, onLoad, onCancel }) {
  return (
    <>
      <button onClick={() => onLoad(0)}>Show bookings</button>
      {bookings && (
        <>
          {bookings.items.length === 0 && <p>No bookings found.</p>}
          {bookings.items.map((booking) => (
            <div key={booking.id} className="slot">
              <span>Slot {booking.slot_id} — {booking.name} — <b>{booking.status}</b></span>
              {booking.status === "confirmed" && (
                <button onClick={() => onCancel(booking.id)}>Cancel</button>
              )}
            </div>
          ))}
          <button disabled={offset === 0} onClick={() => onLoad(Math.max(0, offset - pageSize))}>Prev</button>
          <button disabled={!bookings.has_more} onClick={() => onLoad(offset + pageSize)}>Next</button>
        </>
      )}
    </>
  );
}
