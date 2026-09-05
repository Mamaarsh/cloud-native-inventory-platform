import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useAllProducts } from "@/hooks/useProducts";
import { useAllWarehouses } from "@/hooks/useWarehouses";
import type { Inventory, InventoryRequest } from "@/types";

interface InventoryFormProps {
  inventory?: Inventory;
  onSubmit: (payload: InventoryRequest) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
  serverError?: unknown;
}

type InventoryFormErrors = Partial<Record<keyof InventoryRequest, string>>;

interface InventoryFormValues {
  product: number;
  warehouse: number;
  quantity: number | "";
}

export function InventoryForm({
  inventory,
  onSubmit,
  onCancel,
  isSubmitting,
  serverError,
}: InventoryFormProps) {
  const [form, setForm] = useState<InventoryFormValues>({
    product: inventory?.product ?? 0,
    warehouse: inventory?.warehouse ?? 0,
    quantity: inventory?.quantity ?? 0,
  });
  const [errors, setErrors] = useState<InventoryFormErrors>({});
  const products = useAllProducts();
  const warehouses = useAllWarehouses();

  function validate(): boolean {
    const nextErrors: InventoryFormErrors = {};
    if (form.product <= 0) nextErrors.product = "Select a product.";
    if (form.warehouse <= 0) nextErrors.warehouse = "Select a warehouse.";
    if (form.quantity === "" || !Number.isInteger(form.quantity) || form.quantity < 0) {
      nextErrors.quantity = "Quantity must be a non-negative whole number.";
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!validate()) return;
    try {
      await onSubmit({ ...form, quantity: Number(form.quantity) });
    } catch {
      // TanStack Query exposes the server error through the mutation state below.
    }
  }

  if (products.isPending || warehouses.isPending) {
    return <p className="py-8 text-center text-sm text-slate-500">Loading products and warehouses…</p>;
  }

  if (products.isError || warehouses.isError) {
    return (
      <ErrorMessage
        error={products.error ?? warehouses.error}
        title="Inventory options could not be loaded"
      />
    );
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
      {serverError ? (
        <ErrorMessage error={serverError} title="Inventory could not be saved" />
      ) : null}

      <Select
        label="Product"
        value={form.product || ""}
        onChange={(event) => {
          setForm({ ...form, product: Number(event.target.value) });
          setErrors((current) => ({ ...current, product: undefined }));
        }}
        error={errors.product}
        disabled={isSubmitting}
        autoFocus
      >
        <option value="">Select a product</option>
        {products.data?.map((product) => (
          <option key={product.id} value={product.id}>
            {product.name} · {product.sku}
          </option>
        ))}
      </Select>

      <Select
        label="Warehouse"
        value={form.warehouse || ""}
        onChange={(event) => {
          setForm({ ...form, warehouse: Number(event.target.value) });
          setErrors((current) => ({ ...current, warehouse: undefined }));
        }}
        error={errors.warehouse}
        disabled={isSubmitting}
      >
        <option value="">Select a warehouse</option>
        {warehouses.data?.map((warehouse) => (
          <option key={warehouse.id} value={warehouse.id}>
            {warehouse.name} · {warehouse.location}
          </option>
        ))}
      </Select>

      <Input
        label="Quantity"
        type="number"
        min="0"
        step="1"
        inputMode="numeric"
        value={form.quantity}
        onChange={(event) => {
          setForm({
            ...form,
            quantity: event.target.value === "" ? "" : Number(event.target.value),
          });
          setErrors((current) => ({ ...current, quantity: undefined }));
        }}
        error={errors.quantity}
        hint="Enter the number of units currently available."
        disabled={isSubmitting}
        required
      />

      <div className="flex justify-end gap-3 border-t border-slate-200 pt-5">
        <Button variant="outline" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" isLoading={isSubmitting}>
          {inventory ? "Save changes" : "Add inventory"}
        </Button>
      </div>
    </form>
  );
}
