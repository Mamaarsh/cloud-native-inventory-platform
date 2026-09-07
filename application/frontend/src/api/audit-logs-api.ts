import { apiClient } from "@/api/client";
import type { AuditLogEntry, AuditLogQueryParams, PaginatedResponse } from "@/types";

const path = "/v1/audit-logs/";

export async function listAuditLogs(
  params: AuditLogQueryParams = {},
): Promise<PaginatedResponse<AuditLogEntry>> {
  const { data } = await apiClient.get<PaginatedResponse<AuditLogEntry>>(path, {
    params,
  });
  return data;
}
