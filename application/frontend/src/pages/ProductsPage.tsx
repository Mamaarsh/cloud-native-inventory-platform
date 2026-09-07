import { useState } from "react";
import { PackageSearch, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
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
import { formatCurrency, formatDate } from "@/lib/format";
import { useCreateProduct, useDeleteProduct, useProducts, useUpdateProduct } from "@/hooks/useProducts";
import { useAuth } from "@/hooks/useAuth";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useSuccessFeedback } from "@/hooks/useSuccessFeedback";
import type { Product, ProductRequest } from "@/types";
import { ROLES } from "@/types";

function productPath(productId: number): string {
  return `/products/${productId}`;
}

function isInteractiveTarget(
  target: EventTarget | null,
  row: HTMLTableRowElement,
): boolean {
  if (!(target instanceof Element)) return false;
  const interactiveElement = target.closest(
    "a, button, input, select, textarea, [role='button'], [role='link']",
  );
  return interactiveElement !== null && interactiveElement !== row;
}

export function ProductsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Product | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState<Product | null>(null);
  const debouncedSearch = useDebouncedValue(search);
  const products = useProducts({ page, search: debouncedSearch || undefined, ordering: "name" });
  const createMutation = useCreateProduct();
  const updateMutation = useUpdateProduct();
  const deleteMutation = useDeleteProduct();
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const { showSuccess } = useSuccessFeedback();
  const canManageProducts = hasRole(ROLES.admin);

  function openProduct(productId: number): void {
    void navigate(productPath(productId));
  }

  function handleRowClick(
    event: React.MouseEvent<HTMLTableRowElement>,
    productId: number,
  ): void {
    if (!isInteractiveTarget(event.target, event.currentTarget)) {
      openProduct(productId);
    }
  }

  function handleRowKeyDown(
    event: React.KeyboardEvent<HTMLTableRowElement>,
    productId: number,
  ): void {
    if (event.key !== "Enter" || event.target !== event.currentTarget) return;
    event.preventDefault();
    openProduct(productId);
  }

  function closeForm(): void {
    setFormOpen(false);
    setEditing(null);
    createMutation.reset();
    updateMutation.reset();
  }

  async function saveProduct(payload: ProductRequest): Promise<void> {
    if (editing) {
      await updateMutation.mutateAsync({ id: editing.id, payload });
      showSuccess("Product updated successfully.");
    } else {
      await createMutation.mutateAsync(payload);
      showSuccess("Product created successfully.");
    }
    closeForm();
  }

  async function confirmDelete(): Promise<void> {
    if (!deleting) return;
    await deleteMutation.mutateAsync(deleting.id);
    setDeleting(null);
    showSuccess("Product deleted.");
  }

  return (
    <>
      <PageHeader
        eyebrow="Catalog"
        title="Product registry"
        description="Maintain the products that can be stocked and ordered across your warehouse network."
        actions={
          <RoleGuard role={ROLES.admin}>
            <Button onClick={() => setFormOpen(true)}><Plus className="size-4" /> Add product</Button>
          </RoleGuard>
        }
      />
      <Card className="overflow-hidden" aria-busy={products.isPending}>
        <div className="flex flex-col gap-4 border-b border-slate-200 bg-slate-50/70 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full max-w-md">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
            <input dir="auto" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search products or SKU" aria-label="Search products" className="min-h-11 w-full rounded-xl border border-slate-300 bg-white pl-10 pr-4 text-sm shadow-sm transition-colors hover:border-slate-400 focus:border-brand-600 motion-reduce:transition-none" />
          </div>
          <p className="w-fit rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 shadow-sm">{products.data?.count ?? 0} catalog items</p>
        </div>
        <BackgroundFetchIndicator active={products.isFetching && !products.isPending} label="Updating products" />
        {products.isPending ? <Spinner label="Loading products" /> : null}
        {products.isError ? <div className="p-5"><ErrorMessage error={products.error} onRetry={() => void products.refetch()} /></div> : null}
        {products.data && products.data.results.length === 0 ? (
          <EmptyState
            icon={PackageSearch}
            title="No products found"
            description={
              debouncedSearch
                ? "Try a different search term."
                : canManageProducts
                  ? "Create the first product to begin building your catalog."
                  : "No products are currently configured."
            }
            action={
              debouncedSearch ? (
                <Button variant="outline" size="sm" onClick={() => { setSearch(""); setPage(1); }}>
                  Clear search
                </Button>
              ) : canManageProducts ? (
                <Button size="sm" onClick={() => { setEditing(null); setFormOpen(true); }}>
                  <Plus className="size-4" /> Add product
                </Button>
              ) : undefined
            }
          />
        ) : null}
        {products.data && products.data.results.length > 0 ? (
          <>
            <div className="table-scroll overflow-x-auto">
              <table className="w-full min-w-[760px] text-left">
                <thead className="border-y border-slate-200 bg-slate-100/80 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600">
                  <tr><th scope="col" className="px-6 py-4">Product</th><th scope="col" className="px-6 py-4">SKU</th><th scope="col" className="px-6 py-4 text-right">Price</th><th scope="col" className="px-6 py-4">Status</th><th scope="col" className="px-6 py-4">Updated</th><th scope="col" className="px-6 py-4 text-right">Actions</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70">
                  {products.data.results.map((product) => (
                    <tr
                      key={product.id}
                      role="link"
                      tabIndex={0}
                      aria-label={`Open ${product.name}`}
                      onClick={(event) => handleRowClick(event, product.id)}
                      onKeyDown={(event) => handleRowKeyDown(event, product.id)}
                      className="cursor-pointer transition-colors hover:bg-brand-50/35 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand-500/60 motion-reduce:transition-none"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <ProductImage src={product.image} size="sm" />
                          <div className="min-w-0">
                            <Link
                              to={productPath(product.id)}
                              dir="auto"
                              className="font-semibold text-slate-900 hover:text-brand-700"
                            >
                              {product.name}
                            </Link>
                            <p className="mt-0.5 text-xs text-slate-500">ID {product.id}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 font-mono text-sm text-slate-600">{product.sku}</td>
                      <td className="px-6 py-4 text-right text-sm font-semibold tabular-nums text-slate-800">{formatCurrency(product.price)}</td>
                      <td className="px-6 py-4"><Badge tone={product.is_active ? "green" : "slate"}>{product.is_active ? "Active" : "Inactive"}</Badge></td>
                      <td className="px-6 py-4 text-sm text-slate-500">{formatDate(product.updated_at)}</td>
                      <td className="px-6 py-4">
                        <RoleGuard role={ROLES.admin}>
                          <div className="flex justify-end gap-1">
                            <button type="button" onClick={() => { setEditing(product); setFormOpen(true); }} className="grid size-10 place-items-center rounded-lg text-slate-500 hover:bg-brand-50 hover:text-brand-700" aria-label={`Edit ${product.name}`}><Pencil className="size-4" aria-hidden="true" /></button>
                            <button type="button" onClick={() => setDeleting(product)} className="grid size-10 place-items-center rounded-lg text-slate-500 hover:bg-rose-50 hover:text-rose-700" aria-label={`Delete ${product.name}`}><Trash2 className="size-4" aria-hidden="true" /></button>
                          </div>
                        </RoleGuard>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="border-t border-slate-200 bg-slate-50/50 px-6 py-4"><Pagination page={page} count={products.data.count} hasNext={Boolean(products.data.next)} hasPrevious={Boolean(products.data.previous)} onPageChange={setPage} /></div>
          </>
        ) : null}
      </Card>

      <Modal open={formOpen} onClose={closeForm} title={editing ? "Edit product" : "Create product"} description="Catalog fields are validated again by the backend.">
        <ProductForm key={editing?.id ?? "new"} product={editing ?? undefined} onSubmit={saveProduct} onCancel={closeForm} isSubmitting={createMutation.isPending || updateMutation.isPending} serverError={createMutation.error ?? updateMutation.error} />
      </Modal>
      <Modal open={Boolean(deleting)} onClose={() => { setDeleting(null); deleteMutation.reset(); }} title="Delete product" description="This action cannot be undone." size="sm" isBusy={deleteMutation.isPending}>
        {deleteMutation.isError ? <div className="mb-4"><ErrorMessage error={deleteMutation.error} /></div> : null}
        <p className="text-sm leading-6 text-slate-600">Delete <strong>{deleting?.name}</strong>? Products referenced by orders may be protected by the backend.</p>
        <div className="mt-6 flex justify-end gap-3"><Button variant="outline" disabled={deleteMutation.isPending} onClick={() => setDeleting(null)}>Cancel</Button><Button data-modal-destructive="true" variant="danger" isLoading={deleteMutation.isPending} onClick={() => void confirmDelete()}>Delete product</Button></div>
      </Modal>
    </>
  );
}
