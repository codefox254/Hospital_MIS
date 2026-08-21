import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { CreateUserInput, Facility, FacilityStats } from "../../types/admin";
import type { PaginatedResponse } from "../../types/patient";

export function usePlatformStats() {
  return useQuery({
    queryKey: ["admin", "platform-stats"],
    queryFn: async () => {
      const { data } = await api.get<FacilityStats[]>("/core/platform-stats/");
      return data;
    },
  });
}

export function useFacilities() {
  return useQuery({
    queryKey: ["admin", "facilities"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Facility>>("/core/facilities/");
      return data.results;
    },
  });
}

export function useCreateFacility() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      name: string;
      code: string;
      type: string;
      address?: string;
      phone?: string;
    }) => {
      const { data } = await api.post<Facility>("/core/facilities/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });
}

export function useDeactivateFacility() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<Facility>(`/core/facilities/${id}/deactivate/`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateUserInput) => {
      const { data } = await api.post("/auth/users/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      queryClient.invalidateQueries({ queryKey: ["lookups", "users"] });
    },
  });
}
