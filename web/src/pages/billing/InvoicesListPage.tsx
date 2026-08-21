import { Link } from "react-router-dom";

import { usePatientName } from "../../lib/useLookups";
import { formatStatusLabel, pillClass } from "../../lib/statusPill";
import type { Invoice } from "../../types/billing";
import { useInvoices } from "./hooks";

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  pending_confirmation: "Pending Confirmation",
  paid: "Paid",
  partially_paid: "Partially Paid",
  written_off: "Written Off",
};

function InvoiceCard({ invoice }: { invoice: Invoice }) {
  const { data: patientName } = usePatientName(invoice.patient);
  return (
    <Link to={`/billing/${invoice.id}`} className="modern-card clickable">
      <div className="icon-badge">🧾</div>
      <div className="card-body">
        <div className="card-row">
          <p className="card-title">{invoice.invoice_number}</p>
          <span className={pillClass(invoice.status)}>
            {STATUS_LABELS[invoice.status] ?? formatStatusLabel(invoice.status)}
          </span>
        </div>
        <p className="card-subtitle">{patientName ?? "…"}</p>
        <p className="card-meta">
          Total {invoice.total} · Balance {invoice.balance}
        </p>
      </div>
    </Link>
  );
}

export function InvoicesListPage() {
  const { data, isLoading } = useInvoices();

  return (
    <div>
      <div className="page-header">
        <h1>Billing</h1>
      </div>

      {isLoading && <p>Loading…</p>}

      {data && (
        <div className="card-list">
          {data.results.length === 0 && <p className="card-subtitle">No invoices found.</p>}
          {data.results.map((invoice) => (
            <InvoiceCard key={invoice.id} invoice={invoice} />
          ))}
        </div>
      )}
    </div>
  );
}
