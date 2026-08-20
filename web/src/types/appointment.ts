export type AppointmentStatus =
  | "scheduled"
  | "checked_in"
  | "in_consultation"
  | "completed"
  | "no_show"
  | "cancelled";

export type BookingChannel = "web" | "mobile" | "walk_in";

export interface Appointment {
  id: string;
  facility: string;
  patient: string;
  doctor: string;
  department: string;
  scheduled_at: string;
  duration_minutes: number;
  status: AppointmentStatus;
  booking_channel: BookingChannel;
  created_by: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BookAppointmentInput {
  patient: string;
  doctor: string;
  department: string;
  scheduled_at: string;
  duration_minutes: number;
  booking_channel: BookingChannel;
}

export interface QueueEntry {
  id: string;
  appointment: string;
  queue_number: number;
  priority: "normal" | "priority" | "emergency";
  called_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DoctorScheduleSummary {
  id: string;
  doctor: string;
  department: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
}
