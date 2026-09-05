import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  changeOrderStatus,
  createOrder,
  getOrder,
  listOrders,
  payOrder,
} from "@/api/orders-api";
import type { OrderCreateRequest, OrderQueryParams, OrderStatus } from "@/types";

export const orderKeys = {
  all: ["orders"] as const,
  lists: () => [...orderKeys.all, "list"] as const,
  list: (params: OrderQueryParams) => [...orderKeys.lists(), params] as const,
  detail: (id: number) => [...orderKeys.all, "detail", id] as const,
};

export function useOrders(params: OrderQueryParams = {}) {
  return useQuery({
    queryKey: orderKeys.list(params),
    queryFn: () => listOrders(params),
  });
}

export function useOrder(id: number) {
  return useQuery({
    queryKey: orderKeys.detail(id),
    queryFn: () => getOrder(id),
    enabled: Number.isInteger(id) && id > 0,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OrderCreateRequest) => createOrder(payload),
    onSuccess: async (order) => {
      queryClient.setQueryData(orderKeys.detail(order.id), order);
      await queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });
}

export function useChangeOrderStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: OrderStatus }) =>
      changeOrderStatus(id, { status }),
    onSuccess: async (order) => {
      queryClient.setQueryData(orderKeys.detail(order.id), order);
      await queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });
}

export function usePayOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: payOrder,
    onSuccess: async (payment) => {
      queryClient.setQueryData(["payments", payment.order], payment);
      await queryClient.invalidateQueries({ queryKey: orderKeys.detail(payment.order) });
      await queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });
}
