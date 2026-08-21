import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuthStore } from "../../lib/auth-store";
import { useDepartments, usePatientName, useStaffUsers, staffName } from "../../lib/useLookups";
import { formatStatusLabel, pillClass } from "../../lib/statusPill";
import type { Appointment } from "../../types/appointment";
import {
  useAppointments,
  useCallNext,
  useCancelAppointment,
  useCheckIn,
  useQueueEntries,
} from "./hooks";
import { useQueueSocket } from "./useQueueSocket";

const STATUS_LABELS: Record<string, string> = {
  scheduled: "Scheduled",
  checked_in: "Checked In",
  in_consultation: "In Consultation",
  completed: "Completed",
  no_show: "No Show",
  cancelled: "Cancelled",
};

function AppointmentCard({
  appt,
  doctorName,
  departmentName,
  canCheckIn,
  canCancel,
  onCheckIn,
  onCancel,
}: {
  appt: Appointment;
  doctorName: string;
  departmentName: string;
  canCheckIn: boolean;
  canCancel: boolean;
  onCheckIn: () => void;
  onCancel: () => void;
}) {
  const { data: patientName } = usePatientName(appt.patient);
  const date = new Date(appt.scheduled_at);

  return (
    <div className="modern-card">
      <div className="icon-badge">📅</div>
      <div className="card-body">
        <div className="card-row">
          <p className="card-title">
            {date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}{" "}
            &middot; {date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
          </p>
          <span className={pillClass(appt.status)}>
            {STATUS_LABELS[appt.status] ?? formatStatusLabel(appt.status)}
          </span>
        </div>
        <p className="card-subtitle">{patientName ?? "…"}</p>
        <p className="card-meta">
          {doctorName} · {departmentName} · {appt.duration_minutes} min ·{" "}
          {formatStatusLabel(appt.booking_channel)}
        </p>
      </div>
      <div className="row-actions">
        {canCheckIn && appt.status === "scheduled" && (
          <button type="button" onClick={onCheckIn}>
            Check in
          </button>
        )}
        {canCancel && !["cancelled", "completed", "no_show"].includes(appt.status) && (
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

export function AppointmentsListPage() {
  const user = useAuthStore((s) => s.user);
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const [status, setStatus] = useState("");
  const [selectedDepartment, setSelectedDepartment] = useState<string>("");

  const { data: departments } = useDepartments();
  const { data: staff } = useStaffUsers();
  const department = selectedDepartment || departments?.[0]?.id || "";

  const { data, isLoading } = useAppointments({ status: status || undefined });
  const { data: queue } = useQueueEntries(department);
  useQueueSocket(user?.facility.id, department);

  const checkIn = useCheckIn();
  const cancel = useCancelAppointment();
  const callNext = useCallNext();

  const canCheckIn = hasPermission("appointments.appointment.check_in");
  const canCancel = hasPermission("appointments.appointment.update");
  const canCall = hasPermission("appointments.queue.call");

  const departmentName = (id: string) => departments?.find((d) => d.id === id)?.name ?? "—";
  const doctorName = (id: string) => {
    const u = staff?.find((s) => s.id === id);
    return u ? staffName(u) : "—";
  };

  return (
    <div className="appointments-layout">
      <div>
        <div className="page-header">
          <h1>Appointments</h1>
          {hasPermission("appointments.appointment.create") && (
            <Link to="/appointments/new" className="button-primary">
              + Book appointment
            </Link>
          )}
        </div>

        <div className="filter-row">
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {isLoading && <p>Loading…</p>}

        {data && (
          <div className="card-list">
            {data.results.length === 0 && <p className="card-subtitle">No appointments found.</p>}
            {data.results.map((appt) => (
              <AppointmentCard
                key={appt.id}
                appt={appt}
                doctorName={doctorName(appt.doctor)}
                departmentName={departmentName(appt.department)}
                canCheckIn={canCheckIn}
                canCancel={canCancel}
                onCheckIn={() => checkIn.mutate(appt.id)}
                onCancel={() => cancel.mutate(appt.id)}
              />
            ))}
          </div>
        )}
      </div>

      <aside className="queue-panel">
        <h2>Live queue</h2>
        <select value={department} onChange={(e) => setSelectedDepartment(e.target.value)}>
          {departments?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        <ol className="queue-list">
          {queue?.length === 0 && <p>No one in queue.</p>}
          {queue?.map((entry) => (
            <li key={entry.id} className={entry.called_at ? "queue-called" : ""}>
              <span className="queue-number">#{entry.queue_number}</span>
              <span
                className={
                  entry.priority === "emergency"
                    ? "pill pill-danger"
                    : entry.priority === "priority"
                      ? "pill pill-warning"
                      : "pill pill-neutral"
                }
              >
                {entry.priority}
              </span>
              {canCall && !entry.called_at && (
                <button type="button" onClick={() => callNext.mutate(entry.id)}>
                  Call
                </button>
              )}
              {entry.called_at && <span className="called-badge">Called</span>}
            </li>
          ))}
        </ol>
      </aside>
    </div>
  );
}
