import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { NewPatientInput, PaginatedResponse, Patient } from "../../types/patient";

export function usePatients(search: string) {
  return useQuery({
    queryKey: ["patients", search],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Patient>>("/patients/patients/", {
        params: search ? { search } : undefined,
      });
      return data;
    },
  });
}

export function usePatient(id: string | undefined) {
  return useQuery({
    queryKey: ["patients", "detail", id],
    enabled: !!id,
    queryFn: async () => {
      const { data } = await api.get<Patient>(`/patients/patients/${id}/`);
      return data;
    },
  });
}

export function useRegisterPatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: NewPatientInput) => {
      const { data } = await api.post<Patient>("/patients/patients/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients"] });
    },
  });
}
