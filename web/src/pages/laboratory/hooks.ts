import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api";
import type {
  CreateLabOrderInput,
  LabOrder,
  LabResult,
  LabSample,
  ResultFlag,
} from "../../types/laboratory";
import type { PaginatedResponse } from "../../types/patient";

export function useLabOrders(status?: string) {
  return useQuery({
    queryKey: ["lab", "orders", status],
    queryFn: async () => {
      const { data } = await api.get<PaginatedResponse<LabOrder>>("/laboratory/lab-orders/", {
        params: status ? { status } : undefined,
      });
      return data;
    },
  });
}

export function useLabOrder(id: string | undefined) {
  return useQuery({
    queryKey: ["lab", "orders", "detail", id],
    enabled: !!id,
    queryFn: async () => {
      const { data } = await api.get<LabOrder>(`/laboratory/lab-orders/${id}/`);
      return data;
    },
  });
}

export function useCreateLabOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateLabOrderInput) => {
      const { data } = await api.post<LabOrder>("/laboratory/lab-orders/", input);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab", "orders"] });
    },
  });
}

export function useSamplesForOrder(orderId: string) {
  return useQuery({
    queryKey: ["lab", "samples", orderId],
    queryFn: async () => {
      const items = (
        await api.get<PaginatedResponse<{ id: string }>>("/laboratory/lab-order-items/", {
          params: { lab_order: orderId },
        })
      ).data.results;
      const samples = await Promise.all(
        items.map((item) =>
          api
            .get<PaginatedResponse<LabSample>>("/laboratory/samples/", {
              params: { lab_order_item: item.id },
            })
            .then((r) => r.data.results[0] ?? null),
        ),
      );
      return Object.fromEntries(items.map((item, i) => [item.id, samples[i]]));
    },
  });
}

export function useCollectSample(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ itemId, barcode }: { itemId: string; barcode: string }) => {
      const { data } = await api.post<LabSample>("/laboratory/samples/", {
        lab_order_item: itemId,
        barcode,
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab", "samples", orderId] });
      queryClient.invalidateQueries({ queryKey: ["lab", "orders", "detail", orderId] });
    },
  });
}

export function useResultsForOrder(orderId: string) {
  return useQuery({
    queryKey: ["lab", "results", orderId],
    queryFn: async () => {
      const items = (
        await api.get<PaginatedResponse<{ id: string }>>("/laboratory/lab-order-items/", {
          params: { lab_order: orderId },
        })
      ).data.results;
      const results = await Promise.all(
        items.map((item) =>
          api
            .get<PaginatedResponse<LabResult>>("/laboratory/results/", {
              params: { lab_order_item: item.id },
            })
            .then((r) => r.data.results[0] ?? null),
        ),
      );
      return Object.fromEntries(items.map((item, i) => [item.id, results[i]]));
    },
  });
}

export function useEnterResult(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      parameter,
      value,
      unit,
      flag,
    }: {
      itemId: string;
      parameter: string;
      value: string;
      unit: string;
      flag: ResultFlag;
    }) => {
      const { data } = await api.post<LabResult>("/laboratory/results/", {
        lab_order_item: itemId,
        values: [{ parameter, value, unit, flag }],
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab", "results", orderId] });
      queryClient.invalidateQueries({ queryKey: ["lab", "orders", "detail", orderId] });
    },
  });
}

export function useVerifyResult(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (resultId: string) => {
      const { data } = await api.post<LabResult>(`/laboratory/results/${resultId}/verify/`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lab", "results", orderId] });
      queryClient.invalidateQueries({ queryKey: ["lab", "orders", "detail", orderId] });
    },
  });
}
