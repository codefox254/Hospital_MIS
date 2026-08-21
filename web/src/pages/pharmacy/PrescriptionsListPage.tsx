import { Link } from "react-router-dom";

import { usePatientName } from "../../lib/useLookups";
import { formatStatusLabel, pillClass } from "../../lib/statusPill";
import type { Prescription } from "../../types/pharmacy";
import { usePrescriptions } from "./hooks";

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  partially_dispensed: "Partially Dispensed",
  dispensed: "Dispensed",
  cancelled: "Cancelled",
};

function PrescriptionCard({ rx }: { rx: Prescription }) {
  const { data: patientName } = usePatientName(rx.patient);
  return (
    <Link to={`/pharmacy/${rx.id}`} className="modern-card clickable">
      <div className="icon-badge">💊</div>
      <div className="card-body">
        <div className="card-row">
          <p className="card-title">{patientName ?? "…"}</p>
          <span className={pillClass(rx.status)}>
            {STATUS_LABELS[rx.status] ?? formatStatusLabel(rx.status)}
          </span>
        </div>
        <p className="card-meta">{rx.items.length} item(s)</p>
      </div>
    </Link>
  );
}

export function PrescriptionsListPage() {
  const { data, isLoading } = usePrescriptions();

  return (
    <div>
      <div className="page-header">
        <h1>Pharmacy</h1>
        <Link to="/pharmacy/catalog" className="button-primary">
          Drugs &amp; stock
        </Link>
      </div>

      {isLoading && <p>Loading…</p>}

      {data && (
        <div className="card-list">
          {data.results.length === 0 && <p className="card-subtitle">No prescriptions found.</p>}
          {data.results.map((rx) => (
            <PrescriptionCard key={rx.id} rx={rx} />
          ))}
        </div>
      )}
    </div>
  );
}
