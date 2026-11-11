export default function BookingForm({ form, onChange, onSubmit, busy }) {
  return (
    <>
      <h2>Your details</h2>
      <input
        placeholder="Full name"
        value={form.name}
        onChange={(e) => onChange({ ...form, name: e.target.value })}
      />
      <input
        placeholder="Email"
        value={form.email}
        onChange={(e) => onChange({ ...form, email: e.target.value })}
      />
      <button disabled={busy} onClick={onSubmit}>Book selected slot</button>
    </>
  );
}
