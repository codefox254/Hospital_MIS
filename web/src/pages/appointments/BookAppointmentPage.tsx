import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { staffName, useDepartments, useStaffUsers } from "../../lib/useLookups";
import { usePatients } from "../patients/hooks";
import { useAvailability, useBookAppointment } from "./hooks";
import type { BookingChannel } from "../../types/appointment";

export function BookAppointmentPage() {
  const navigate = useNavigate();
  const { data: departments } = useDepartments();
  const { data: staff } = useStaffUsers();

  const [patientSearch, setPatientSearch] = useState("");
  const [patientId, setPatientId] = useState("");
  const [doctor, setDoctor] = useState("");
  const [department, setDepartment] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [selectedSlot, setSelectedSlot] = useState("");
  const [channel, setChannel] = useState<BookingChannel>("walk_in");

  const { data: patientResults } = usePatients(patientSearch);
  const { data: slots, isFetching: slotsLoading } = useAvailability(doctor, department, date);
  const book = useBookAppointment();

  async function handleBook() {
    if (!patientId || !doctor || !department || !selectedSlot) return;
    try {
      const appt = await book.mutateAsync({
        patient: patientId,
        doctor,
        department,
        scheduled_at: selectedSlot,
        duration_minutes: 30,
        booking_channel: channel,
      });
      navigate("/appointments", { state: { booked: appt.id }, replace: true });
    } catch {
      // book.error surfaces below.
    }
  }

  return (
    <div>
      <h1>Book appointment</h1>
      <div className="form-grid booking-grid">
        <div>
          <label htmlFor="patient-search">Patient</label>
          <input
            id="patient-search"
            placeholder="Search by name, MRN, or phone"
            value={patientSearch}
            onChange={(e) => {
              setPatientSearch(e.target.value);
              setPatientId("");
            }}
          />
          {patientSearch && !patientId && (
            <ul className="typeahead-results">
              {patientResults?.results.slice(0, 6).map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setPatientId(p.id);
                      setPatientSearch(`${p.first_name} ${p.last_name} (${p.mrn})`);
                    }}
                  >
                    {p.first_name} {p.last_name} — {p.mrn}
                  </button>
                </li>
              ))}
              {patientResults?.results.length === 0 && <li>No matches.</li>}
            </ul>
          )}
        </div>

        <div>
          <label htmlFor="department">Department</label>
          <select
            id="department"
            value={department}
            onChange={(e) => {
              setDepartment(e.target.value);
              setSelectedSlot("");
            }}
          >
            <option value="">Select a department</option>
            {departments?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="doctor">Doctor</label>
          <select
            id="doctor"
            value={doctor}
            onChange={(e) => {
              setDoctor(e.target.value);
              setSelectedSlot("");
            }}
          >
            <option value="">Select a doctor</option>
            {staff?.map((s) => (
              <option key={s.id} value={s.id}>
                {staffName(s)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="date">Date</label>
          <input
            id="date"
            type="date"
            value={date}
            onChange={(e) => {
              setDate(e.target.value);
              setSelectedSlot("");
            }}
          />
        </div>

        <div>
          <label htmlFor="channel">Booking channel</label>
          <select id="channel" value={channel} onChange={(e) => setChannel(e.target.value as BookingChannel)}>
            <option value="walk_in">Walk-in</option>
            <option value="web">Web</option>
            <option value="mobile">Mobile</option>
          </select>
        </div>

        <div className="checkbox-row" style={{ display: "block" }}>
          <label>Available slots</label>
          {slotsLoading && <p>Checking availability…</p>}
          {!slotsLoading && doctor && department && slots?.length === 0 && (
            <p>No available slots for this date.</p>
          )}
          <div className="slot-grid">
            {slots?.map((slot) => (
              <button
                key={slot}
                type="button"
                className={slot === selectedSlot ? "slot-button selected" : "slot-button"}
                onClick={() => setSelectedSlot(slot)}
              >
                {new Date(slot).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </button>
            ))}
          </div>
        </div>

        {book.isError && <p className="form-error">{apiErrorMessage(book.error)}</p>}

        <button
          type="button"
          onClick={handleBook}
          disabled={!patientId || !selectedSlot || book.isPending}
        >
          {book.isPending ? "Booking…" : "Book appointment"}
        </button>
      </div>
    </div>
  );
}
