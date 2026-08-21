import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuthStore } from "../../lib/auth-store";
import { useDepartments, usePatientName, useStaffUsers, staffName } from "../../lib/useLookups";
import { formatStatusLabel, pillClass } from "../../lib/statusPill";
import type { Visit } from "../../types/opd";
import { useVisits } from "./hooks";

const STATUS_LABELS: Record<string, string> = {
  in_progress: "In Progress",
  completed: "Completed",
};

function VisitCard({
  visit,
  doctorName,
  departmentName,
}: {
  visit: Visit;
  doctorName: string;
  departmentName: string;
}) {
  const { data: patientName } = usePatientName(visit.patient);
  return (
    <Link to={`/opd/${visit.id}`} className="modern-card clickable">
      <div className="icon-badge">🩺</div>
      <div className="card-body">
        <div className="card-row">
          <p className="card-title">{patientName ?? "…"}</p>
          <span className={pillClass(visit.status)}>
            {STATUS_LABELS[visit.status] ?? formatStatusLabel(visit.status)}
          </span>
        </div>
        <p className="card-subtitle">{new Date(visit.checked_in_at).toLocaleString()}</p>
        <p className="card-meta">
          {doctorName} · {departmentName}
        </p>
      </div>
    </Link>
  );
}

export function VisitsListPage() {
  const [status, setStatus] = useState("in_progress");
  const { data, isLoading } = useVisits(status || undefined);
  const { data: departments } = useDepartments();
  const { data: staff } = useStaffUsers();
  const canStart = useAuthStore((s) => s.hasPermission("opd.visit.create"));

  const departmentName = (id: string) => departments?.find((d) => d.id === id)?.name ?? "—";
  const doctorName = (id: string) => {
    const u = staff?.find((s) => s.id === id);
    return u ? staffName(u) : "—";
  };

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
        <div className="card-list">
          {data.results.length === 0 && <p className="card-subtitle">No visits found.</p>}
          {data.results.map((visit) => (
            <VisitCard
              key={visit.id}
              visit={visit}
              doctorName={doctorName(visit.doctor)}
              departmentName={departmentName(visit.department)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
