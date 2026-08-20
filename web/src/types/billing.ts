export type InvoiceStatus = "open" | "pending_confirmation" | "paid" | "partially_paid" | "written_off";

export interface InvoiceLineItem {
  id: string;
  invoice: string;
  source_module: string;
  source_reference_id: string;
  description: string;
  quantity: number;
  unit_price: string;
  amount: string;
}

export interface Invoice {
  id: string;
  facility: string;
  patient: string;
  visit: string | null;
  invoice_number: string;
  status: InvoiceStatus;
  subtotal: string;
  discount: string;
  tax: string;
  total: string;
  balance: string;
  created_by: string;
  line_items: InvoiceLineItem[];
}

export type PaymentMethod = "cash" | "card" | "bank" | "insurance";
export type PaymentStatus = "pending" | "confirmed" | "failed" | "refunded";

export interface Payment {
  id: string;
  invoice: string;
  method: PaymentMethod | "mpesa";
  amount: string;
  reference: string;
  status: PaymentStatus;
  received_by: string | null;
  received_at: string;
}

export interface MpesaTransaction {
  id: string;
  payment: string;
  checkout_request_id: string;
  mpesa_receipt_number: string;
  phone_number: string;
  status: "requested" | "confirmed" | "failed";
}

export interface Refund {
  id: string;
  invoice: string;
  payment: string;
  amount: string;
  reason: string;
  approved_by: string;
  approved_at: string;
}
