import { useState } from "react";
import { useParams } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { useAuthStore } from "../../lib/auth-store";
import {
  useApproveRefund,
  useInvoice,
  useMpesaStkPush,
  usePayments,
  useRecordPayment,
  useRefunds,
} from "./hooks";
import type { PaymentMethod } from "../../types/billing";

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  pending_confirmation: "Pending Confirmation",
  paid: "Paid",
  partially_paid: "Partially Paid",
  written_off: "Written Off",
};

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const hasPermission = useAuthStore((s) => s.hasPermission);

  const { data: invoice } = useInvoice(id);
  const { data: payments } = usePayments(id);
  const { data: refunds } = useRefunds(id);

  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [amount, setAmount] = useState("");
  const [phone, setPhone] = useState("");
  const recordPayment = useRecordPayment(id ?? "");
  const stkPush = useMpesaStkPush(id ?? "");

  const [refundPaymentId, setRefundPaymentId] = useState("");
  const [refundAmount, setRefundAmount] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const approveRefund = useApproveRefund(id ?? "");

  if (!invoice) return <p>Loading…</p>;

  const settled = invoice.balance === "0.00";
  const confirmedPayments = payments?.filter((p) => p.status === "confirmed") ?? [];

  return (
    <div className="consultation-workspace">
      <div className="page-header">
        <h1>{invoice.invoice_number}</h1>
        <span className={`status-pill status-${invoice.status}`}>{STATUS_LABELS[invoice.status]}</span>
      </div>

      <section className="consult-section">
        <h2>Line items</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Description</th>
              <th>Module</th>
              <th>Qty</th>
              <th>Unit price</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {invoice.line_items.length === 0 && (
              <tr>
                <td colSpan={5}>No line items yet.</td>
              </tr>
            )}
            {invoice.line_items.map((li) => (
              <tr key={li.id}>
                <td>{li.description}</td>
                <td>{li.source_module}</td>
                <td>{li.quantity}</td>
                <td>{li.unit_price}</td>
                <td>{li.amount}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted" style={{ marginTop: "0.75rem" }}>
          Subtotal {invoice.subtotal} — Discount {invoice.discount} — Tax {invoice.tax} —{" "}
          <strong>Total {invoice.total}</strong> — Balance <strong>{invoice.balance}</strong>
        </p>
      </section>

      {!settled && hasPermission("billing.payment.create") && (
        <section className="consult-section">
          <h2>Record payment</h2>
          <div className="vitals-form">
            <select value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)}>
              <option value="cash">Cash</option>
              <option value="card">Card</option>
              <option value="bank">Bank</option>
              <option value="insurance">Insurance</option>
            </select>
            <input placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <button
              type="button"
              disabled={!amount || recordPayment.isPending}
              onClick={() => recordPayment.mutate({ method, amount }, { onSuccess: () => setAmount("") })}
            >
              Record payment
            </button>
          </div>
          {recordPayment.isError && <p className="form-error">{apiErrorMessage(recordPayment.error)}</p>}

          <h2 style={{ marginTop: "1.5rem" }}>Or pay via M-Pesa</h2>
          <div className="vitals-form">
            <input placeholder="Phone (2547XXXXXXXX)" value={phone} onChange={(e) => setPhone(e.target.value)} />
            <input placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <button
              type="button"
              disabled={!phone || !amount || stkPush.isPending || invoice.status === "pending_confirmation"}
              onClick={() => stkPush.mutate({ phone_number: phone, amount })}
            >
              {stkPush.isPending ? "Sending…" : "Send STK push"}
            </button>
          </div>
          {invoice.status === "pending_confirmation" && (
            <p className="muted">Waiting for M-Pesa confirmation… (polling every 3s)</p>
          )}
          {stkPush.isError && <p className="form-error">{apiErrorMessage(stkPush.error)}</p>}
        </section>
      )}

      <section className="consult-section">
        <h2>Payments</h2>
        <ul className="diagnosis-list">
          {payments?.map((p) => (
            <li key={p.id}>
              {p.method} {p.amount} — <span className="muted">{p.status}</span>
            </li>
          ))}
          {payments?.length === 0 && <li className="muted">No payments yet.</li>}
        </ul>
      </section>

      {hasPermission("billing.refund.create") && confirmedPayments.length > 0 && (
        <section className="consult-section">
          <h2>Approve a refund</h2>
          <div className="vitals-form">
            <select value={refundPaymentId} onChange={(e) => setRefundPaymentId(e.target.value)}>
              <option value="">Select a payment</option>
              {confirmedPayments.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.method} {p.amount}
                </option>
              ))}
            </select>
            <input placeholder="Refund amount" value={refundAmount} onChange={(e) => setRefundAmount(e.target.value)} />
            <input placeholder="Reason" value={refundReason} onChange={(e) => setRefundReason(e.target.value)} />
            <button
              type="button"
              disabled={!refundPaymentId || !refundAmount || !refundReason || approveRefund.isPending}
              onClick={() =>
                approveRefund.mutate(
                  { payment: refundPaymentId, amount: refundAmount, reason: refundReason },
                  { onSuccess: () => { setRefundAmount(""); setRefundReason(""); setRefundPaymentId(""); } },
                )
              }
            >
              Approve refund
            </button>
          </div>
          {approveRefund.isError && <p className="form-error">{apiErrorMessage(approveRefund.error)}</p>}
          <ul className="diagnosis-list" style={{ marginTop: "0.75rem" }}>
            {refunds?.map((r) => (
              <li key={r.id}>
                {r.amount} — {r.reason}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
