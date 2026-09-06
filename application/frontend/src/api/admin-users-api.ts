import { apiClient } from "@/api/client";
import type {
  AdminUser,
  AdminUserQueryParams,
  AdminUserUpdateRequest,
  PaginatedResponse,
} from "@/types";

const path = "/auth/admin/users/";

export async function listAdminUsers(
  params: AdminUserQueryParams = {},
): Promise<PaginatedResponse<AdminUser>> {
  const { data } = await apiClient.get<PaginatedResponse<AdminUser>>(path, {
    params,
  });
  return data;
}

export async function getAdminUser(id: number): Promise<AdminUser> {
  const { data } = await apiClient.get<AdminUser>(`${path}${id}/`);
  return data;
}

export async function updateAdminUser(
  id: number,
  payload: AdminUserUpdateRequest,
): Promise<AdminUser> {
  const { data } = await apiClient.patch<AdminUser>(`${path}${id}/`, payload);
  return data;
}
