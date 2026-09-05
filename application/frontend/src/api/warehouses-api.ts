import { apiClient } from "@/api/client";
import type { PaginatedResponse, Warehouse, WarehouseQueryParams, WarehouseRequest } from "@/types";

const path = "/v1/warehouses/";

export async function listWarehouses(params: WarehouseQueryParams = {}): Promise<PaginatedResponse<Warehouse>> {
  const { data } = await apiClient.get<PaginatedResponse<Warehouse>>(path, { params });
  return data;
}

export async function listAllWarehouses(): Promise<Warehouse[]> {
  const warehouses: Warehouse[] = [];
  let page = 1;
  let response = await listWarehouses({ page, ordering: "name" });
  warehouses.push(...response.results);
  while (response.next) {
    page += 1;
    response = await listWarehouses({ page, ordering: "name" });
    warehouses.push(...response.results);
  }
  return warehouses;
}

export async function getWarehouse(id: number): Promise<Warehouse> {
  const { data } = await apiClient.get<Warehouse>(`${path}${id}/`);
  return data;
}

export async function createWarehouse(payload: WarehouseRequest): Promise<Warehouse> {
  const { data } = await apiClient.post<Warehouse>(path, payload);
  return data;
}

export async function updateWarehouse(id: number, payload: Partial<WarehouseRequest>): Promise<Warehouse> {
  const { data } = await apiClient.patch<Warehouse>(`${path}${id}/`, payload);
  return data;
}

export async function deleteWarehouse(id: number): Promise<void> {
  await apiClient.delete(`${path}${id}/`);
}
