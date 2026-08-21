export interface InvoiceLineItem {
  id: string;
  source_module: string;
  description: string;
  quantity: number;
  unit_price: string;
  amount: string;
}

export interface Payment {
  id: string;
  invoice: string;
  method: string;
  amount: string;
  reference: string;
  status: string;
  received_at: string;
}

export interface Invoice {
  id: string;
  patient: string;
  visit: string | null;
  invoice_number: string;
  status: string;
  subtotal: string;
  discount: string;
  tax: string;
  total: string;
  balance: string;
  line_items: InvoiceLineItem[];
  created_at: string;
}
