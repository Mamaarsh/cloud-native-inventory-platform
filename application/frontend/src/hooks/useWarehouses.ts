import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createWarehouse,
  deleteWarehouse,
  getWarehouse,
  listAllWarehouses,
  listWarehouses,
  updateWarehouse,
} from "@/api/warehouses-api";
import type { WarehouseQueryParams, WarehouseRequest } from "@/types";

export const warehouseKeys = {
  all: ["warehouses"] as const,
  lists: () => [...warehouseKeys.all, "list"] as const,
  list: (params: WarehouseQueryParams) => [...warehouseKeys.lists(), params] as const,
  detail: (id: number) => [...warehouseKeys.all, "detail", id] as const,
};

export function useWarehouses(params: WarehouseQueryParams = {}) {
  return useQuery({
    queryKey: warehouseKeys.list(params),
    queryFn: () => listWarehouses(params),
    placeholderData: keepPreviousData,
  });
}

export function useWarehouse(id: number) {
  return useQuery({
    queryKey: warehouseKeys.detail(id),
    queryFn: () => getWarehouse(id),
    enabled: Number.isInteger(id) && id > 0,
  });
}

export function useAllWarehouses() {
  return useQuery({
    queryKey: [...warehouseKeys.all, "all-options"],
    queryFn: listAllWarehouses,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateWarehouse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createWarehouse,
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: warehouseKeys.all }),
  });
}

export function useUpdateWarehouse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<WarehouseRequest> }) =>
      updateWarehouse(id, payload),
    onSuccess: async (warehouse) => {
      queryClient.setQueryData(warehouseKeys.detail(warehouse.id), warehouse);
      await queryClient.invalidateQueries({ queryKey: warehouseKeys.lists() });
    },
  });
}

export function useDeleteWarehouse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteWarehouse,
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: warehouseKeys.all }),
  });
}
