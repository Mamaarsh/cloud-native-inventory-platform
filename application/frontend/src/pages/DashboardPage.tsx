import { Boxes, ClipboardList, PackageSearch, Warehouse } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useInventory } from "@/hooks/useInventory";
import { useOrders } from "@/hooks/useOrders";
import { useProducts } from "@/hooks/useProducts";
import { useWarehouses } from "@/hooks/useWarehouses";
import { formatCurrency, formatDate } from "@/lib/format";

export function DashboardPage() {
  const products = useProducts({ page: 1 });
  const warehouses = useWarehouses({ page: 1 });
  const inventory = useInventory({ page: 1, ordering: "quantity" });
  const orders = useOrders({ page: 1, ordering: "-created_at" });
  const firstError = products.error ?? warehouses.error ?? inventory.error ?? orders.error;
  const unitsOnPage = inventory.data?.results.reduce((total, item) => total + item.quantity, 0) ?? 0;

  const metrics = [
    { label: "Products", value: products.data?.count, isPending: products.isPending, hint: "Catalog records", icon: PackageSearch, color: "bg-blue-50 text-blue-700 ring-blue-100", to: "/products" },
    { label: "Warehouses", value: warehouses.data?.count, isPending: warehouses.isPending, hint: "Configured locations", icon: Warehouse, color: "bg-violet-50 text-violet-700 ring-violet-100", to: "/warehouses" },
    { label: "Orders", value: orders.data?.count, isPending: orders.isPending, hint: "Across all statuses", icon: ClipboardList, color: "bg-amber-50 text-amber-700 ring-amber-100", to: "/orders" },
    {
      label: "Stock records",
      value: inventory.data?.count,
      isPending: inventory.isPending,
      hint: inventory.isPending
        ? "Loading stock data"
        : inventory.data
          ? `${unitsOnPage.toLocaleString()} units in loaded records`
          : "Stock data unavailable",
      icon: Boxes,
      color: "bg-emerald-50 text-emerald-700 ring-emerald-100",
      to: "/inventory",
    },
  ];

  return (
    <>
      <PageHeader
        eyebrow="Command center"
        title="Inventory at a glance"
        description="Operational totals and the latest order activity across the platform."
      />
      {firstError ? (
        <div className="mb-6">
          <ErrorMessage error={firstError} title="Some dashboard data could not be loaded" />
        </div>
      ) : null}
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, isPending, hint, icon: Icon, color, to }) => (
          <Link to={to} key={label} className="group rounded-2xl">
            <Card
              className="h-full p-6 transition duration-200 group-hover:-translate-y-0.5 group-hover:border-slate-300 group-hover:shadow-[0_2px_4px_rgb(15_23_42/0.05),0_14px_36px_rgb(15_23_42/0.07)] motion-reduce:transform-none motion-reduce:transition-none"
              aria-busy={isPending}
            >
              <div className="flex items-start justify-between gap-4">
                <p className="pt-1 text-xs font-bold uppercase tracking-[0.12em] text-slate-500">
                  {label}
                </p>
                <span className={`grid size-12 shrink-0 place-items-center rounded-xl ring-1 ring-inset ${color}`}>
                  <Icon className="size-5" aria-hidden="true" />
                </span>
              </div>
              <div className="mt-5 min-h-12">
                {isPending ? (
                  <Spinner compact label={`Loading ${label.toLowerCase()}`} />
                ) : value !== undefined ? (
                  <p className="text-4xl font-bold tracking-[-0.04em] tabular-nums text-slate-950">
                    {value.toLocaleString()}
                  </p>
                ) : (
                  <p className="flex min-h-12 items-center text-sm font-semibold text-slate-500">
                    Unavailable
                  </p>
                )}
              </div>
              <p className="mt-3 text-xs font-medium text-slate-500">{hint}</p>
            </Card>
          </Link>
        ))}
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/70 px-6 py-5">
            <div>
              <h3 className="font-bold text-slate-950">Recent orders</h3>
              <p className="mt-1 text-xs text-slate-500">Latest fulfillment activity</p>
            </div>
            <Link to="/orders" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
              View all
            </Link>
          </div>
          <div className="divide-y divide-slate-200/70">
            {orders.isPending ? <Spinner label="Loading recent orders" /> : null}
            {orders.data?.results.slice(0, 5).map((order) => {
              const total = order.items.reduce((sum, item) => sum + Number(item.unit_price) * item.quantity, 0);
              return (
                <Link
                  key={order.id}
                  to={`/orders/${order.id}`}
                  className="flex items-center justify-between gap-4 px-6 py-4.5 transition-colors hover:bg-slate-50 motion-reduce:transition-none"
                >
                  <div>
                    <p className="text-sm font-bold text-slate-900">Order #{order.id}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {order.user.username} · {formatDate(order.created_at)}
                    </p>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={order.status} />
                    <p className="mt-2 text-xs font-bold tabular-nums text-slate-700">
                      {formatCurrency(total)}
                    </p>
                  </div>
                </Link>
              );
            })}
            {orders.data?.results.length === 0 ? (
              <p className="px-6 py-12 text-center text-sm text-slate-500">
                No orders have been created yet.
              </p>
            ) : null}
          </div>
        </Card>
        <Card className="overflow-hidden border-slate-900 bg-ink-950 text-white">
          <div className="dashboard-grid flex h-full flex-col p-6">
            <span className="grid size-12 place-items-center rounded-xl border border-white/10 bg-white/[0.07]">
              <Boxes className="size-5 text-brand-500" aria-hidden="true" />
            </span>
            <h3 className="mt-7 text-xl font-bold">Current inventory snapshot</h3>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Monitor catalog coverage, warehouse locations, fulfillment activity, and stock records.
            </p>
            <div className="mt-8 rounded-xl border border-white/10 bg-white/[0.05] p-4 xl:mt-auto">
              <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400">
                Loaded stock sample
              </p>
              <p className="mt-2 text-3xl font-bold tabular-nums">
                {inventory.isPending
                  ? "Loading…"
                  : inventory.data
                    ? unitsOnPage.toLocaleString()
                    : "Unavailable"}
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-400">
                {inventory.data
                  ? "units across the currently loaded records"
                  : inventory.isPending
                    ? "Retrieving current stock records"
                    : "Stock sample could not be loaded"}
              </p>
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}
