import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type { Invoice, MpesaTransaction, Payment, PaymentMethod, Refund } from "../../types/billing";
import type { PaginatedResponse } from "../../types/patient";

export function useInvoices() {
  return useQuery({
    queryKey: ["billing", "invoices"],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Invoice>>("/billing/invoices/");
      return data;
    },
  });
}

export function useInvoice(id: string | undefined) {
  return useQuery({
    queryKey: ["billing", "invoices", "detail", id],
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data?.status === "pending_confirmation" ? 3000 : false,
    queryFn: async () => {
      const { data } = await api.get<Invoice>(`/billing/invoices/${id}/`);
      return data;
    },
  });
}

export function useStartInvoice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { patient: string; visit?: string }) => {
      const { data } = await api.post<Invoice>("/billing/invoices/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing", "invoices"] });
    },
  });
}

export function usePayments(invoiceId: string | undefined) {
  return useQuery({
    queryKey: ["billing", "payments", invoiceId],
    enabled: !!invoiceId,
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Payment>>("/billing/payments/", {
        params: { invoice: invoiceId },
      });
      return data.results;
    },
  });
}

export function useRecordPayment(invoiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { method: PaymentMethod; amount: string; reference?: string }) => {
      const { data } = await api.post<Payment>("/billing/payments/", { invoice: invoiceId, ...input });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing", "invoices", "detail", invoiceId] });
      queryClient.invalidateQueries({ queryKey: ["billing", "payments", invoiceId] });
    },
  });
}

export function useMpesaStkPush(invoiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { phone_number: string; amount: string }) => {
      const { data } = await api.post<MpesaTransaction>("/billing/payments/mpesa_stk_push/", {
        invoice: invoiceId,
        ...input,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing", "invoices", "detail", invoiceId] });
    },
  });
}

export function useRefunds(invoiceId: string | undefined) {
  return useQuery({
    queryKey: ["billing", "refunds", invoiceId],
    enabled: !!invoiceId,
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<Refund>>("/billing/refunds/", {
        params: { invoice: invoiceId },
      });
      return data.results;
    },
  });
}

export function useApproveRefund(invoiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { payment: string; amount: string; reason: string }) => {
      const { data } = await api.post<Refund>("/billing/refunds/", { invoice: invoiceId, ...input });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing", "invoices", "detail", invoiceId] });
      queryClient.invalidateQueries({ queryKey: ["billing", "refunds", invoiceId] });
    },
  });
}
