import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { listAuditLogs } from "@/api/audit-logs-api";
import type { AuditLogQueryParams } from "@/types";

export const auditLogKeys = {
  all: ["audit-logs"] as const,
  lists: () => [...auditLogKeys.all, "list"] as const,
  list: (params: AuditLogQueryParams) => [...auditLogKeys.lists(), params] as const,
};

export function useAuditLogs(params: AuditLogQueryParams = {}) {
  return useQuery({
    queryKey: auditLogKeys.list(params),
    queryFn: () => listAuditLogs(params),
    placeholderData: keepPreviousData,
  });
}
