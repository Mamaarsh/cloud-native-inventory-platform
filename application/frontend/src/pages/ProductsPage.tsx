import { useState } from "react";
import { PackageSearch, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { RoleGuard } from "@/auth/RoleGuard";
import { ProductForm } from "@/components/products/ProductForm";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { formatCurrency, formatDate } from "@/lib/format";
import { useCreateProduct, useDeleteProduct, useProducts, useUpdateProduct } from "@/hooks/useProducts";
import type { Product, ProductRequest } from "@/types";
import { ROLES } from "@/types";

export function ProductsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Product | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState<Product | null>(null);
  const products = useProducts({ page, search: search || undefined, ordering: "name" });
  const createMutation = useCreateProduct();
  const updateMutation = useUpdateProduct();
  const deleteMutation = useDeleteProduct();

  function closeForm(): void {
    setFormOpen(false);
    setEditing(null);
    createMutation.reset();
    updateMutation.reset();
  }

  async function saveProduct(payload: ProductRequest): Promise<void> {
    if (editing) await updateMutation.mutateAsync({ id: editing.id, payload });
    else await createMutation.mutateAsync(payload);
    closeForm();
  }

  async function confirmDelete(): Promise<void> {
    if (!deleting) return;
    await deleteMutation.mutateAsync(deleting.id);
    setDeleting(null);
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
      <Card>
        <div className="flex flex-col gap-4 border-b border-slate-200 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full max-w-md">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
            <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search products or SKU" aria-label="Search products" className="min-h-11 w-full rounded-xl border border-slate-300 bg-white pl-10 pr-4 text-sm" />
          </div>
          <p className="text-sm text-slate-500">{products.data?.count ?? 0} catalog items</p>
        </div>
        {products.isPending ? <div className="p-8"><span className="text-sm text-slate-500">Loading products…</span></div> : null}
        {products.isError ? <div className="p-5"><ErrorMessage error={products.error} onRetry={() => void products.refetch()} /></div> : null}
        {products.data && products.data.results.length === 0 ? <EmptyState icon={PackageSearch} title="No products found" description={search ? "Try a different search term." : "Create the first product to begin building your catalog."} /> : null}
        {products.data && products.data.results.length > 0 ? (
          <>
            <div className="table-scroll overflow-x-auto">
              <table className="w-full min-w-[760px] text-left">
                <thead className="bg-slate-50/80 text-xs font-bold uppercase tracking-wider text-slate-500">
                  <tr><th className="px-6 py-4">Product</th><th className="px-6 py-4">SKU</th><th className="px-6 py-4">Price</th><th className="px-6 py-4">Status</th><th className="px-6 py-4">Updated</th><th className="px-6 py-4 text-right">Actions</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {products.data.results.map((product) => (
                    <tr key={product.id} className="hover:bg-slate-50/70">
                      <td className="px-6 py-4"><p className="font-semibold text-slate-900">{product.name}</p><p className="mt-0.5 text-xs text-slate-400">ID {product.id}</p></td>
                      <td className="px-6 py-4 font-mono text-sm text-slate-600">{product.sku}</td>
                      <td className="px-6 py-4 text-sm font-semibold text-slate-800">{formatCurrency(product.price)}</td>
                      <td className="px-6 py-4"><Badge tone={product.is_active ? "green" : "slate"}>{product.is_active ? "Active" : "Inactive"}</Badge></td>
                      <td className="px-6 py-4 text-sm text-slate-500">{formatDate(product.updated_at)}</td>
                      <td className="px-6 py-4">
                        <RoleGuard role={ROLES.admin}>
                          <div className="flex justify-end gap-1">
                            <button type="button" onClick={() => { setEditing(product); setFormOpen(true); }} className="rounded-lg p-2 text-slate-500 hover:bg-brand-50 hover:text-brand-700" aria-label={`Edit ${product.name}`}><Pencil className="size-4" /></button>
                            <button type="button" onClick={() => setDeleting(product)} className="rounded-lg p-2 text-slate-500 hover:bg-rose-50 hover:text-rose-700" aria-label={`Delete ${product.name}`}><Trash2 className="size-4" /></button>
                          </div>
                        </RoleGuard>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="border-t border-slate-200 p-5"><Pagination page={page} count={products.data.count} hasNext={Boolean(products.data.next)} hasPrevious={Boolean(products.data.previous)} onPageChange={setPage} /></div>
          </>
        ) : null}
      </Card>

      <Modal open={formOpen} onClose={closeForm} title={editing ? "Edit product" : "Create product"} description="Catalog fields are validated again by the backend.">
        <ProductForm key={editing?.id ?? "new"} product={editing ?? undefined} onSubmit={saveProduct} onCancel={closeForm} isSubmitting={createMutation.isPending || updateMutation.isPending} serverError={createMutation.error ?? updateMutation.error} />
      </Modal>
      <Modal open={Boolean(deleting)} onClose={() => { setDeleting(null); deleteMutation.reset(); }} title="Delete product" description="This action cannot be undone." size="sm">
        {deleteMutation.isError ? <div className="mb-4"><ErrorMessage error={deleteMutation.error} /></div> : null}
        <p className="text-sm leading-6 text-slate-600">Delete <strong>{deleting?.name}</strong>? Products referenced by orders may be protected by the backend.</p>
        <div className="mt-6 flex justify-end gap-3"><Button variant="outline" onClick={() => setDeleting(null)}>Cancel</Button><Button variant="danger" isLoading={deleteMutation.isPending} onClick={() => void confirmDelete()}>Delete product</Button></div>
      </Modal>
    </>
  );
}
