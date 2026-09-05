import { useState } from "react";
import { MapPin, Pencil, Plus, Search, Trash2, Warehouse as WarehouseIcon } from "lucide-react";
import { RoleGuard } from "@/auth/RoleGuard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { useCreateWarehouse, useDeleteWarehouse, useUpdateWarehouse, useWarehouses } from "@/hooks/useWarehouses";
import { getApiErrorMessage } from "@/lib/api-error";
import { formatDate } from "@/lib/format";
import type { Warehouse, WarehouseRequest } from "@/types";
import { ROLES } from "@/types";

export function WarehousesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Warehouse | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState<Warehouse | null>(null);
  const [form, setForm] = useState<WarehouseRequest>({ name: "", location: "" });
  const warehouses = useWarehouses({ page, search: search || undefined, ordering: "name" });
  const createMutation = useCreateWarehouse();
  const updateMutation = useUpdateWarehouse();
  const deleteMutation = useDeleteWarehouse();

  function openForm(warehouse?: Warehouse): void {
    setEditing(warehouse ?? null);
    setForm({ name: warehouse?.name ?? "", location: warehouse?.location ?? "" });
    setFormOpen(true);
  }

  function closeForm(): void {
    setFormOpen(false);
    setEditing(null);
    createMutation.reset();
    updateMutation.reset();
  }

  async function saveWarehouse(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!form.name.trim() || !form.location.trim()) return;
    if (editing) await updateMutation.mutateAsync({ id: editing.id, payload: form });
    else await createMutation.mutateAsync(form);
    closeForm();
  }

  async function confirmDelete(): Promise<void> {
    if (!deleting) return;
    await deleteMutation.mutateAsync(deleting.id);
    setDeleting(null);
  }

  const formError = createMutation.error ?? updateMutation.error;

  return (
    <>
      <PageHeader eyebrow="Network" title="Warehouse locations" description="View the physical locations that hold available inventory." actions={<RoleGuard role={ROLES.admin}><Button onClick={() => openForm()}><Plus className="size-4" /> Add warehouse</Button></RoleGuard>} />
      <Card>
        <div className="flex flex-col gap-4 border-b border-slate-200 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full max-w-md"><Search className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Search name or location" aria-label="Search warehouses" className="min-h-11 w-full rounded-xl border border-slate-300 pl-10 pr-4 text-sm" /></div>
          <p className="text-sm text-slate-500">{warehouses.data?.count ?? 0} locations</p>
        </div>
        {warehouses.isPending ? <div className="p-8 text-sm text-slate-500">Loading warehouses…</div> : null}
        {warehouses.isError ? <div className="p-5"><ErrorMessage error={warehouses.error} onRetry={() => void warehouses.refetch()} /></div> : null}
        {warehouses.data?.results.length === 0 ? <EmptyState icon={WarehouseIcon} title="No warehouses found" description={search ? "Try a broader search." : "No warehouse locations have been configured."} /> : null}
        {warehouses.data && warehouses.data.results.length > 0 ? (
          <>
            <div className="grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-3">
              {warehouses.data.results.map((warehouse) => (
                <div key={warehouse.id} className="rounded-2xl border border-slate-200 p-5 transition hover:border-brand-200 hover:shadow-sm">
                  <div className="flex items-start justify-between gap-3"><span className="grid size-11 place-items-center rounded-xl bg-brand-50 text-brand-700"><WarehouseIcon className="size-5" /></span><RoleGuard role={ROLES.admin}><div className="flex gap-1"><button type="button" onClick={() => openForm(warehouse)} className="rounded-lg p-2 text-slate-400 hover:bg-brand-50 hover:text-brand-700" aria-label={`Edit ${warehouse.name}`}><Pencil className="size-4" /></button><button type="button" onClick={() => setDeleting(warehouse)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700" aria-label={`Delete ${warehouse.name}`}><Trash2 className="size-4" /></button></div></RoleGuard></div>
                  <h3 className="mt-4 font-bold text-slate-900">{warehouse.name}</h3>
                  <p className="mt-2 flex items-center gap-2 text-sm text-slate-500"><MapPin className="size-4" />{warehouse.location}</p>
                  <p className="mt-4 text-xs text-slate-400">Added {formatDate(warehouse.created_at)}</p>
                </div>
              ))}
            </div>
            <div className="border-t border-slate-200 p-5"><Pagination page={page} count={warehouses.data.count} hasNext={Boolean(warehouses.data.next)} hasPrevious={Boolean(warehouses.data.previous)} onPageChange={setPage} /></div>
          </>
        ) : null}
      </Card>

      <Modal open={formOpen} onClose={closeForm} title={editing ? "Edit warehouse" : "Create warehouse"} description="Only Admin can modify warehouse records.">
        <form onSubmit={(event) => void saveWarehouse(event)} className="space-y-5">
          {formError ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{getApiErrorMessage(formError)}</p> : null}
          <Input label="Warehouse name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required autoFocus />
          <Input label="Location" value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} required />
          <div className="flex justify-end gap-3 border-t border-slate-200 pt-5"><Button variant="outline" onClick={closeForm}>Cancel</Button><Button type="submit" isLoading={createMutation.isPending || updateMutation.isPending}>{editing ? "Save changes" : "Create warehouse"}</Button></div>
        </form>
      </Modal>
      <Modal open={Boolean(deleting)} onClose={() => { setDeleting(null); deleteMutation.reset(); }} title="Delete warehouse" description="Inventory relationships may prevent deletion." size="sm">
        {deleteMutation.isError ? <div className="mb-4"><ErrorMessage error={deleteMutation.error} /></div> : null}
        <p className="text-sm text-slate-600">Are you sure you want to delete <strong>{deleting?.name}</strong>?</p>
        <div className="mt-6 flex justify-end gap-3"><Button variant="outline" onClick={() => setDeleting(null)}>Cancel</Button><Button variant="danger" isLoading={deleteMutation.isPending} onClick={() => void confirmDelete()}>Delete warehouse</Button></div>
      </Modal>
    </>
  );
}
