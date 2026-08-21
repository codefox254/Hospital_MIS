export interface Facility {
  id: string;
  name: string;
  code: string;
  type: "clinic" | "hospital" | "branch";
  address: string;
  phone: string;
  is_active: boolean;
  created_at: string;
}

export interface FacilityStats {
  id: string;
  name: string;
  code: string;
  type: string;
  is_active: boolean;
  patient_count: number;
  active_user_count: number;
  appointments_today: number;
}

export interface CreateUserInput {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  phone?: string;
  facility?: string;
  role?: string;
}
