import { ArrowRight, Boxes, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import { BackgroundFetchIndicator } from "@/components/ui/BackgroundFetchIndicator";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Pagination } from "@/components/ui/Pagination";
import { Spinner } from "@/components/ui/Spinner";
import { useInventoryMovements } from "@/hooks/useInventory";
import { formatDate, titleCase } from "@/lib/format";

interface InventoryMovementHistoryProps {
  inventoryId: number;
  page: number;
  onPageChange: (page: number) => void;
}

export function InventoryMovementHistory({
  inventoryId,
  page,
  onPageChange,
}: InventoryMovementHistoryProps) {
  const movements = useInventoryMovements(inventoryId, page);

  if (movements.isPending) {
    return <Spinner label="Loading stock movement history" />;
  }

  if (movements.isError) {
    return (
      <ErrorMessage
        error={movements.error}
        onRetry={() => void movements.refetch()}
        title="Movement history could not be loaded"
      />
    );
  }

  if (!movements.data || movements.data.results.length === 0) {
    return (
      <EmptyState
        icon={Boxes}
        title="No movement history"
        description="History for existing stock begins when movement tracking is deployed."
      />
    );
  }

  return (
    <div aria-busy={movements.isFetching}>
      <BackgroundFetchIndicator
        active={movements.isFetching && !movements.isPending}
        label="Updating movement history"
      />
      <div className="divide-y divide-slate-200/70 overflow-hidden rounded-xl border border-slate-200">
        {movements.data.results.map((movement) => {
          const isIncrease = movement.quantity_delta > 0;
          const signedDelta = `${isIncrease ? "+" : ""}${movement.quantity_delta.toLocaleString()}`;

          return (
            <article key={movement.id} className="p-4 sm:p-5">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex min-w-0 items-start gap-3">
                  <span
                    className={`min-w-16 rounded-xl px-3 py-2 text-center text-lg font-bold tabular-nums ring-1 ring-inset ${
                      isIncrease
                        ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                        : "bg-rose-50 text-rose-700 ring-rose-200"
                    }`}
                    aria-label={`${isIncrease ? "Increase" : "Decrease"} of ${Math.abs(movement.quantity_delta)}`}
                  >
                    {signedDelta}
                  </span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={isIncrease ? "green" : "red"}>
                        {titleCase(movement.movement_type)}
                      </Badge>
                      <span className="inline-flex items-center gap-1.5 text-sm font-bold tabular-nums text-slate-800">
                        {movement.quantity_before.toLocaleString()}
                        <ArrowRight className="size-3.5 text-slate-400" aria-hidden="true" />
                        {movement.quantity_after.toLocaleString()}
                      </span>
                    </div>
                    <p dir="auto" className="mt-2 text-sm leading-6 text-slate-700">
                      {movement.reason || "No additional reason provided."}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                      <span>
                        by {movement.performed_by?.username ?? "System"}
                      </span>
                      {movement.order_id ? (
                        <Link
                          to={`/orders/${movement.order_id}`}
                          className="inline-flex items-center gap-1 font-semibold text-brand-600 hover:text-brand-700"
                        >
                          Order #{movement.order_id}
                          <ExternalLink className="size-3" aria-hidden="true" />
                        </Link>
                      ) : null}
                    </div>
                  </div>
                </div>
                <time
                  dateTime={movement.created_at}
                  className="shrink-0 text-xs text-slate-500"
                >
                  {formatDate(movement.created_at)}
                </time>
              </div>
            </article>
          );
        })}
      </div>
      <div className="mt-4">
        <Pagination
          page={page}
          count={movements.data.count}
          hasNext={Boolean(movements.data.next)}
          hasPrevious={Boolean(movements.data.previous)}
          onPageChange={onPageChange}
        />
      </div>
    </div>
  );
}
