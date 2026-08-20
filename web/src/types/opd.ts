export type VisitStatus = "in_progress" | "completed";

export interface Visit {
  id: string;
  facility: string;
  patient: string;
  appointment: string | null;
  doctor: string;
  department: string;
  status: VisitStatus;
  checked_in_at: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface StartVisitInput {
  patient: string;
  doctor: string;
  department: string;
  appointment?: string;
}

export interface Vitals {
  id: string;
  visit: string;
  recorded_by: string;
  bp_systolic: number | null;
  bp_diastolic: number | null;
  pulse: number | null;
  temperature_c: string | null;
  respiration_rate: number | null;
  spo2_percent: number | null;
  weight_kg: string | null;
  height_cm: string | null;
  recorded_at: string;
}

export interface Consultation {
  id: string;
  visit: string;
  chief_complaint: string;
  history_of_present_illness: string;
  examination_notes: string;
  is_draft: boolean;
  locked_at: string | null;
  signed_by: string | null;
  created_at: string;
  updated_at: string;
}

export type DiagnosisType = "primary" | "secondary" | "differential";

export interface Diagnosis {
  id: string;
  consultation: string;
  icd_code: string;
  description: string;
  type: DiagnosisType;
}

export interface ConsultationAddendum {
  id: string;
  consultation: string;
  author: string;
  text: string;
  created_at: string;
}
