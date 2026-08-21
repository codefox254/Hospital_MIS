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
  ordered_by: string;
  priority: string;
  status: string;
  ordered_at: string;
  items: LabOrderItem[];
}

export interface LabResultValue {
  id: string;
  parameter: string;
  value: string;
  unit: string;
  reference_range: string;
  flag: string;
}

export interface LabResult {
  id: string;
  lab_order_item: string;
  status: string;
  is_critical: boolean;
  entered_at: string | null;
  verified_at: string | null;
  values: LabResultValue[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
