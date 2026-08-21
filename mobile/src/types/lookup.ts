export interface Department {
  id: string;
  name: string;
}

export interface StaffUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface PatientLite {
  id: string;
  mrn: string;
  first_name: string;
  last_name: string;
}
