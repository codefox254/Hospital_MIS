export type LabOrderStatus = "pending" | "collected" | "processing" | "completed";
export type LabPriority = "routine" | "stat";
export type LabSampleStatus = "collected" | "rejected" | "received";
export type LabResultStatus = "entered" | "verified" | "amended";
export type ResultFlag = "normal" | "low" | "high" | "critical";

export interface LabOrderItem {
  id: string;
  lab_order: string;
  test_code: string;
  test_name: string;
}

export interface LabOrder {
  id: string;
  facility: string;
  visit: string;
  ordered_by: string;
  priority: LabPriority;
  status: LabOrderStatus;
  ordered_at: string;
  items: LabOrderItem[];
}

export interface CreateLabOrderInput {
  visit: string;
  priority?: LabPriority;
  items: { test_code: string; test_name: string }[];
}

export interface LabSample {
  id: string;
  lab_order_item: string;
  barcode: string;
  collected_by: string;
  collected_at: string;
  status: LabSampleStatus;
  rejection_reason: string;
}

export interface LabResultValue {
  id: string;
  lab_result: string;
  parameter: string;
  value: string;
  unit: string;
  reference_range: string;
  flag: ResultFlag;
}

export interface LabResult {
  id: string;
  lab_order_item: string;
  entered_by: string;
  entered_at: string | null;
  verified_by: string | null;
  verified_at: string | null;
  status: LabResultStatus;
  is_critical: boolean;
  released_to_portal_at: string | null;
  values: LabResultValue[];
}
