export interface Drug {
  id: string;
  name: string;
  generic_name: string;
  form: string;
  strength: string;
  is_controlled: boolean;
}

export interface StockBatch {
  id: string;
  facility: string;
  drug: string;
  batch_number: string;
  expiry_date: string;
  quantity_on_hand: number;
  unit_cost: string | null;
}

export type PrescriptionStatus = "pending" | "partially_dispensed" | "dispensed" | "cancelled";

export interface PrescriptionItem {
  id: string;
  prescription: string;
  drug: string;
  dosage: string;
  frequency: string;
  duration_days: number | null;
  qty_prescribed: number;
}

export interface Prescription {
  id: string;
  consultation: string;
  patient: string;
  prescribed_by: string;
  status: PrescriptionStatus;
  items: PrescriptionItem[];
}

export interface CreatePrescriptionInput {
  consultation: string;
  items: {
    drug: string;
    dosage: string;
    frequency: string;
    duration_days?: number;
    qty_prescribed: number;
  }[];
}

export interface DispenseRecord {
  id: string;
  prescription_item: string;
  batch: string;
  dispensed_by: string;
  qty_dispensed: number;
  dispensed_at: string;
}

export interface AllergyConflict {
  substance: string;
  reaction: string;
}
