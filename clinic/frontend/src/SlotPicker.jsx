import { useRef, useState } from "react";

const COLLAPSED_SLOT_COUNT = 3;

function formatStart(start) {
  return new Date(start).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }) + " UTC";
}

export default function SlotPicker({ slots, selectedSlot, onSelect }) {
  const [isOpen, setIsOpen] = useState(true);
  const [showAll, setShowAll] = useState(false);
  const sectionRef = useRef(null);
  const hasMore = slots.length > COLLAPSED_SLOT_COUNT;

  function toggleSlots() {
    if (showAll) {
      setShowAll(false);
      sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      setShowAll(true);
    }
  }

  return (
    <section className="appointments" ref={sectionRef}>
      <button
        className="appointments-toggle"
        type="button"
        aria-expanded={isOpen}
        aria-controls="appointment-list"
        onClick={() => setIsOpen((open) => !open)}
      >
        <span>Available appointments</span>
        <span aria-hidden="true">{isOpen ? "−" : "+"}</span>
      </button>
      <div
        className={`appointments-panel ${isOpen ? "open" : ""}`}
        id="appointment-list"
        aria-hidden={!isOpen}
      >
        <div className={`appointment-list ${showAll ? "expanded" : ""}`}>
          {slots.length === 0 && <p>No appointments available.</p>}
          {slots.map((slot) => (
            <div
              key={slot.id}
              className={`slot ${slot.available ? "" : "taken"} ${selectedSlot === slot.id ? "sel" : ""}`}
            >
              <span><b>{slot.provider}</b> — {formatStart(slot.start)}</span>
              <button disabled={!slot.available} onClick={() => onSelect(slot.id)}>
                {slot.available ? (selectedSlot === slot.id ? "Selected" : "Select") : "Taken"}
              </button>
            </div>
          ))}
        </div>
        {hasMore && (
          <button className="view-appointments" type="button" onClick={toggleSlots}>
            {showAll ? "View fewer appointments" : "View more appointments"}
          </button>
        )}
      </div>
    </section>
  );
}
