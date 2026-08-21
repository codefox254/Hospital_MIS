export interface StatusStyle {
  bg: string;
  fg: string;
}

const PALETTE: Record<string, StatusStyle> = {
  scheduled: { bg: "#dbeafe", fg: "#1d4ed8" },
  checked_in: { bg: "#fef3c7", fg: "#b45309" },
  completed: { bg: "#dcfce7", fg: "#15803d" },
  cancelled: { bg: "#fee2e2", fg: "#b91c1c" },
  no_show: { bg: "#f3f4f6", fg: "#4b5563" },
  pending: { bg: "#f3f4f6", fg: "#4b5563" },
  collected: { bg: "#e0e7ff", fg: "#4338ca" },
  processing: { bg: "#fef3c7", fg: "#b45309" },
  received: { bg: "#e0e7ff", fg: "#4338ca" },
  rejected: { bg: "#fee2e2", fg: "#b91c1c" },
  entered: { bg: "#fef3c7", fg: "#b45309" },
  verified: { bg: "#dcfce7", fg: "#15803d" },
  amended: { bg: "#ffedd5", fg: "#c2410c" },
  open: { bg: "#dbeafe", fg: "#1d4ed8" },
  pending_confirmation: { bg: "#fef3c7", fg: "#b45309" },
  paid: { bg: "#dcfce7", fg: "#15803d" },
  partially_paid: { bg: "#ffedd5", fg: "#c2410c" },
  written_off: { bg: "#f3f4f6", fg: "#4b5563" },
};

const DEFAULT_STATUS: StatusStyle = { bg: "#f3f4f6", fg: "#4b5563" };

export function statusStyle(status: string): StatusStyle {
  return PALETTE[status] ?? DEFAULT_STATUS;
}

const PRIORITY_PALETTE: Record<string, StatusStyle> = {
  routine: { bg: "#f3f4f6", fg: "#4b5563" },
  urgent: { bg: "#ffedd5", fg: "#c2410c" },
  stat: { bg: "#fee2e2", fg: "#b91c1c" },
};

export function priorityStyle(priority: string): StatusStyle {
  return PRIORITY_PALETTE[priority] ?? DEFAULT_STATUS;
}

export function formatLabel(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
