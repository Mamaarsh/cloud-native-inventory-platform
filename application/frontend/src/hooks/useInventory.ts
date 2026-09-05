import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createInventory,
  deleteInventory,
  listInventory,
  updateInventory,
} from "@/api/inventory-api";
import type { InventoryQueryParams, InventoryRequest } from "@/types";

export const inventoryKeys = {
  all: ["inventory"] as const,
  lists: () => [...inventoryKeys.all, "list"] as const,
  list: (params: InventoryQueryParams) => [...inventoryKeys.lists(), params] as const,
};

export function useInventory(params: InventoryQueryParams = {}) {
  return useQuery({
    queryKey: inventoryKeys.list(params),
    queryFn: () => listInventory(params),
    placeholderData: keepPreviousData,
  });
}

export function useCreateInventory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createInventory,
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: inventoryKeys.all }),
  });
}

export function useUpdateInventory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<InventoryRequest> }) =>
      updateInventory(id, payload),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: inventoryKeys.all }),
  });
}

export function useDeleteInventory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteInventory,
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: inventoryKeys.all }),
  });
}
