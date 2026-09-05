import { Boxes, ClipboardList, PackageSearch, Warehouse } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { PageHeader } from "@/components/ui/PageHeader";
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
    { label: "Products", value: products.data?.count, hint: "Catalog records", icon: PackageSearch, color: "bg-blue-50 text-blue-700", to: "/products" },
    { label: "Warehouses", value: warehouses.data?.count, hint: "Active locations", icon: Warehouse, color: "bg-violet-50 text-violet-700", to: "/warehouses" },
    { label: "Orders", value: orders.data?.count, hint: "Across all statuses", icon: ClipboardList, color: "bg-amber-50 text-amber-700", to: "/orders" },
    { label: "Inventory", value: inventory.data?.count, hint: `${unitsOnPage.toLocaleString()} units on this page`, icon: Boxes, color: "bg-emerald-50 text-emerald-700", to: "/inventory" },
  ];

  return (
    <>
      <PageHeader eyebrow="Command center" title="Inventory at a glance" description="Live operational totals and the latest order activity from the platform API." />
      {firstError ? <div className="mb-6"><ErrorMessage error={firstError} title="Some dashboard data could not be loaded" /></div> : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(({ label, value, hint, icon: Icon, color, to }) => (
          <Link to={to} key={label} className="group">
            <Card className="h-full p-5 transition duration-200 group-hover:-translate-y-0.5 group-hover:border-brand-200">
              <div className="flex items-start justify-between"><div><p className="text-sm font-semibold text-slate-500">{label}</p><p className="mt-3 text-3xl font-bold tracking-tight text-slate-950">{value ?? "—"}</p></div><span className={`grid size-11 place-items-center rounded-xl ${color}`}><Icon className="size-5" /></span></div>
              <p className="mt-4 text-xs text-slate-400">{hint}</p>
            </Card>
          </Link>
        ))}
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-[1.45fr_0.55fr]">
        <Card>
          <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5"><div><h3 className="font-bold text-slate-950">Recent orders</h3><p className="mt-1 text-xs text-slate-500">Latest fulfillment activity</p></div><Link to="/orders" className="text-sm font-semibold text-brand-700 hover:text-brand-500">View all</Link></div>
          <div className="divide-y divide-slate-100">
            {orders.data?.results.slice(0, 5).map((order) => {
              const total = order.items.reduce((sum, item) => sum + Number(item.unit_price) * item.quantity, 0);
              return <Link key={order.id} to={`/orders/${order.id}`} className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-slate-50"><div><p className="text-sm font-bold text-slate-900">Order #{order.id}</p><p className="mt-1 text-xs text-slate-500">{order.user.username} · {formatDate(order.created_at)}</p></div><div className="text-right"><StatusBadge status={order.status} /><p className="mt-1.5 text-xs font-semibold text-slate-600">{formatCurrency(total)}</p></div></Link>;
            })}
            {orders.data?.results.length === 0 ? <p className="px-6 py-12 text-center text-sm text-slate-500">No orders have been created yet.</p> : null}
          </div>
        </Card>
        <Card className="overflow-hidden bg-ink-950 text-white">
          <div className="dashboard-grid h-full p-6">
            <span className="grid size-11 place-items-center rounded-xl bg-white/10"><Boxes className="size-5 text-brand-500" /></span>
            <h3 className="mt-7 text-xl font-bold">Operational data, kept honest.</h3>
            <p className="mt-3 text-sm leading-6 text-slate-400">Dashboard totals come directly from paginated API counts. No placeholder metrics or synthetic records are shown.</p>
            <div className="mt-8 rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-xs font-bold uppercase tracking-wider text-slate-500">Inventory signal</p><p className="mt-2 text-2xl font-bold">{unitsOnPage.toLocaleString()}</p><p className="mt-1 text-xs text-slate-400">units across the current inventory page</p></div>
          </div>
        </Card>
      </div>
    </>
  );
}
