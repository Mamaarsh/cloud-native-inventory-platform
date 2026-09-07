import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  changeOrderStatus,
  createOrder,
  getOrder,
  listOrders,
  payOrder,
} from "@/api/orders-api";
import type {
  OrderCreateRequest,
  OrderDetail,
  OrderQueryParams,
  OrderStatus,
} from "@/types";

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
    placeholderData: keepPreviousData,
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
      queryClient.setQueryData<OrderDetail>(orderKeys.detail(order.id), {
        ...order,
        payment: null,
      });
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
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: orderKeys.detail(order.id) }),
        queryClient.invalidateQueries({ queryKey: orderKeys.lists() }),
      ]);
    },
  });
}

export function usePayOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: payOrder,
    onSuccess: async (payment) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: orderKeys.detail(payment.order) }),
        queryClient.invalidateQueries({ queryKey: orderKeys.lists() }),
      ]);
    },
  });
}
