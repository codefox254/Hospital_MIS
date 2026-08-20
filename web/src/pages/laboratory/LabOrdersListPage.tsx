import { Link } from "react-router-dom";

import { useAuthStore } from "../../lib/auth-store";
import { useLabOrders } from "./hooks";

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  collected: "Collected",
  processing: "Processing",
  completed: "Completed",
};

export function LabOrdersListPage() {
  const { data, isLoading } = useLabOrders();
  const canCreate = useAuthStore((s) => s.hasPermission("laboratory.lab_order.create"));

  return (
    <div>
      <div className="page-header">
        <h1>Laboratory</h1>
        {canCreate && (
          <Link to="/laboratory/new" className="button-primary">
            + Order tests
          </Link>
        )}
      </div>

      {isLoading && <p>Loading…</p>}

      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Ordered</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Tests</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.results.length === 0 && (
              <tr>
                <td colSpan={5}>No lab orders found.</td>
              </tr>
            )}
            {data.results.map((order) => (
              <tr key={order.id}>
                <td>{new Date(order.ordered_at).toLocaleString()}</td>
                <td>{order.priority}</td>
                <td>
                  <span className={`status-pill status-${order.status}`}>
                    {STATUS_LABELS[order.status]}
                  </span>
                </td>
                <td>{order.items.map((i) => i.test_code).join(", ")}</td>
                <td>
                  <Link to={`/laboratory/${order.id}`}>Open</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
