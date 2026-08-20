import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuthStore } from "../../lib/auth-store";
import { useDepartments } from "../../lib/useLookups";
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

export function AppointmentsListPage() {
  const user = useAuthStore((s) => s.user);
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const [status, setStatus] = useState("");
  const [selectedDepartment, setSelectedDepartment] = useState<string>("");

  const { data: departments } = useDepartments();
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
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Status</th>
                <th>Channel</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.results.length === 0 && (
                <tr>
                  <td colSpan={4}>No appointments found.</td>
                </tr>
              )}
              {data.results.map((appt) => (
                <tr key={appt.id}>
                  <td>{new Date(appt.scheduled_at).toLocaleString()}</td>
                  <td>
                    <span className={`status-pill status-${appt.status}`}>
                      {STATUS_LABELS[appt.status]}
                    </span>
                  </td>
                  <td>{appt.booking_channel}</td>
                  <td className="row-actions">
                    {canCheckIn && appt.status === "scheduled" && (
                      <button type="button" onClick={() => checkIn.mutate(appt.id)}>
                        Check in
                      </button>
                    )}
                    {canCancel &&
                      !["cancelled", "completed", "no_show"].includes(appt.status) && (
                        <button type="button" onClick={() => cancel.mutate(appt.id)}>
                          Cancel
                        </button>
                      )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
              <span className={`priority-${entry.priority}`}>{entry.priority}</span>
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
