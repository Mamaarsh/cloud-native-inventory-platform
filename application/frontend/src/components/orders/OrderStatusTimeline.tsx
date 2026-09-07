import { ArrowRight, History } from "lucide-react";
import { BackgroundFetchIndicator } from "@/components/ui/BackgroundFetchIndicator";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useOrderHistory } from "@/hooks/useOrders";
import { formatDate } from "@/lib/format";

interface OrderStatusTimelineProps {
  orderId: number;
}

export function OrderStatusTimeline({ orderId }: OrderStatusTimelineProps) {
  const history = useOrderHistory(orderId);

  return (
    <Card className="overflow-hidden" aria-busy={history.isFetching}>
      <div className="border-b border-slate-200 bg-slate-50/70 px-6 py-5">
        <h3 className="font-bold text-slate-950">Order timeline</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          Immutable status events recorded by the backend.
        </p>
      </div>

      <BackgroundFetchIndicator
        active={history.isFetching && !history.isPending}
        label="Updating order timeline"
      />

      <div className="p-6">
        {history.isPending ? (
          <Spinner label="Loading order timeline" />
        ) : history.isError ? (
          <ErrorMessage
            error={history.error}
            onRetry={() => void history.refetch()}
            title="Order timeline could not be loaded"
          />
        ) : !history.data || history.data.length === 0 ? (
          <EmptyState
            icon={History}
            title="No recorded status history"
            description="No recorded status history is available for this order."
          />
        ) : (
          <ol aria-label="Order status history" className="space-y-0">
            {history.data.map((entry, index) => {
              const isInitial = entry.from_status === null;
              const isLast = index === history.data.length - 1;

              return (
                <li
                  key={entry.id}
                  className="relative grid grid-cols-[20px_minmax(0,1fr)] gap-3 pb-6 last:pb-0"
                >
                  {!isLast ? (
                    <span
                      className="absolute bottom-0 left-[9px] top-5 w-px bg-slate-200"
                      aria-hidden="true"
                    />
                  ) : null}
                  <span
                    className="relative z-10 mt-1.5 size-5 rounded-full border-4 border-white bg-brand-600 ring-1 ring-brand-200"
                    aria-hidden="true"
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-slate-900">
                      {isInitial ? "Created" : "Status changed"}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {entry.from_status ? (
                        <>
                          <StatusBadge status={entry.from_status} />
                          <ArrowRight
                            className="size-4 shrink-0 text-slate-400"
                            aria-label="changed to"
                          />
                        </>
                      ) : null}
                      <StatusBadge status={entry.to_status} />
                    </div>
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      <time dateTime={entry.created_at}>
                        {formatDate(entry.created_at)}
                      </time>
                      <span aria-hidden="true"> · </span>
                      <span dir="auto">
                        by {entry.performed_by?.username ?? "System"}
                      </span>
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </Card>
  );
}
