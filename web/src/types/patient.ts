export type Gender = "male" | "female" | "other" | "unspecified";

export interface Patient {
  id: string;
  facility: string;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: Gender;
  national_id: string;
  phone: string;
  email: string;
  photo_url: string;
  blood_group: string;
  is_provisional: boolean;
  merged_into_patient: string | null;
  is_merged: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface NewPatientInput {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: Gender;
  national_id?: string;
  phone?: string;
  email?: string;
  blood_group?: string;
  is_provisional?: boolean;
}
