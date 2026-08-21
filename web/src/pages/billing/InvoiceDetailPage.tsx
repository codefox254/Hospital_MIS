import { useState } from "react";
import { useParams } from "react-router-dom";

import { apiErrorMessage } from "../../lib/api";
import { useAuthStore } from "../../lib/auth-store";
import { usePatientName } from "../../lib/useLookups";
import { formatStatusLabel, pillClass } from "../../lib/statusPill";
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

const PAYMENT_RAILS: { method: PaymentMethod; label: string; icon: string; className: string }[] = [
  { method: "cash", label: "Cash", icon: "💵", className: "cash" },
  { method: "card", label: "Card", icon: "💳", className: "card" },
  { method: "bank", label: "Bank", icon: "🏦", className: "bank" },
  { method: "insurance", label: "Insurance", icon: "🛡️", className: "insurance" },
];

function paymentIconFor(method: string) {
  if (method === "mpesa") return { icon: "📱", className: "mpesa", label: "M-Pesa" };
  const rail = PAYMENT_RAILS.find((r) => r.method === method);
  return rail
    ? { icon: rail.icon, className: rail.className, label: rail.label }
    : { icon: "💰", className: "cash", label: formatStatusLabel(method) };
}

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const hasPermission = useAuthStore((s) => s.hasPermission);

  const { data: invoice } = useInvoice(id);
  const { data: payments } = usePayments(id);
  const { data: refunds } = useRefunds(id);
  const { data: patientName } = usePatientName(invoice?.patient);

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
      <div className="invoice-header-card">
        <div className="card-row">
          <div>
            <p className="invoice-number">{invoice.invoice_number}</p>
            <p className="invoice-patient">{patientName ?? "…"}</p>
          </div>
          <span className={pillClass(invoice.status)}>
            {STATUS_LABELS[invoice.status] ?? formatStatusLabel(invoice.status)}
          </span>
        </div>
        <div className="invoice-totals-row">
          <div>
            <span className="invoice-totals-label">Total</span>
            <span className="invoice-totals-value">{invoice.total}</span>
          </div>
          <div>
            <span className="invoice-totals-label">Balance</span>
            <span className="invoice-totals-value">{invoice.balance}</span>
          </div>
        </div>
      </div>

      <section className="consult-section">
        <h2>Line items</h2>
        <div className="card-list">
          {invoice.line_items.length === 0 && <p className="card-subtitle">No line items yet.</p>}
          {invoice.line_items.map((li) => (
            <div key={li.id} className="modern-card">
              <div className="card-body">
                <div className="card-row">
                  <p className="card-title">{li.description}</p>
                  <p className="card-title">{li.amount}</p>
                </div>
                <p className="card-meta">
                  {formatStatusLabel(li.source_module)} · Qty {li.quantity} · @ {li.unit_price}
                </p>
              </div>
            </div>
          ))}
        </div>
        <p className="muted" style={{ marginTop: "0.75rem" }}>
          Subtotal {invoice.subtotal} — Discount {invoice.discount} — Tax {invoice.tax}
        </p>
      </section>

      {!settled && hasPermission("billing.payment.create") && (
        <section className="consult-section">
          <h2>Record payment</h2>
          <div className="payment-rail-grid">
            {PAYMENT_RAILS.map((rail) => (
              <button
                key={rail.method}
                type="button"
                className={method === rail.method ? "payment-rail-tile selected" : "payment-rail-tile"}
                onClick={() => setMethod(rail.method)}
              >
                <span className={`payment-icon ${rail.className}`}>{rail.icon}</span>
                {rail.label}
              </button>
            ))}
          </div>
          <div className="vitals-form">
            <input placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <button
              type="button"
              disabled={!amount || recordPayment.isPending}
              onClick={() => recordPayment.mutate({ method, amount }, { onSuccess: () => setAmount("") })}
            >
              Record {PAYMENT_RAILS.find((r) => r.method === method)?.label.toLowerCase()} payment
            </button>
          </div>
          {recordPayment.isError && <p className="form-error">{apiErrorMessage(recordPayment.error)}</p>}

          <h2 style={{ marginTop: "1.5rem" }}>
            <span className="payment-icon mpesa" style={{ marginRight: "0.5rem" }}>
              📱
            </span>
            Or pay via M-Pesa
          </h2>
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
        <div className="card-list">
          {payments?.map((p) => {
            const rail = paymentIconFor(p.method);
            return (
              <div key={p.id} className="modern-card">
                <span className={`payment-icon ${rail.className}`}>{rail.icon}</span>
                <div className="card-body">
                  <div className="card-row">
                    <p className="card-title">{rail.label}</p>
                    <p className="card-title">{p.amount}</p>
                  </div>
                  <div className="card-row">
                    <p className="card-meta">{new Date(p.received_at).toLocaleString()}</p>
                    <span className={pillClass(p.status)}>{formatStatusLabel(p.status)}</span>
                  </div>
                </div>
              </div>
            );
          })}
          {payments?.length === 0 && <p className="card-subtitle">No payments yet.</p>}
        </div>
      </section>

      {settled && confirmedPayments.length > 0 ? (
        <ReceiptPanel
          invoiceNumber={invoice.invoice_number}
          patientName={patientName ?? ""}
          lineItems={invoice.line_items}
          payments={confirmedPayments}
          total={invoice.total}
        />
      ) : null}

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
          <div className="card-list" style={{ marginTop: "0.75rem" }}>
            {refunds?.map((r) => (
              <div key={r.id} className="modern-card">
                <div className="card-body">
                  <div className="card-row">
                    <p className="card-title">{r.amount}</p>
                    <p className="card-meta">{new Date(r.approved_at).toLocaleString()}</p>
                  </div>
                  <p className="card-meta">{r.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ReceiptPanel({
  invoiceNumber,
  patientName,
  lineItems,
  payments,
  total,
}: {
  invoiceNumber: string;
  patientName: string;
  lineItems: { id: string; description: string; quantity: number; amount: string }[];
  payments: { id: string; method: string; amount: string; received_at: string }[];
  total: string;
}) {
  return (
    <section className="consult-section receipt-section">
      <div className="page-header">
        <h2>Receipt</h2>
        <button type="button" className="button-primary" onClick={() => window.print()}>
          Print receipt
        </button>
      </div>
      <div className="receipt-paper" id="receipt-printable">
        <p className="receipt-brand">FDO Hospital</p>
        <p className="receipt-meta">Invoice {invoiceNumber}</p>
        <p className="receipt-meta">{patientName}</p>
        <p className="receipt-meta">{new Date().toLocaleString()}</p>
        <hr />
        {lineItems.map((li) => (
          <div key={li.id} className="receipt-row">
            <span>
              {li.description} × {li.quantity}
            </span>
            <span>{li.amount}</span>
          </div>
        ))}
        <hr />
        {payments.map((p) => (
          <div key={p.id} className="receipt-row muted">
            <span>Paid via {formatStatusLabel(p.method)}</span>
            <span>{p.amount}</span>
          </div>
        ))}
        <hr />
        <div className="receipt-row receipt-total">
          <span>Total paid</span>
          <span>{total}</span>
        </div>
      </div>
    </section>
  );
}
