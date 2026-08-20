export interface Department {
  id: string;
  facility: string;
  name: string;
  code: string;
  parent_department: string | null;
}

export interface StaffUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}
