import { useQuery } from "@tanstack/react-query";

import { api } from "./api";
import type { Department, StaffUser } from "../types/lookup";
import type { PaginatedResponse } from "../types/patient";

export function useDepartments() {
  return useQuery({
    queryKey: ["lookups", "departments"],
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Department>>("/core/departments/");
      return data.results;
    },
  });
}

export function useStaffUsers() {
  return useQuery({
    queryKey: ["lookups", "users"],
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<StaffUser>>("/auth/users/");
      return data.results;
    },
  });
}

export function staffName(user: StaffUser): string {
  return `${user.first_name} ${user.last_name}`.trim() || user.email;
}

interface PatientLite {
  id: string;
  mrn: string;
  first_name: string;
  last_name: string;
}

/** One GET per patient id, cached by react-query — cards across
 * Appointments/Lab/Billing all reference a patient by id only (the
 * serializers return raw FKs, not nested names), so this is the shared
 * per-row resolver rather than each page re-implementing its own fetch. */
export function usePatientName(id: string | undefined) {
  return useQuery({
    queryKey: ["lookups", "patient", id],
    enabled: !!id,
    staleTime: 5 * 60_000,
    queryFn: async () => {
      const { data } = await api.get<PatientLite>(`/patients/patients/${id}/`);
      return `${data.first_name} ${data.last_name}`.trim() || data.mrn;
    },
  });
}
