import { Link } from "react-router-dom";

import { useAuthStore } from "../../lib/auth-store";
import { formatStatusLabel, pillClass } from "../../lib/statusPill";
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
        <div className="card-list">
          {data.results.length === 0 && <p className="card-subtitle">No lab orders found.</p>}
          {data.results.map((order) => (
            <Link key={order.id} to={`/laboratory/${order.id}`} className="modern-card clickable">
              <div className="icon-badge">🧪</div>
              <div className="card-body">
                <div className="card-row">
                  <p className="card-title">{new Date(order.ordered_at).toLocaleString()}</p>
                  <div style={{ display: "flex", gap: "0.4rem" }}>
                    {order.priority !== "routine" && (
                      <span className={pillClass(order.priority)}>
                        {formatStatusLabel(order.priority)}
                      </span>
                    )}
                    <span className={pillClass(order.status)}>
                      {STATUS_LABELS[order.status] ?? formatStatusLabel(order.status)}
                    </span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginTop: "0.5rem" }}>
                  {order.items.map((i) => (
                    <span key={i.id} className="chip">
                      {i.test_name}
                    </span>
                  ))}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
