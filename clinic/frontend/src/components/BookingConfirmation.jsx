export default function BookingConfirmation({ booking, onCancel }) {
  return (
    <>
      <h2>Confirmation</h2>
      {booking ? (
        <div className="card">
          <b>Booking {booking.id}</b>
          <br />
          Status: {booking.status}
          <br />
          {booking.name} ({booking.email})<br />
          Slot: {booking.slot_id}
          {booking.status === "confirmed" && (
            <div>
              <button onClick={() => onCancel(booking.id)}>
                Cancel booking
              </button>
            </div>
          )}
        </div>
      ) : (
        "Nothing booked yet."
      )}
    </>
  );
}
