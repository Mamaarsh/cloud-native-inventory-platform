import { apiClient } from "@/api/client";
import type {
  Order,
  OrderCreateRequest,
  OrderDetail,
  OrderQueryParams,
  OrderStatusHistoryEntry,
  OrderStatusRequest,
  PaginatedResponse,
  Payment,
} from "@/types";

const path = "/v1/orders/";

export async function listOrders(params: OrderQueryParams = {}): Promise<PaginatedResponse<Order>> {
  const { data } = await apiClient.get<PaginatedResponse<Order>>(path, { params });
  return data;
}

export async function getOrder(id: number): Promise<OrderDetail> {
  const { data } = await apiClient.get<OrderDetail>(`${path}${id}/`);
  return data;
}

export async function getOrderHistory(
  id: number,
): Promise<OrderStatusHistoryEntry[]> {
  const { data } = await apiClient.get<OrderStatusHistoryEntry[]>(
    `${path}${id}/history/`,
  );
  return data;
}

export async function createOrder(payload: OrderCreateRequest): Promise<Order> {
  const { data } = await apiClient.post<Order>(path, payload);
  return data;
}

export async function changeOrderStatus(id: number, payload: OrderStatusRequest): Promise<Order> {
  const { data } = await apiClient.post<Order>(`${path}${id}/change-status/`, payload);
  return data;
}

export async function payOrder(id: number): Promise<Payment> {
  const { data } = await apiClient.post<Payment>(`${path}${id}/pay/`, {});
  return data;
}
