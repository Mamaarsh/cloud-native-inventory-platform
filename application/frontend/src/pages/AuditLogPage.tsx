import { useState } from "react";
import { ClipboardClock, Search, ShieldCheck } from "lucide-react";
import { BackgroundFetchIndicator } from "@/components/ui/BackgroundFetchIndicator";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { useAuditLogs } from "@/hooks/useAuditLogs";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { formatCurrency, formatDate, titleCase } from "@/lib/format";
import type { AuditLogEntry, AuditTargetType } from "@/types";

const actionLabels: Record<string, string> = {
  "user.created": "Created user",
  "user.registered": "Registered account",
  "user.activated": "Activated user",
  "user.deactivated": "Deactivated user",
  "user.role_changed": "Changed user role",
  "user.password_changed": "Changed password",
  "product.created": "Created product",
  "product.updated": "Updated product",
  "product.activated": "Activated product",
  "product.deactivated": "Deactivated product",
  "product.deleted": "Deleted product",
  "warehouse.created": "Created warehouse",
  "warehouse.updated": "Updated warehouse",
  "warehouse.deleted": "Deleted warehouse",
  "inventory.created": "Created inventory record",
  "inventory.adjusted": "Adjusted inventory",
  "inventory.deleted": "Deleted inventory record",
  "order.created": "Created order",
  "order.status_changed": "Changed order status",
  "payment.succeeded": "Payment succeeded",
};

const actionOptions = Object.entries(actionLabels);
const targetTypes: AuditTargetType[] = [
  "user",
  "product",
  "warehouse",
  "inventory",
  "order",
  "payment",
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "None";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string" || typeof value === "number") return String(value);
  return "Recorded";
}

function auditDetails(entry: AuditLogEntry): string[] {
  const metadata = entry.metadata;
  if (entry.action === "user.role_changed") {
    return [`${displayValue(metadata.old_role)} → ${displayValue(metadata.new_role)}`];
  }
  if (entry.action === "inventory.adjusted" && metadata.movement_id) {
    return [`Movement #${displayValue(metadata.movement_id)}`];
  }
  if (entry.action === "order.status_changed" && metadata.status_history_id) {
    return [`Status history #${displayValue(metadata.status_history_id)}`];
  }
  if (entry.action === "order.created" && metadata.item_count !== undefined) {
    return [`${displayValue(metadata.item_count)} order item(s)`];
  }
  if (entry.action === "payment.succeeded") {
    const details = [];
    if (metadata.payment_id) details.push(`Payment #${displayValue(metadata.payment_id)}`);
    if (metadata.provider) details.push(`Provider: ${displayValue(metadata.provider)}`);
    if (typeof metadata.amount === "string" || typeof metadata.amount === "number") {
      details.push(formatCurrency(metadata.amount));
    }
    return details;
  }

  const details: string[] = [];
  if (isRecord(metadata.changes)) {
    for (const [field, values] of Object.entries(metadata.changes)) {
      if (!isRecord(values)) continue;
      details.push(
        `${titleCase(field)}: ${displayValue(values.before)} → ${displayValue(values.after)}`,
      );
    }
  }
  if (metadata.image_changed === true) details.push("Product image changed");
  return details;
}

export function AuditLogPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [targetType, setTargetType] = useState<AuditTargetType | "">("");
  const [action, setAction] = useState("");
  const debouncedSearch = useDebouncedValue(search);
  const auditLogs = useAuditLogs({
    page,
    search: debouncedSearch || undefined,
    target_type: targetType || undefined,
    action: action || undefined,
  });
  const hasFilters = Boolean(debouncedSearch || targetType || action);

  function clearFilters(): void {
    setSearch("");
    setTargetType("");
    setAction("");
    setPage(1);
  }

  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Audit log"
        description="Review immutable security and operational activity across the workspace."
      />
      <Card className="overflow-hidden" aria-busy={auditLogs.isPending}>
        <div className="grid gap-4 border-b border-slate-200 bg-slate-50/70 px-6 py-5 lg:grid-cols-[1fr_220px_240px]">
          <div className="relative self-end">
            <Search className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              dir="auto"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Search actor or target"
              aria-label="Search audit log"
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white pl-10 pr-4 text-sm shadow-sm transition-colors hover:border-slate-400 focus:border-brand-600 motion-reduce:transition-none"
            />
          </div>
          <Select
            label="Resource type"
            value={targetType}
            onChange={(event) => {
              setTargetType(event.target.value as AuditTargetType | "");
              setPage(1);
            }}
          >
            <option value="">All resource types</option>
            {targetTypes.map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}
          </Select>
          <Select
            label="Action"
            value={action}
            onChange={(event) => {
              setAction(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All actions</option>
            {actionOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </Select>
        </div>
        <BackgroundFetchIndicator
          active={auditLogs.isFetching && !auditLogs.isPending}
          label="Updating audit log"
        />
        {auditLogs.isPending ? <Spinner label="Loading audit log" /> : null}
        {auditLogs.isError ? (
          <div className="p-5">
            <ErrorMessage error={auditLogs.error} onRetry={() => void auditLogs.refetch()} />
          </div>
        ) : null}
        {auditLogs.data?.results.length === 0 ? (
          <EmptyState
            icon={ClipboardClock}
            title="No audit events found"
            description={hasFilters ? "No events match the selected filters." : "Audited activity will appear here as changes occur."}
            action={hasFilters ? <Button variant="outline" size="sm" onClick={clearFilters}>Clear filters</Button> : undefined}
          />
        ) : null}
        {auditLogs.data && auditLogs.data.results.length > 0 ? (
          <>
            <div className="table-scroll overflow-x-auto">
              <table className="w-full min-w-[940px] text-left">
                <thead className="border-y border-slate-200 bg-slate-100/80 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600">
                  <tr>
                    <th scope="col" className="px-6 py-4">Time</th>
                    <th scope="col" className="px-6 py-4">Actor</th>
                    <th scope="col" className="px-6 py-4">Action</th>
                    <th scope="col" className="px-6 py-4">Target</th>
                    <th scope="col" className="px-6 py-4">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70">
                  {auditLogs.data.results.map((entry) => {
                    const details = auditDetails(entry);
                    return (
                      <tr key={entry.id} className="transition-colors hover:bg-brand-50/35 motion-reduce:transition-none">
                        <td className="whitespace-nowrap px-6 py-4 text-sm text-slate-500">{formatDate(entry.created_at)}</td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center gap-2 text-sm font-semibold text-slate-800">
                            <ShieldCheck className="size-4 text-slate-400" aria-hidden="true" />
                            {entry.actor?.username ?? "System"}
                          </span>
                        </td>
                        <td className="px-6 py-4"><Badge tone="slate">{actionLabels[entry.action] ?? titleCase(entry.action.replaceAll(".", " "))}</Badge></td>
                        <td className="px-6 py-4"><p dir="auto" className="font-semibold text-slate-900">{entry.target_label}</p><p className="mt-0.5 text-xs text-slate-500">{titleCase(entry.target_type)} · #{entry.target_id}</p></td>
                        <td className="px-6 py-4 text-sm text-slate-600">{details.length > 0 ? details.map((detail) => <span key={detail} className="block">{detail}</span>) : <span className="text-slate-400">—</span>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="border-t border-slate-200 bg-slate-50/50 px-6 py-4">
              <Pagination
                page={page}
                count={auditLogs.data.count}
                hasNext={Boolean(auditLogs.data.next)}
                hasPrevious={Boolean(auditLogs.data.previous)}
                onPageChange={setPage}
              />
            </div>
          </>
        ) : null}
      </Card>
    </>
  );
}
