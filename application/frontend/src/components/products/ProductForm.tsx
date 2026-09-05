import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { getApiErrorMessage } from "@/lib/api-error";
import type { Product, ProductRequest } from "@/types";

interface ProductFormProps {
  product?: Product;
  onSubmit: (payload: ProductRequest) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
  serverError?: unknown;
}

export function ProductForm({ product, onSubmit, onCancel, isSubmitting, serverError }: ProductFormProps) {
  const [form, setForm] = useState<ProductRequest>({
    name: product?.name ?? "",
    sku: product?.sku ?? "",
    price: product?.price ?? "",
    is_active: product?.is_active ?? true,
  });
  const [errors, setErrors] = useState<Partial<Record<keyof ProductRequest, string>>>({});

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const nextErrors: Partial<Record<keyof ProductRequest, string>> = {};
    if (!form.name.trim()) nextErrors.name = "Product name is required.";
    if (!form.sku.trim()) nextErrors.sku = "SKU is required.";
    if (!form.price || Number(form.price) < 0) nextErrors.price = "Enter a valid non-negative price.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    await onSubmit({ ...form, name: form.name.trim(), sku: form.sku.trim() });
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
      {serverError ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700" role="alert">{getApiErrorMessage(serverError)}</p> : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Product name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} error={errors.name} autoFocus />
        <Input label="SKU" value={form.sku} onChange={(event) => setForm({ ...form, sku: event.target.value })} error={errors.sku} placeholder="SKU-001" />
      </div>
      <Input label="Unit price" type="number" min="0" step="0.01" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} error={errors.price} />
      <label className="flex items-center gap-3 rounded-xl border border-slate-200 p-4">
        <input type="checkbox" checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} className="size-4 accent-brand-600" />
        <span>
          <span className="block text-sm font-semibold text-slate-800">Active product</span>
          <span className="block text-xs text-slate-500">Only active products can be added to new orders.</span>
        </span>
      </label>
      <div className="flex justify-end gap-3 border-t border-slate-200 pt-5">
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit" isLoading={isSubmitting}>{product ? "Save changes" : "Create product"}</Button>
      </div>
    </form>
  );
}
