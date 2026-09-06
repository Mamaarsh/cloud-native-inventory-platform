import { useState } from "react";
import { ArrowLeft, CheckCircle2, CreditCard, MapPin, UserRound } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { ProductImage } from "@/components/products/ProductImage";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useAuth } from "@/hooks/useAuth";
import { useChangeOrderStatus, useOrder, usePayOrder } from "@/hooks/useOrders";
import { useSuccessFeedback } from "@/hooks/useSuccessFeedback";
import { formatCurrency, formatDate, titleCase } from "@/lib/format";
import { allowedStatusTransitions } from "@/lib/order-status";
import { OrderStatus, ROLES } from "@/types";

export function OrderDetailPage() {
  const { id: idParam } = useParams();
  const orderId = Number(idParam);
  const order = useOrder(orderId);
  const statusMutation = useChangeOrderStatus();
  const paymentMutation = usePayOrder();
  const { hasRole } = useAuth();
  const { showSuccess } = useSuccessFeedback();
  const [payOpen, setPayOpen] = useState(false);

  if (!Number.isInteger(orderId) || orderId <= 0) return <ErrorMessage error={new Error("Invalid order ID.")} />;
  if (order.isPending) return <Spinner label="Loading order" />;
  if (order.isError) return <ErrorMessage error={order.error} onRetry={() => void order.refetch()} title="Order could not be loaded" />;
  if (!order.data) return null;

  const total = order.data.items.reduce((sum, item) => sum + Number(item.unit_price) * item.quantity, 0);
  const transitions = allowedStatusTransitions(order.data.status, hasRole(ROLES.admin), hasRole(ROLES.warehouseManager));
  const canPay = hasRole(ROLES.admin) && ![OrderStatus.Delivered, OrderStatus.Cancelled].includes(order.data.status);
  const pendingTransition = statusMutation.isPending ? statusMutation.variables?.status : undefined;

  async function changeStatus(status: OrderStatus): Promise<void> {
    await statusMutation.mutateAsync({ id: orderId, status });
    showSuccess(`Order status changed to ${titleCase(status)}.`);
  }

  async function pay(): Promise<void> {
    await paymentMutation.mutateAsync(orderId);
    setPayOpen(false);
  }

  return (
    <>
      <Link to="/orders" className="mb-5 inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-brand-700"><ArrowLeft className="size-4" /> Back to orders</Link>
      <PageHeader
        eyebrow={`Order #${order.data.id}`}
        title={`${order.data.items.length} item${order.data.items.length === 1 ? "" : "s"} · ${formatCurrency(total)}`}
        description={`Created ${formatDate(order.data.created_at)} by ${order.data.user.username}.`}
        actions={<><StatusBadge status={order.data.status} />{canPay ? <Button variant="outline" onClick={() => setPayOpen(true)}><CreditCard className="size-4" /> Pay order</Button> : null}</>}
      />
      {statusMutation.isError ? <div className="mb-5"><ErrorMessage error={statusMutation.error} title="Status could not be changed" /></div> : null}
      {paymentMutation.isError ? <div className="mb-5"><ErrorMessage error={paymentMutation.error} title="Payment could not be processed" /></div> : null}
      {paymentMutation.data ? <div className="mb-5 flex items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-800"><CheckCircle2 className="mt-0.5 size-5" /><div><p className="font-bold">Payment {titleCase(paymentMutation.data.status)}</p><p className="mt-1 text-sm">{formatCurrency(paymentMutation.data.amount)} via {paymentMutation.data.provider}{paymentMutation.data.provider_reference ? ` · ${paymentMutation.data.provider_reference}` : ""}</p></div></div> : null}
      <div className="grid gap-6 xl:grid-cols-[1fr_340px]">
        <Card className="overflow-hidden">
          <div className="border-b border-slate-200 bg-slate-50/70 px-6 py-5"><h3 className="font-bold text-slate-950">Order items</h3><p className="mt-1 text-xs text-slate-500">Unit prices are historical snapshots captured at creation.</p></div>
          <div className="divide-y divide-slate-200/70">
            {order.data.items.map((item) => (
              <div
                key={item.id}
                className="grid grid-cols-[auto_minmax(0,1fr)] gap-5 px-6 py-6 lg:grid-cols-[auto_minmax(0,1fr)_190px] lg:items-center lg:gap-6"
              >
                <ProductImage
                  src={item.product.image}
                  size="lg"
                  className="bg-white shadow-sm sm:size-24 lg:size-28"
                />

                <div className="min-w-0">
                  <p dir="auto" className="text-lg font-bold leading-6 text-slate-950">
                    {item.product.name}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-xs font-medium text-slate-600">
                      {item.product.sku}
                    </span>
                    <span className="text-xs text-slate-500">
                      Product #{item.product.id} · Item #{item.id}
                    </span>
                  </div>
                  <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2.5">
                    <MapPin className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden="true" />
                    <div className="min-w-0">
                      <p dir="auto" className="text-sm font-semibold text-slate-800">
                        {item.warehouse.name}
                      </p>
                      <p dir="auto" className="mt-0.5 text-xs text-slate-500">
                        {item.warehouse.location}
                      </p>
                    </div>
                  </div>
                </div>

                <dl className="col-span-2 grid grid-cols-2 gap-4 border-t border-slate-200 pt-4 lg:col-span-1 lg:grid-cols-1 lg:border-l lg:border-t-0 lg:py-1 lg:pl-6 lg:text-right">
                  <div>
                    <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      Historical unit price
                    </dt>
                    <dd className="mt-1 text-sm font-semibold tabular-nums text-slate-800">
                      {formatCurrency(item.unit_price)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      Quantity
                    </dt>
                    <dd className="mt-1 text-sm font-semibold tabular-nums text-slate-800">
                      {item.quantity.toLocaleString()}
                    </dd>
                  </div>
                  <div className="col-span-2 border-t border-slate-200 pt-3 lg:col-span-1">
                    <dt className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      Line subtotal
                    </dt>
                    <dd className="mt-1 text-lg font-bold tabular-nums text-slate-950">
                      {formatCurrency(Number(item.unit_price) * item.quantity)}
                    </dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
          <div className="flex justify-between border-t border-slate-200 bg-slate-100/70 px-6 py-5"><span className="font-semibold text-slate-700">Order total</span><span className="text-xl font-bold tabular-nums text-slate-950">{formatCurrency(total)}</span></div>
        </Card>
        <div className="space-y-6">
          <Card className="p-6"><h3 className="font-bold text-slate-950">Status workflow</h3><p className="mt-2 text-sm leading-6 text-slate-500">Only transitions allowed for your role and the current state are shown.</p>{transitions.length > 0 ? <div className="mt-5 space-y-2">{transitions.map((status) => <Button key={status} variant={status === OrderStatus.Cancelled ? "danger" : "primary"} className="w-full" isLoading={pendingTransition === status} disabled={statusMutation.isPending && pendingTransition !== status} onClick={() => void changeStatus(status)}>Mark as {titleCase(status)}</Button>)}</div> : <p className="mt-5 rounded-xl bg-slate-100 p-3 text-sm text-slate-600">No status actions are available.</p>}</Card>
          <Card className="p-6"><h3 className="font-bold text-slate-950">Customer</h3><div className="mt-4 flex items-center gap-3"><span className="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-700"><UserRound className="size-5" /></span><div><p className="text-sm font-semibold text-slate-900">{order.data.user.username}</p><p className="text-xs text-slate-500">{order.data.user.email || "No email address"}</p></div></div><dl className="mt-5 space-y-3 border-t border-slate-200 pt-4 text-sm"><div className="flex justify-between"><dt className="text-slate-500">Created</dt><dd className="font-medium text-slate-700">{formatDate(order.data.created_at)}</dd></div><div className="flex justify-between"><dt className="text-slate-500">Updated</dt><dd className="font-medium text-slate-700">{formatDate(order.data.updated_at)}</dd></div></dl></Card>
        </div>
      </div>
      <Modal open={payOpen} onClose={() => setPayOpen(false)} title="Confirm payment" description="The backend payment service is idempotent for successful payments." size="sm" isBusy={paymentMutation.isPending}>
        <p className="text-sm leading-6 text-slate-600">Process a payment of <strong>{formatCurrency(total)}</strong> for order #{orderId}?</p>
        <div className="mt-6 flex justify-end gap-3"><Button variant="outline" disabled={paymentMutation.isPending} onClick={() => setPayOpen(false)}>Cancel</Button><Button data-modal-destructive="true" isLoading={paymentMutation.isPending} onClick={() => void pay()}><CreditCard className="size-4" /> Process payment</Button></div>
      </Modal>
    </>
  );
}
