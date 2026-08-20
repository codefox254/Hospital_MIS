import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  Consultation,
  ConsultationAddendum,
  Diagnosis,
  DiagnosisType,
  StartVisitInput,
  Vitals,
  Visit,
} from "../../types/opd";
import type { PaginatedResponse } from "../../types/patient";

export function useVisits(status?: string) {
  return useQuery({
    queryKey: ["opd", "visits", status],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Visit>>("/opd/visits/", {
        params: status ? { status } : undefined,
      });
      return data;
    },
  });
}

export function useVisit(id: string | undefined) {
  return useQuery({
    queryKey: ["opd", "visits", "detail", id],
    enabled: !!id,
    queryFn: async () => {
      const { data } = await api.get<Visit>(`/opd/visits/${id}/`);
      return data;
    },
  });
}

export function useStartVisit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: StartVisitInput) => {
      const { data } = await api.post<Visit>("/opd/visits/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opd", "visits"] });
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
  });
}

export function useConsultationForVisit(visitId: string | undefined) {
  return useQuery({
    queryKey: ["opd", "consultation", "for-visit", visitId],
    enabled: !!visitId,
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Consultation>>("/opd/consultations/", {
        params: { visit: visitId },
      });
      return data.results[0] ?? null;
    },
  });
}

export function useVitalsForVisit(visitId: string | undefined) {
  return useQuery({
    queryKey: ["opd", "vitals", visitId],
    enabled: !!visitId,
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Vitals>>("/opd/vitals/", {
        params: { visit: visitId },
      });
      return data.results;
    },
  });
}

export function useRecordVitals(visitId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Omit<Partial<Vitals>, "id" | "visit" | "recorded_by" | "recorded_at">) => {
      const { data } = await api.post<Vitals>("/opd/vitals/", { visit: visitId, ...input });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opd", "vitals", visitId] });
    },
  });
}

export function useUpdateConsultationDraft(consultationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (fields: Partial<Pick<Consultation, "chief_complaint" | "history_of_present_illness" | "examination_notes">>) => {
      const { data } = await api.patch<Consultation>(`/opd/consultations/${consultationId}/`, fields);
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["opd", "consultation", "for-visit", data.visit], data);
    },
  });
}

export function useCompleteConsultation(visitId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (consultationId: string) => {
      const { data } = await api.post<Consultation>(`/opd/consultations/${consultationId}/complete/`);
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["opd", "consultation", "for-visit", visitId], data);
      queryClient.invalidateQueries({ queryKey: ["opd", "visits"] });
    },
  });
}

export function useDiagnoses(consultationId: string | undefined) {
  return useQuery({
    queryKey: ["opd", "diagnoses", consultationId],
    enabled: !!consultationId,
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Diagnosis>>("/opd/diagnoses/", {
        params: { consultation: consultationId },
      });
      return data.results;
    },
  });
}

export function useAddDiagnosis(consultationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { description: string; type: DiagnosisType; icd_code?: string }) => {
      const { data } = await api.post<Diagnosis>("/opd/diagnoses/", {
        consultation: consultationId,
        ...input,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opd", "diagnoses", consultationId] });
    },
  });
}

export function useAddenda(consultationId: string | undefined) {
  return useQuery({
    queryKey: ["opd", "addenda", consultationId],
    enabled: !!consultationId,
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<ConsultationAddendum>>("/opd/addenda/", {
        params: { consultation: consultationId },
      });
      return data.results;
    },
  });
}

export function useAddAddendum(consultationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (text: string) => {
      const { data } = await api.post<ConsultationAddendum>("/opd/addenda/", {
        consultation: consultationId,
        text,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["opd", "addenda", consultationId] });
    },
  });
}
