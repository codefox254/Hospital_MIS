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
