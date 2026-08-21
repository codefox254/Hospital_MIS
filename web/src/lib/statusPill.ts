/** Maps a status/priority string to one of index.css's `.pill-*` classes —
 * shared across every module's list/detail views so the same status name
 * always reads as the same color, not redecided per page. */
const PILL_CLASS: Record<string, string> = {
  scheduled: "pill-info",
  checked_in: "pill-warning",
  in_consultation: "pill-info",
  in_progress: "pill-warning",
  completed: "pill-success",
  cancelled: "pill-danger",
  no_show: "pill-neutral",
  pending: "pill-neutral",
  collected: "pill-info",
  processing: "pill-warning",
  received: "pill-info",
  rejected: "pill-danger",
  entered: "pill-warning",
  verified: "pill-success",
  amended: "pill-warning",
  open: "pill-info",
  pending_confirmation: "pill-warning",
  paid: "pill-success",
  partially_paid: "pill-warning",
  written_off: "pill-neutral",
  confirmed: "pill-success",
  failed: "pill-danger",
  refunded: "pill-warning",
  routine: "pill-neutral",
  urgent: "pill-warning",
  emergency: "pill-danger",
  stat: "pill-danger",
  active: "pill-success",
  inactive: "pill-neutral",
  partially_dispensed: "pill-warning",
  dispensed: "pill-success",
};

export function pillClass(status: string): string {
  return `pill ${PILL_CLASS[status] ?? "pill-neutral"}`;
}

export function formatStatusLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
