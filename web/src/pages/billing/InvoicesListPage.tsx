import { Link } from "react-router-dom";

import { useInvoices } from "./hooks";

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  pending_confirmation: "Pending Confirmation",
  paid: "Paid",
  partially_paid: "Partially Paid",
  written_off: "Written Off",
};

export function InvoicesListPage() {
  const { data, isLoading } = useInvoices();

  return (
    <div>
      <div className="page-header">
        <h1>Billing</h1>
      </div>

      {isLoading && <p>Loading…</p>}

      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Status</th>
              <th>Total</th>
              <th>Balance</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data.results.length === 0 && (
              <tr>
                <td colSpan={5}>No invoices found.</td>
              </tr>
            )}
            {data.results.map((invoice) => (
              <tr key={invoice.id}>
                <td>{invoice.invoice_number}</td>
                <td>
                  <span className={`status-pill status-${invoice.status}`}>
                    {STATUS_LABELS[invoice.status]}
                  </span>
                </td>
                <td>{invoice.total}</td>
                <td>{invoice.balance}</td>
                <td>
                  <Link to={`/billing/${invoice.id}`}>Open</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
