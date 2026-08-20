import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuthStore } from "../../lib/auth-store";
import { useVisits } from "./hooks";

const STATUS_LABELS: Record<string, string> = {
  in_progress: "In Progress",
  completed: "Completed",
};

export function VisitsListPage() {
  const [status, setStatus] = useState("in_progress");
  const { data, isLoading } = useVisits(status || undefined);
  const canStart = useAuthStore((s) => s.hasPermission("opd.visit.create"));

  return (
    <div>
      <div className="page-header">
        <h1>OPD Visits</h1>
        {canStart && (
          <Link to="/opd/new" className="button-primary">
            + Start visit
          </Link>
        )}
      </div>

      <div className="filter-row">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All</option>
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
              <th>Checked in</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.results.length === 0 && (
              <tr>
                <td colSpan={3}>No visits found.</td>
              </tr>
            )}
            {data.results.map((visit) => (
              <tr key={visit.id}>
                <td>{new Date(visit.checked_in_at).toLocaleString()}</td>
                <td>
                  <span className={`status-pill status-${visit.status}`}>
                    {STATUS_LABELS[visit.status]}
                  </span>
                </td>
                <td>
                  <Link to={`/opd/${visit.id}`}>Open consultation</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
