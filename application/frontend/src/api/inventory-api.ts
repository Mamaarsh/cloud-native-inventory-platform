import { apiClient } from "@/api/client";
import type {
  Inventory,
  InventoryAdjustmentRequest,
  InventoryMovement,
  InventoryQueryParams,
  InventoryRequest,
  PaginatedResponse,
} from "@/types";

const path = "/v1/inventory/";

export async function listInventory(params: InventoryQueryParams = {}): Promise<PaginatedResponse<Inventory>> {
  const { data } = await apiClient.get<PaginatedResponse<Inventory>>(path, { params });
  return data;
}

export async function createInventory(payload: InventoryRequest): Promise<Inventory> {
  const { data } = await apiClient.post<Inventory>(path, payload);
  return data;
}

export async function updateInventory(
  id: number,
  payload: Partial<InventoryRequest>,
): Promise<Inventory> {
  const { data } = await apiClient.patch<Inventory>(`${path}${id}/`, payload);
  return data;
}

export async function deleteInventory(id: number): Promise<void> {
  await apiClient.delete(`${path}${id}/`);
}

export async function adjustInventory(
  id: number,
  payload: InventoryAdjustmentRequest,
): Promise<InventoryMovement> {
  const { data } = await apiClient.post<InventoryMovement>(
    `${path}${id}/adjust/`,
    payload,
  );
  return data;
}

export async function listInventoryMovements(
  id: number,
  page: number,
): Promise<PaginatedResponse<InventoryMovement>> {
  const { data } = await apiClient.get<PaginatedResponse<InventoryMovement>>(
    `${path}${id}/movements/`,
    { params: { page } },
  );
  return data;
}
