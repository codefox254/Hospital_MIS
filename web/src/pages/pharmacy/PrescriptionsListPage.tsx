import { Link } from "react-router-dom";

import { usePrescriptions } from "./hooks";

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  partially_dispensed: "Partially Dispensed",
  dispensed: "Dispensed",
  cancelled: "Cancelled",
};

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
        <table className="data-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Items</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.results.length === 0 && (
              <tr>
                <td colSpan={3}>No prescriptions found.</td>
              </tr>
            )}
            {data.results.map((rx) => (
              <tr key={rx.id}>
                <td>
                  <span className={`status-pill status-${rx.status}`}>{STATUS_LABELS[rx.status]}</span>
                </td>
                <td>{rx.items.length} item(s)</td>
                <td>
                  <Link to={`/pharmacy/${rx.id}`}>Open</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
