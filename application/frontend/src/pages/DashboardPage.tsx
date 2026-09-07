import {
  AlertTriangle,
  Boxes,
  ClipboardList,
  PackageSearch,
  Warehouse,
} from "lucide-react";
import { Link } from "react-router-dom";
import { ProductImage } from "@/components/products/ProductImage";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useInventory } from "@/hooks/useInventory";
import { useOrders } from "@/hooks/useOrders";
import { useAllProducts } from "@/hooks/useProducts";
import { useAllWarehouses } from "@/hooks/useWarehouses";
import { formatCurrency, formatDate } from "@/lib/format";
import {
  getInventoryStatus,
  LOW_STOCK_THRESHOLD,
  needsStockAttention,
} from "@/lib/inventory-status";
import { OrderStatus } from "@/types";

export function DashboardPage() {
  const products = useAllProducts();
  const warehouses = useAllWarehouses();
  const inventory = useInventory({ page: 1, ordering: "quantity" });
  const orders = useOrders({ page: 1, ordering: "-created_at" });
  const pendingOrders = useOrders({ page: 1, status: OrderStatus.Pending });
  const firstError = products.error
    ?? warehouses.error
    ?? inventory.error
    ?? orders.error
    ?? pendingOrders.error;
  const loadedInventory = inventory.data?.results ?? [];
  const unitsOnPage = loadedInventory.reduce(
    (total, item) => total + item.quantity,
    0,
  );
  const lowStockRecords = loadedInventory.filter((item) =>
    needsStockAttention(item.quantity));
  const productMap = new Map(
    products.data?.map((product) => [product.id, product]),
  );
  const warehouseMap = new Map(
    warehouses.data?.map((warehouse) => [warehouse.id, warehouse]),
  );

  const metrics = [
    {
      label: "Total products",
      value: products.data?.length,
      isPending: products.isPending,
      hint: "Catalog records",
      icon: PackageSearch,
      color: "bg-blue-50 text-blue-700 ring-blue-100",
      to: "/products",
    },
    {
      label: "Warehouses",
      value: warehouses.data?.length,
      isPending: warehouses.isPending,
      hint: "Configured locations",
      icon: Warehouse,
      color: "bg-violet-50 text-violet-700 ring-violet-100",
      to: "/warehouses",
    },
    {
      label: "Pending orders",
      value: pendingOrders.data?.count,
      isPending: pendingOrders.isPending,
      hint: "Awaiting fulfillment",
      icon: ClipboardList,
      color: "bg-amber-50 text-amber-700 ring-amber-100",
      to: "/orders",
    },
    {
      label: "Stock records",
      value: inventory.data?.count,
      isPending: inventory.isPending,
      hint: "Tracked product locations",
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
        description="Operational totals, stock attention, and the latest fulfillment activity."
      />

      {firstError ? (
        <div className="mb-6">
          <ErrorMessage
            error={firstError}
            title="Some dashboard data could not be loaded"
          />
        </div>
      ) : null}

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, isPending, hint, icon: Icon, color, to }) => (
          <Link
            to={to}
            key={label}
            className="group rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
          >
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

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <Card className="overflow-hidden" aria-busy={orders.isPending}>
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/70 px-6 py-5">
            <div>
              <h2 className="font-bold text-slate-950">Recent orders</h2>
              <p className="mt-1 text-xs text-slate-500">
                {orders.data
                  ? `Latest activity across ${orders.data.count.toLocaleString()} total orders`
                  : "Latest fulfillment activity"}
              </p>
            </div>
            <Link
              to="/orders"
              className="text-sm font-semibold text-brand-600 hover:text-brand-700"
            >
              View all
            </Link>
          </div>

          <div className="divide-y divide-slate-200/70">
            {orders.isPending ? <Spinner label="Loading recent orders" /> : null}
            {orders.data?.results.slice(0, 5).map((order) => {
              const total = order.items.reduce(
                (sum, item) => sum + Number(item.unit_price) * item.quantity,
                0,
              );

              return (
                <Link
                  key={order.id}
                  to={`/orders/${order.id}`}
                  className="grid gap-3 px-6 py-4.5 transition-colors hover:bg-slate-50 motion-reduce:transition-none sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <ProductImage src={order.items[0]?.product.image} size="sm" />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <p className="text-sm font-bold text-slate-900">
                          Order #{order.id}
                        </p>
                        <span className="text-xs text-slate-400">
                          {order.items.length} line{order.items.length === 1 ? "" : "s"}
                        </span>
                      </div>
                      <p dir="auto" className="mt-1 truncate text-xs font-medium text-slate-600">
                        {order.user.username}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        {formatDate(order.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-4 pl-[3.75rem] sm:block sm:pl-0 sm:text-right">
                    <StatusBadge status={order.status} />
                    <p className="text-sm font-bold tabular-nums text-slate-800 sm:mt-2">
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

        <Card
          className="self-start overflow-hidden"
          aria-busy={inventory.isPending || products.isPending || warehouses.isPending}
        >
          <div className="flex items-center justify-between gap-4 border-b border-slate-200 bg-slate-50/70 px-6 py-5">
            <div className="flex min-w-0 items-center gap-3">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-100">
                <AlertTriangle className="size-5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <h2 className="font-bold text-slate-950">Stock attention</h2>
                <p className="mt-1 text-xs text-slate-500">
                  Lowest-quantity loaded records
                </p>
              </div>
            </div>
            {inventory.data ? (
              <span
                className="shrink-0 text-sm font-bold tabular-nums text-slate-700"
                aria-label={`${lowStockRecords.length} of ${loadedInventory.length} loaded records need attention`}
              >
                {lowStockRecords.length}/{loadedInventory.length}
              </span>
            ) : null}
          </div>

          {inventory.isPending || products.isPending || warehouses.isPending ? (
            <Spinner label="Loading stock attention" />
          ) : lowStockRecords.length > 0 ? (
            <div className="divide-y divide-slate-200/70">
              {lowStockRecords.slice(0, 5).map((item) => {
                const product = productMap.get(item.product);
                const warehouse = warehouseMap.get(item.warehouse);
                const stockStatus = getInventoryStatus(item.quantity);

                return (
                  <div key={item.id} className="flex items-center gap-3 px-6 py-4">
                    <ProductImage src={product?.image} size="sm" />
                    <div className="min-w-0 flex-1">
                      <p dir="auto" className="truncate text-sm font-semibold text-slate-900">
                        {product?.name ?? `Product #${item.product}`}
                      </p>
                      <p dir="auto" className="mt-1 truncate text-xs text-slate-500">
                        {warehouse?.name ?? `Warehouse #${item.warehouse}`}
                      </p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-lg font-bold tabular-nums text-slate-950">
                        {item.quantity.toLocaleString()}
                      </p>
                      <Badge tone={stockStatus.tone}>{stockStatus.label}</Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : inventory.data && loadedInventory.length > 0 ? (
            <div className="px-6 py-8 text-center">
              <span className="mx-auto grid size-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-100">
                <Boxes className="size-5" aria-hidden="true" />
              </span>
              <p className="mt-3 text-sm font-semibold text-slate-800">
                All loaded stock records are healthy.
              </p>
              <p className="mt-1 text-xs text-slate-500">
                No quantity below {LOW_STOCK_THRESHOLD} in this loaded sample.
              </p>
            </div>
          ) : inventory.data ? (
            <div className="px-6 py-8 text-center">
              <span className="mx-auto grid size-10 place-items-center rounded-xl bg-slate-100 text-slate-500 ring-1 ring-inset ring-slate-200">
                <Boxes className="size-5" aria-hidden="true" />
              </span>
              <p className="mt-3 text-sm font-semibold text-slate-800">
                No stock records are available yet.
              </p>
            </div>
          ) : (
            <p className="px-6 py-8 text-center text-sm text-slate-500">
              Stock attention is unavailable.
            </p>
          )}

          {inventory.data ? (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-slate-50/50 px-6 py-4">
              <p className="text-xs text-slate-500">
                <strong className="font-bold tabular-nums text-slate-700">
                  {unitsOnPage.toLocaleString()}
                </strong>{" "}
                units across {loadedInventory.length} loaded records
              </p>
              <Link
                to="/inventory"
                className="text-sm font-semibold text-brand-600 hover:text-brand-700"
              >
                Review inventory
              </Link>
            </div>
          ) : null}
        </Card>
      </div>
    </>
  );
}
