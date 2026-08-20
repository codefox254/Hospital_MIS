import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  AllergyConflict,
  CreatePrescriptionInput,
  DispenseRecord,
  Drug,
  Prescription,
  StockBatch,
} from "../../types/pharmacy";
import type { PaginatedResponse } from "../../types/patient";

export function useDrugs() {
  return useQuery({
    queryKey: ["pharmacy", "drugs"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Drug>>("/pharmacy/drugs/");
      return data.results;
    },
  });
}

export function useCreateDrug() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Omit<Drug, "id">) => {
      const { data } = await api.post<Drug>("/pharmacy/drugs/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pharmacy", "drugs"] });
    },
  });
}

export function useStockBatches() {
  return useQuery({
    queryKey: ["pharmacy", "stock-batches"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<StockBatch>>("/pharmacy/stock-batches/");
      return data.results;
    },
  });
}

export function useCreateStockBatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Omit<StockBatch, "id" | "facility">) => {
      const { data } = await api.post<StockBatch>("/pharmacy/stock-batches/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pharmacy", "stock-batches"] });
    },
  });
}

export function usePrescriptions() {
  return useQuery({
    queryKey: ["pharmacy", "prescriptions"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Prescription>>("/pharmacy/prescriptions/");
      return data;
    },
  });
}

export function usePrescription(id: string | undefined) {
  return useQuery({
    queryKey: ["pharmacy", "prescriptions", "detail", id],
    enabled: !!id,
    queryFn: async () => {
      const { data } = await api.get<Prescription>(`/pharmacy/prescriptions/${id}/`);
      return data;
    },
  });
}

export function useCreatePrescription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreatePrescriptionInput) => {
      const { data } = await api.post<Prescription>("/pharmacy/prescriptions/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pharmacy", "prescriptions"] });
    },
  });
}

export function useAllergyCheck(patientId: string, drugId: string) {
  return useQuery({
    queryKey: ["pharmacy", "allergy-check", patientId, drugId],
    enabled: !!patientId && !!drugId,
    queryFn: async () => {
      const { data } = await api.get<{ conflicts: AllergyConflict[] }>(
        "/pharmacy/stock-batches/allergy_check/",
        { params: { patient: patientId, drug: drugId } },
      );
      return data.conflicts;
    },
  });
}

export function useDispense(prescriptionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { prescription_item: string; batch: string; qty_dispensed: number }) => {
      const { data } = await api.post<DispenseRecord>("/pharmacy/dispense-records/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pharmacy", "prescriptions", "detail", prescriptionId] });
      queryClient.invalidateQueries({ queryKey: ["pharmacy", "stock-batches"] });
    },
  });
}
