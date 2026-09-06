import { useState } from "react";
import { Boxes, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { RoleGuard } from "@/auth/RoleGuard";
import { InventoryForm } from "@/components/inventory/InventoryForm";
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
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import {
  useCreateInventory,
  useDeleteInventory,
  useInventory,
  useUpdateInventory,
} from "@/hooks/useInventory";
import { useAuth } from "@/hooks/useAuth";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useSuccessFeedback } from "@/hooks/useSuccessFeedback";
import { useAllProducts } from "@/hooks/useProducts";
import { useAllWarehouses } from "@/hooks/useWarehouses";
import { formatDate } from "@/lib/format";
import type { Inventory, InventoryRequest } from "@/types";
import { ROLES } from "@/types";

const inventoryCreators = [ROLES.admin, ROLES.warehouseManager, ROLES.operator];
const inventoryEditors = [ROLES.admin, ROLES.warehouseManager];

export function InventoryPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [product, setProduct] = useState<number | undefined>();
  const [warehouse, setWarehouse] = useState<number | undefined>();
  const [editing, setEditing] = useState<Inventory | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState<Inventory | null>(null);
  const debouncedSearch = useDebouncedValue(search);

  const inventory = useInventory({
    page,
    search: debouncedSearch || undefined,
    product,
    warehouse,
    ordering: "quantity",
  });
  const products = useAllProducts();
  const warehouses = useAllWarehouses();
  const createMutation = useCreateInventory();
  const updateMutation = useUpdateInventory();
  const deleteMutation = useDeleteInventory();
  const { hasRole } = useAuth();
  const { showSuccess } = useSuccessFeedback();

  const productMap = new Map(products.data?.map((item) => [item.id, item]));
  const warehouseMap = new Map(warehouses.data?.map((item) => [item.id, item]));
  const hasFilters = Boolean(debouncedSearch || product || warehouse);
  const canCreateInventory = hasRole(inventoryCreators);

  function clearFilters(): void {
    setSearch("");
    setProduct(undefined);
    setWarehouse(undefined);
    setPage(1);
  }

  function openForm(item?: Inventory): void {
    createMutation.reset();
    updateMutation.reset();
    setEditing(item ?? null);
    setFormOpen(true);
  }

  function closeForm(): void {
    setFormOpen(false);
    setEditing(null);
    createMutation.reset();
    updateMutation.reset();
  }

  function closeDeleteModal(): void {
    setDeleting(null);
    deleteMutation.reset();
  }

  async function saveInventory(payload: InventoryRequest): Promise<void> {
    if (editing) {
      await updateMutation.mutateAsync({ id: editing.id, payload });
      showSuccess("Inventory record updated successfully.");
    } else {
      await createMutation.mutateAsync(payload);
      showSuccess("Inventory record created successfully.");
    }
    closeForm();
  }

  async function confirmDelete(): Promise<void> {
    if (!deleting) return;
    try {
      await deleteMutation.mutateAsync(deleting.id);
      setDeleting(null);
      showSuccess("Inventory record deleted.");
    } catch {
      // The mutation error remains visible in the confirmation modal.
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Stock control"
        title="Inventory levels"
        description="Inspect and manage quantity by product and warehouse. Filters are evaluated by the backend API."
        actions={
          <RoleGuard role={inventoryCreators}>
            <Button onClick={() => openForm()}>
              <Plus className="size-4" /> Add inventory
            </Button>
          </RoleGuard>
        }
      />

      <Card className="overflow-hidden" aria-busy={inventory.isPending}>
        <div className="grid gap-4 border-b border-slate-200 bg-slate-50/70 px-6 py-5 md:grid-cols-3">
          <div className="relative self-end">
            <Search className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
            <input
              dir="auto"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Search stock"
              aria-label="Search inventory"
              className="min-h-11 w-full rounded-xl border border-slate-300 bg-white pl-10 pr-4 text-sm shadow-sm transition-colors hover:border-slate-400 focus:border-brand-600 motion-reduce:transition-none"
            />
          </div>

          <Select
            label="Product"
            dir="auto"
            value={product ?? ""}
            onChange={(event) => {
              setProduct(event.target.value ? Number(event.target.value) : undefined);
              setPage(1);
            }}
          >
            <option value="">All products</option>
            {products.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} · {item.sku}
              </option>
            ))}
          </Select>

          <Select
            label="Warehouse"
            dir="auto"
            value={warehouse ?? ""}
            onChange={(event) => {
              setWarehouse(event.target.value ? Number(event.target.value) : undefined);
              setPage(1);
            }}
          >
            <option value="">All warehouses</option>
            {warehouses.data?.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </Select>
        </div>

        <BackgroundFetchIndicator active={inventory.isFetching && !inventory.isPending} label="Updating inventory" />

        {inventory.isPending ? (
          <Spinner label="Loading inventory" />
        ) : null}
        {inventory.isError ? (
          <div className="p-5">
            <ErrorMessage error={inventory.error} onRetry={() => void inventory.refetch()} />
          </div>
        ) : null}
        {inventory.data?.results.length === 0 ? (
          <EmptyState
            icon={Boxes}
            title="No inventory matches"
            description={
              hasFilters
                ? "Adjust the search, product, or warehouse filters."
                : canCreateInventory
                  ? "Add the first stock record to start tracking warehouse quantities."
                  : "No inventory records are currently configured."
            }
            action={
              hasFilters ? (
                <Button variant="outline" size="sm" onClick={clearFilters}>
                  Clear filters
                </Button>
              ) : canCreateInventory ? (
                <Button size="sm" onClick={() => openForm()}>
                  <Plus className="size-4" /> Add inventory
                </Button>
              ) : undefined
            }
          />
        ) : null}

        {inventory.data && inventory.data.results.length > 0 ? (
          <>
            <div className="table-scroll overflow-x-auto">
              <table className="w-full min-w-[820px] text-left">
                <thead className="border-y border-slate-200 bg-slate-100/80 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600">
                  <tr>
                    <th scope="col" className="px-6 py-4">Product</th>
                    <th scope="col" className="px-6 py-4">Warehouse</th>
                    <th scope="col" className="px-6 py-4 text-right">Quantity</th>
                    <th scope="col" className="px-6 py-4">Signal</th>
                    <th scope="col" className="px-6 py-4">Last updated</th>
                    <th scope="col" className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70">
                  {inventory.data.results.map((item) => {
                    const productRecord = productMap.get(item.product);
                    const warehouseRecord = warehouseMap.get(item.warehouse);

                    return (
                      <tr key={item.id} className="transition-colors hover:bg-brand-50/35 motion-reduce:transition-none">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <ProductImage src={productRecord?.image} size="sm" />
                            <div className="min-w-0">
                              <p dir="auto" className="font-semibold text-slate-900">
                                {productRecord?.name ?? `Product #${item.product}`}
                              </p>
                              <p className="mt-0.5 font-mono text-xs text-slate-500">
                                {productRecord?.sku ?? "Details unavailable"}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <p dir="auto" className="text-sm font-medium text-slate-800">
                            {warehouseRecord?.name ?? `Warehouse #${item.warehouse}`}
                          </p>
                          <p dir="auto" className="mt-0.5 text-xs text-slate-500">
                            {warehouseRecord?.location}
                          </p>
                        </td>
                        <td className="px-6 py-4 text-right text-xl font-bold tabular-nums text-slate-950">
                          {item.quantity.toLocaleString()}
                        </td>
                        <td className="px-6 py-4">
                          <Badge
                            tone={item.quantity === 0 ? "red" : item.quantity < 10 ? "amber" : "green"}
                          >
                            {item.quantity === 0
                              ? "Out of stock"
                              : item.quantity < 10
                                ? "Low stock"
                                : "In stock"}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-500">
                          {formatDate(item.updated_at)}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex justify-end gap-1">
                            <RoleGuard role={inventoryEditors}>
                              <button
                                type="button"
                                onClick={() => openForm(item)}
                                className="grid size-10 place-items-center rounded-lg text-slate-500 transition-colors hover:bg-brand-50 hover:text-brand-700 motion-reduce:transition-none"
                                aria-label={`Edit inventory for ${productRecord?.name ?? `product ${item.product}`}`}
                              >
                                <Pencil className="size-4" aria-hidden="true" />
                              </button>
                            </RoleGuard>
                            <RoleGuard role={ROLES.admin}>
                              <button
                                type="button"
                                onClick={() => setDeleting(item)}
                                className="grid size-10 place-items-center rounded-lg text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-700 motion-reduce:transition-none"
                                aria-label={`Delete inventory for ${productRecord?.name ?? `product ${item.product}`}`}
                              >
                                <Trash2 className="size-4" aria-hidden="true" />
                              </button>
                            </RoleGuard>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="border-t border-slate-200 bg-slate-50/50 px-6 py-4">
              <Pagination
                page={page}
                count={inventory.data.count}
                hasNext={Boolean(inventory.data.next)}
                hasPrevious={Boolean(inventory.data.previous)}
                onPageChange={setPage}
              />
            </div>
          </>
        ) : null}
      </Card>

      <Modal
        open={formOpen}
        onClose={closeForm}
        title={editing ? "Edit inventory" : "Add inventory"}
        description="Each product and warehouse combination can have one stock record."
      >
        <InventoryForm
          key={editing?.id ?? "new"}
          inventory={editing ?? undefined}
          onSubmit={saveInventory}
          onCancel={closeForm}
          isSubmitting={createMutation.isPending || updateMutation.isPending}
          serverError={createMutation.error ?? updateMutation.error}
        />
      </Modal>

      <Modal
        open={Boolean(deleting)}
        onClose={closeDeleteModal}
        title="Delete inventory"
        description="This removes the stock record from the warehouse."
        size="sm"
        isBusy={deleteMutation.isPending}
      >
        {deleteMutation.isError ? (
          <div className="mb-4">
            <ErrorMessage error={deleteMutation.error} />
          </div>
        ) : null}
        <p className="text-sm leading-6 text-slate-600">
          Delete inventory for{" "}
          <strong>
            {deleting
              ? productMap.get(deleting.product)?.name ?? `product #${deleting.product}`
              : ""}
          </strong>
          {deleting
            ? ` at ${warehouseMap.get(deleting.warehouse)?.name ?? `warehouse #${deleting.warehouse}`}`
            : ""}
          ?
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={closeDeleteModal} disabled={deleteMutation.isPending}>
            Cancel
          </Button>
          <Button
            data-modal-destructive="true"
            variant="danger"
            isLoading={deleteMutation.isPending}
            onClick={() => void confirmDelete()}
          >
            Delete inventory
          </Button>
        </div>
      </Modal>
    </>
  );
}
