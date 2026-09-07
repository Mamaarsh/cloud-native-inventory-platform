import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adjustInventory,
  createInventory,
  deleteInventory,
  listInventoryMovements,
  listInventory,
  updateInventory,
} from "@/api/inventory-api";
import type {
  InventoryAdjustmentRequest,
  InventoryQueryParams,
  InventoryRequest,
} from "@/types";

export const inventoryKeys = {
  all: ["inventory"] as const,
  lists: () => [...inventoryKeys.all, "list"] as const,
  list: (params: InventoryQueryParams) => [...inventoryKeys.lists(), params] as const,
  movements: () => [...inventoryKeys.all, "movements"] as const,
  movementLists: (id: number) => [...inventoryKeys.movements(), id] as const,
  movementList: (id: number, page: number) => [
    ...inventoryKeys.movementLists(id),
    page,
  ] as const,
};

export function useInventory(
  params: InventoryQueryParams = {},
  enabled = true,
) {
  return useQuery({
    queryKey: inventoryKeys.list(params),
    queryFn: () => listInventory(params),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useInventoryMovements(
  id: number,
  page: number,
  enabled = true,
) {
  return useQuery({
    queryKey: inventoryKeys.movementList(id, page),
    queryFn: () => listInventoryMovements(id, page),
    placeholderData: keepPreviousData,
    enabled: enabled && Number.isInteger(id) && id > 0,
  });
}

export function useAdjustInventory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: InventoryAdjustmentRequest;
    }) => adjustInventory(id, payload),
    onSuccess: async (movement) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: inventoryKeys.lists() }),
        queryClient.invalidateQueries({
          queryKey: inventoryKeys.movementLists(movement.inventory),
        }),
      ]);
    },
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
