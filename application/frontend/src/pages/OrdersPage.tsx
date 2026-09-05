import { useState } from "react";
import { ClipboardList, Plus, Search } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { RoleGuard } from "@/auth/RoleGuard";
import { OrderCreateForm } from "@/components/orders/OrderCreateForm";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { Select } from "@/components/ui/Select";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useCreateOrder, useOrders } from "@/hooks/useOrders";
import { formatCurrency, formatDate, titleCase } from "@/lib/format";
import { OrderStatus, ROLES, type OrderCreateRequest } from "@/types";

export function OrdersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<OrderStatus | "">("");
  const [createOpen, setCreateOpen] = useState(false);
  const orders = useOrders({ page, search: search || undefined, status, ordering: "-created_at" });
  const createMutation = useCreateOrder();
  const navigate = useNavigate();

  async function submitOrder(payload: OrderCreateRequest): Promise<void> {
    const order = await createMutation.mutateAsync(payload);
    setCreateOpen(false);
    void navigate(`/orders/${order.id}`);
  }

  return (
    <>
      <PageHeader eyebrow="Fulfillment" title="Orders" description="Track customer orders from creation through delivery, with historical pricing preserved on every line." actions={<RoleGuard role={ROLES.admin}><Button onClick={() => setCreateOpen(true)}><Plus className="size-4" /> Create order</Button></RoleGuard>} />
      <Card>
        <div className="grid gap-4 border-b border-slate-200 p-5 md:grid-cols-[1fr_240px]">
          <div className="relative self-end"><Search className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search customer or product" aria-label="Search orders" className="min-h-11 w-full rounded-xl border border-slate-300 pl-10 pr-4 text-sm" /></div>
          <Select label="Status" value={status} onChange={(event) => { setStatus(event.target.value as OrderStatus | ""); setPage(1); }}><option value="">All statuses</option>{Object.values(OrderStatus).map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}</Select>
        </div>
        {orders.isPending ? <div className="p-8 text-sm text-slate-500">Loading orders…</div> : null}
        {orders.isError ? <div className="p-5"><ErrorMessage error={orders.error} onRetry={() => void orders.refetch()} /></div> : null}
        {orders.data?.results.length === 0 ? <EmptyState icon={ClipboardList} title="No orders found" description={search || status ? "Adjust the search or status filter." : "No orders have been created yet."} /> : null}
        {orders.data && orders.data.results.length > 0 ? (
          <>
            <div className="table-scroll overflow-x-auto"><table className="w-full min-w-[820px] text-left"><thead className="bg-slate-50/80 text-xs font-bold uppercase tracking-wider text-slate-500"><tr><th className="px-6 py-4">Order</th><th className="px-6 py-4">Customer</th><th className="px-6 py-4">Items</th><th className="px-6 py-4">Amount</th><th className="px-6 py-4">Status</th><th className="px-6 py-4">Created</th></tr></thead><tbody className="divide-y divide-slate-100">{orders.data.results.map((order) => { const total = order.items.reduce((sum, item) => sum + Number(item.unit_price) * item.quantity, 0); return <tr key={order.id} className="hover:bg-slate-50/70"><td className="px-6 py-4"><Link to={`/orders/${order.id}`} className="font-bold text-brand-700 hover:text-brand-500">#{order.id}</Link></td><td className="px-6 py-4"><p className="text-sm font-semibold text-slate-900">{order.user.username}</p><p className="mt-0.5 text-xs text-slate-400">{order.user.email || "No email"}</p></td><td className="px-6 py-4 text-sm text-slate-600">{order.items.length} line{order.items.length === 1 ? "" : "s"}</td><td className="px-6 py-4 text-sm font-bold text-slate-800">{formatCurrency(total)}</td><td className="px-6 py-4"><StatusBadge status={order.status} /></td><td className="px-6 py-4 text-sm text-slate-500">{formatDate(order.created_at)}</td></tr>; })}</tbody></table></div>
            <div className="border-t border-slate-200 p-5"><Pagination page={page} count={orders.data.count} hasNext={Boolean(orders.data.next)} hasPrevious={Boolean(orders.data.previous)} onPageChange={setPage} /></div>
          </>
        ) : null}
      </Card>
      <Modal open={createOpen} onClose={() => { setCreateOpen(false); createMutation.reset(); }} title="Create order" description="Stock is validated and reserved atomically by the backend." size="lg">
        <OrderCreateForm onSubmit={submitOrder} onCancel={() => setCreateOpen(false)} isSubmitting={createMutation.isPending} serverError={createMutation.error} />
      </Modal>
    </>
  );
}
