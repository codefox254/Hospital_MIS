import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  Appointment,
  BookAppointmentInput,
  QueueEntry,
} from "../../types/appointment";
import type { PaginatedResponse } from "../../types/patient";

export function useAppointments(filters: { status?: string; date?: string }) {
  return useQuery({
    queryKey: ["appointments", filters],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Appointment>>(
        "/appointments/appointments/",
        { params: filters },
      );
      return data;
    },
  });
}

export function useAvailability(doctor: string, department: string, date: string) {
  return useQuery({
    queryKey: ["appointments", "availability", doctor, department, date],
    enabled: !!doctor && !!department && !!date,
    queryFn: async () => {
      const { data } = await api.get<{ slots: string[] }>("/appointments/availability/", {
        params: { doctor, department, date },
      });
      return data.slots;
    },
  });
}

export function useBookAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: BookAppointmentInput) => {
      const { data } = await api.post<Appointment>("/appointments/appointments/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
  });
}

export function useCheckIn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (appointmentId: string) => {
      const { data } = await api.post<QueueEntry>(
        `/appointments/appointments/${appointmentId}/check_in/`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      queryClient.invalidateQueries({ queryKey: ["queue"] });
    },
  });
}

export function useCancelAppointment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (appointmentId: string) => {
      const { data } = await api.post<Appointment>(
        `/appointments/appointments/${appointmentId}/cancel/`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
    },
  });
}

export function useQueueEntries(department: string | undefined) {
  return useQuery({
    queryKey: ["queue", department],
    enabled: !!department,
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<QueueEntry>>(
        "/appointments/queue-entries/",
        { params: { "appointment__department": department } },
      );
      return data.results;
    },
  });
}

export function useCallNext() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (queueEntryId: string) => {
      const { data } = await api.post<QueueEntry>(
        `/appointments/queue-entries/${queueEntryId}/call/`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queue"] });
    },
  });
}
