import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAdminUser,
  listAdminUsers,
  updateAdminUser,
} from "@/api/admin-users-api";
import type { AdminUserQueryParams, AdminUserUpdateRequest } from "@/types";

export const adminUserKeys = {
  all: ["admin-users"] as const,
  lists: () => [...adminUserKeys.all, "list"] as const,
  list: (params: AdminUserQueryParams) => [...adminUserKeys.lists(), params] as const,
  details: () => [...adminUserKeys.all, "detail"] as const,
  detail: (id: number) => [...adminUserKeys.details(), id] as const,
};

export function useAdminUsers(params: AdminUserQueryParams = {}) {
  return useQuery({
    queryKey: adminUserKeys.list(params),
    queryFn: () => listAdminUsers(params),
    placeholderData: keepPreviousData,
  });
}

export function useAdminUser(id: number) {
  return useQuery({
    queryKey: adminUserKeys.detail(id),
    queryFn: () => getAdminUser(id),
    enabled: Number.isInteger(id) && id > 0,
  });
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: AdminUserUpdateRequest;
    }) => updateAdminUser(id, payload),
    onSuccess: async (user) => {
      queryClient.setQueryData(adminUserKeys.detail(user.id), user);
      await queryClient.invalidateQueries({ queryKey: adminUserKeys.lists() });
    },
  });
}
