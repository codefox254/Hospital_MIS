export interface Appointment {
  id: string;
  patient: string;
  doctor: string;
  department: string;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
  booking_channel: string;
}

export interface LabOrderItem {
  id: string;
  test_code: string;
  test_name: string;
}

export interface LabOrder {
  id: string;
  visit: string;
  priority: string;
  status: string;
  ordered_at: string;
  items: LabOrderItem[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
