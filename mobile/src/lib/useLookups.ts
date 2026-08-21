import { useEffect, useState } from "react";

import { api } from "./api";
import type { Department, PatientLite, StaffUser } from "../types/lookup";
import type { PaginatedResponse } from "../types/appointment";

const departmentCache = new Map<string, Department>();
const staffCache = new Map<string, StaffUser>();
const patientCache = new Map<string, PatientLite>();

let departmentsLoaded = false;
let staffLoaded = false;

async function ensureDepartments() {
  if (departmentsLoaded) return;
  departmentsLoaded = true;
  const { data } = await api.get<PaginatedResponse<Department>>("/core/departments/");
  data.results.forEach((d) => departmentCache.set(d.id, d));
}

async function ensureStaff() {
  if (staffLoaded) return;
  staffLoaded = true;
  const { data } = await api.get<PaginatedResponse<StaffUser>>("/auth/users/");
  data.results.forEach((u) => staffCache.set(u.id, u));
}

async function ensurePatient(id: string) {
  if (patientCache.has(id)) return;
  const { data } = await api.get<PatientLite>(`/patients/patients/${id}/`);
  patientCache.set(id, data);
}

export function staffName(id: string): string {
  const u = staffCache.get(id);
  if (!u) return "";
  return `${u.first_name} ${u.last_name}`.trim() || u.email;
}

export function departmentName(id: string): string {
  return departmentCache.get(id)?.name ?? "";
}

export function patientName(id: string): string {
  const p = patientCache.get(id);
  if (!p) return "";
  return `${p.first_name} ${p.last_name}`.trim() || p.mrn;
}

/** Warms the department/staff/patient lookup caches so name helpers above
 * resolve on first render of a detail screen — these lists are small and
 * shared across every detail screen, so a stand-in module cache beats
 * refetching (or a full lookups context) for this app's size. */
export function useLookups(patientId?: string) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    // Reset on every patientId change (including undefined -> real id, once
    // the owning screen's own fetch resolves) — otherwise a stale `true`
    // from an earlier run with no patientId lets the screen render before
    // this run's ensurePatient() call has actually populated the cache.
    setReady(false);
    Promise.all([ensureDepartments(), ensureStaff(), patientId ? ensurePatient(patientId) : null])
      .then(() => {
        if (!cancelled) setReady(true);
      })
      .catch(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  return ready;
}
