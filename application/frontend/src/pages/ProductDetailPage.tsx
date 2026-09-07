import { useState } from "react";
import axios from "axios";
import {
  ArrowLeft,
  Boxes,
  Pencil,
  Tag,
  Trash2,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { RoleGuard } from "@/auth/RoleGuard";
import { ProductForm } from "@/components/products/ProductForm";
import { ProductImage } from "@/components/products/ProductImage";
import { BackgroundFetchIndicator } from "@/components/ui/BackgroundFetchIndicator";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { Spinner } from "@/components/ui/Spinner";
import { useInventory } from "@/hooks/useInventory";
import {
  useDeleteProduct,
  useProduct,
  useUpdateProduct,
} from "@/hooks/useProducts";
import { useSuccessFeedback } from "@/hooks/useSuccessFeedback";
import { useAllWarehouses } from "@/hooks/useWarehouses";
import { formatCurrency, formatDate } from "@/lib/format";
import { getInventoryStatus } from "@/lib/inventory-status";
import type { ProductRequest } from "@/types";
import { ROLES } from "@/types";

export function ProductDetailPage() {
  const { id: idParam } = useParams();
  const productId = Number(idParam);
  const hasValidProductId = Number.isInteger(productId) && productId > 0;
  const [inventoryPage, setInventoryPage] = useState(1);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const product = useProduct(productId);
  const inventory = useInventory(
    {
      page: inventoryPage,
      product: hasValidProductId ? productId : undefined,
      ordering: "quantity",
    },
    hasValidProductId && product.isSuccess,
  );
  const warehouses = useAllWarehouses(
    hasValidProductId && product.isSuccess,
  );
  const updateMutation = useUpdateProduct();
  const deleteMutation = useDeleteProduct();
  const navigate = useNavigate();
  const { showSuccess } = useSuccessFeedback();

  function closeEditModal(): void {
    setEditOpen(false);
    updateMutation.reset();
  }

  function closeDeleteModal(): void {
    setDeleteOpen(false);
    deleteMutation.reset();
  }

  async function saveProduct(payload: ProductRequest): Promise<void> {
    await updateMutation.mutateAsync({ id: productId, payload });
    closeEditModal();
    showSuccess("Product updated successfully.");
  }

  async function deleteProduct(): Promise<void> {
    try {
      await deleteMutation.mutateAsync(productId);
      showSuccess("Product deleted.");
      void navigate("/products", { replace: true });
    } catch {
      // The mutation error remains visible in the confirmation modal.
    }
  }

  const backLink = (
    <Link
      to="/products"
      className="mb-5 inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-brand-700"
    >
      <ArrowLeft className="size-4" aria-hidden="true" /> Back to products
    </Link>
  );

  if (!hasValidProductId) {
    return (
      <>
        {backLink}
        <ErrorMessage
          error={new Error("The product ID in this URL is invalid.")}
          title="Product could not be opened"
        />
      </>
    );
  }

  if (product.isPending) {
    return (
      <>
        {backLink}
        <Card aria-busy="true">
          <Spinner label="Loading product" />
        </Card>
      </>
    );
  }

  if (product.isError) {
    const notFound = axios.isAxiosError(product.error)
      && product.error.response?.status === 404;

    return (
      <>
        {backLink}
        {notFound ? (
          <Card>
            <EmptyState
              icon={Tag}
              title="Product not found"
              description="This product may have been removed or the link may be incorrect."
              action={(
                <Link
                  to="/products"
                  className="inline-flex min-h-9 items-center rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"
                >
                  Return to products
                </Link>
              )}
            />
          </Card>
        ) : (
          <ErrorMessage
            error={product.error}
            onRetry={() => void product.refetch()}
            title="Product could not be loaded"
          />
        )}
      </>
    );
  }

  if (!product.data) return null;

  const warehouseMap = new Map(
    warehouses.data?.map((warehouse) => [warehouse.id, warehouse]),
  );
  const loadedInventory = inventory.data?.results ?? [];
  const loadedUnits = loadedInventory.reduce(
    (total, record) => total + record.quantity,
    0,
  );
  const inventoryError = inventory.error ?? warehouses.error;

  return (
    <>
      {backLink}
      <PageHeader
        eyebrow={`Product #${product.data.id}`}
        title={product.data.name}
        description={`Catalog identity and warehouse availability for SKU ${product.data.sku}.`}
        actions={(
          <RoleGuard role={ROLES.admin}>
            <Button variant="outline" onClick={() => setEditOpen(true)}>
              <Pencil className="size-4" aria-hidden="true" /> Edit product
            </Button>
            <Button variant="danger" onClick={() => setDeleteOpen(true)}>
              <Trash2 className="size-4" aria-hidden="true" /> Delete
            </Button>
          </RoleGuard>
        )}
      />

      <Card className="overflow-hidden">
        <div className="grid gap-6 p-6 md:grid-cols-[auto_minmax(0,1fr)] md:items-center md:p-8">
          <ProductImage
            src={product.data.image}
            alt={product.data.image ? `${product.data.name} product image` : ""}
            size="lg"
            className="size-28 bg-white shadow-sm sm:size-32"
          />
          <div className="min-w-0">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">
                  Unit price
                </p>
                <p className="mt-2 text-3xl font-bold tracking-[-0.03em] tabular-nums text-slate-950">
                  {formatCurrency(product.data.price)}
                </p>
              </div>
              <Badge tone={product.data.is_active ? "green" : "slate"}>
                {product.data.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>

            <dl className="mt-6 grid gap-4 border-t border-slate-200 pt-5 sm:grid-cols-2 xl:grid-cols-4">
              <div>
                <dt className="text-xs font-semibold text-slate-500">SKU</dt>
                <dd className="mt-1 break-all font-mono text-sm font-semibold text-slate-800">
                  {product.data.sku}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-slate-500">Product ID</dt>
                <dd className="mt-1 text-sm font-semibold tabular-nums text-slate-800">
                  {product.data.id}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-slate-500">Created</dt>
                <dd className="mt-1 text-sm font-medium text-slate-700">
                  {formatDate(product.data.created_at)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-slate-500">Last updated</dt>
                <dd className="mt-1 text-sm font-medium text-slate-700">
                  {formatDate(product.data.updated_at)}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </Card>

      <Card className="mt-6 overflow-hidden" aria-busy={inventory.isPending || warehouses.isPending}>
        <div className="flex flex-col gap-4 border-b border-slate-200 bg-slate-50/70 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-bold text-slate-950">Warehouse inventory</h2>
            <p className="mt-1 text-xs text-slate-500">
              {inventory.data
                ? `${inventory.data.count.toLocaleString()} stock records for this product`
                : "Availability by warehouse"}
            </p>
          </div>
          {inventory.data && loadedInventory.length > 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-right shadow-sm">
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">
                Units on this page
              </p>
              <p className="mt-1 text-xl font-bold tabular-nums text-slate-950">
                {loadedUnits.toLocaleString()}
              </p>
            </div>
          ) : null}
        </div>

        <BackgroundFetchIndicator
          active={inventory.isFetching && !inventory.isPending}
          label="Updating product inventory"
        />

        {inventory.isPending || warehouses.isPending ? (
          <Spinner label="Loading product inventory" />
        ) : null}
        {inventoryError ? (
          <div className="p-5">
            <ErrorMessage
              error={inventoryError}
              onRetry={() => {
                void inventory.refetch();
                void warehouses.refetch();
              }}
              title="Product inventory could not be loaded"
            />
          </div>
        ) : null}
        {inventory.data && inventory.data.results.length === 0 ? (
          <EmptyState
            icon={Boxes}
            title="No inventory records"
            description="This product is not currently tracked in any warehouse."
          />
        ) : null}

        {inventory.data && inventory.data.results.length > 0 ? (
          <>
            <div className="table-scroll overflow-x-auto">
              <table className="w-full min-w-[640px] text-left">
                <thead className="border-y border-slate-200 bg-slate-100/80 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600">
                  <tr>
                    <th scope="col" className="px-6 py-4">Warehouse</th>
                    <th scope="col" className="px-6 py-4">Location</th>
                    <th scope="col" className="px-6 py-4 text-right">Quantity</th>
                    <th scope="col" className="px-6 py-4">Status</th>
                    <th scope="col" className="px-6 py-4">Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70">
                  {inventory.data.results.map((record) => {
                    const warehouse = warehouseMap.get(record.warehouse);
                    const stockStatus = getInventoryStatus(record.quantity);

                    return (
                      <tr key={record.id} className="transition-colors hover:bg-brand-50/35 motion-reduce:transition-none">
                        <td dir="auto" className="px-6 py-4 text-sm font-semibold text-slate-900">
                          {warehouse?.name ?? `Warehouse #${record.warehouse}`}
                        </td>
                        <td dir="auto" className="px-6 py-4 text-sm text-slate-500">
                          {warehouse?.location || "Location unavailable"}
                        </td>
                        <td className="px-6 py-4 text-right text-lg font-bold tabular-nums text-slate-950">
                          {record.quantity.toLocaleString()}
                        </td>
                        <td className="px-6 py-4">
                          <Badge tone={stockStatus.tone}>{stockStatus.label}</Badge>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-500">
                          {formatDate(record.updated_at)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="border-t border-slate-200 bg-slate-50/50 px-6 py-4">
              <Pagination
                page={inventoryPage}
                count={inventory.data.count}
                hasNext={Boolean(inventory.data.next)}
                hasPrevious={Boolean(inventory.data.previous)}
                onPageChange={setInventoryPage}
              />
            </div>
          </>
        ) : null}
      </Card>

      <Modal
        open={editOpen}
        onClose={closeEditModal}
        title="Edit product"
        description="Catalog fields are validated again by the backend."
      >
        <ProductForm
          product={product.data}
          onSubmit={saveProduct}
          onCancel={closeEditModal}
          isSubmitting={updateMutation.isPending}
          serverError={updateMutation.error}
        />
      </Modal>

      <Modal
        open={deleteOpen}
        onClose={closeDeleteModal}
        title="Delete product"
        description="This action cannot be undone."
        size="sm"
        isBusy={deleteMutation.isPending}
      >
        {deleteMutation.isError ? (
          <div className="mb-4">
            <ErrorMessage
              error={deleteMutation.error}
              title="Product could not be deleted"
              fallbackMessage="The product could not be deleted. Please try again."
            />
          </div>
        ) : null}
        <p className="text-sm leading-6 text-slate-600">
          Delete <strong dir="auto">{product.data.name}</strong>? Products referenced by
          inventory or orders must be deactivated through Edit instead.
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <Button
            variant="outline"
            disabled={deleteMutation.isPending}
            onClick={closeDeleteModal}
          >
            Cancel
          </Button>
          <Button
            data-modal-destructive="true"
            variant="danger"
            isLoading={deleteMutation.isPending}
            onClick={() => void deleteProduct()}
          >
            Delete product
          </Button>
        </div>
      </Modal>
    </>
  );
}
