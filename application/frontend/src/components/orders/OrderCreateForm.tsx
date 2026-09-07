import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { ProductImage } from "@/components/products/ProductImage";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { useAllProducts } from "@/hooks/useProducts";
import { useAllWarehouses } from "@/hooks/useWarehouses";
import type { OrderCreateRequest, OrderItemCreateRequest } from "@/types";

interface OrderCreateFormProps {
  onSubmit: (payload: OrderCreateRequest) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
  serverError?: unknown;
}

interface OrderItemFormValue extends Omit<OrderItemCreateRequest, "quantity"> {
  quantity: string;
}

const emptyItem = (): OrderItemFormValue => ({
  product: 0,
  warehouse: 0,
  quantity: "",
});

function isValidQuantity(value: string): boolean {
  if (!value.trim()) return false;
  const quantity = Number(value);
  return Number.isInteger(quantity) && quantity >= 1;
}

export function OrderCreateForm({ onSubmit, onCancel, isSubmitting, serverError }: OrderCreateFormProps) {
  const [items, setItems] = useState<OrderItemFormValue[]>([emptyItem()]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const products = useAllProducts();
  const warehouses = useAllWarehouses();
  const activeProducts = products.data?.filter((product) => product.is_active) ?? [];

  function updateItem(index: number, patch: Partial<OrderItemFormValue>): void {
    setItems((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (items.some((item) => (
      item.product <= 0
      || item.warehouse <= 0
      || !isValidQuantity(item.quantity)
    ))) {
      setValidationError("Choose a product and warehouse and enter a quantity greater than zero for every item.");
      return;
    }
    const itemKeys = items.map((item) => `${item.product}:${item.warehouse}`);
    if (new Set(itemKeys).size !== itemKeys.length) {
      setValidationError("Each product and warehouse combination can appear only once.");
      return;
    }
    setValidationError(null);
    await onSubmit({
      items: items.map((item) => ({
        ...item,
        quantity: Number(item.quantity),
      })),
    });
  }

  if (products.isPending || warehouses.isPending) {
    return <Spinner label="Loading order options" />;
  }

  if (products.isError || warehouses.isError) {
    return <ErrorMessage error={products.error ?? warehouses.error} title="Order options could not be loaded" />;
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
      {validationError ? <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800" role="alert">{validationError}</p> : null}
      {serverError ? <ErrorMessage error={serverError} title="Order could not be created" /> : null}
      <div className="space-y-4">
        {items.map((item, index) => {
          const selectedProduct = activeProducts.find(
            (product) => product.id === item.product,
          );

          return (
            <div key={index} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5 shadow-[0_1px_2px_rgb(15_23_42/0.03)]">
              <div className="mb-4 flex items-center justify-between"><p className="text-sm font-bold text-slate-800">Item {index + 1}</p>{items.length > 1 ? <button type="button" onClick={() => setItems((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="grid size-10 place-items-center rounded-lg text-slate-500 hover:bg-rose-50 hover:text-rose-700" aria-label={`Remove item ${index + 1}`}><Trash2 className="size-4" aria-hidden="true" /></button> : null}</div>
              <div className="grid gap-4 md:grid-cols-[1.3fr_1.3fr_0.6fr]">
                <div>
                  <Select label="Product" dir="auto" value={item.product || ""} onChange={(event) => updateItem(index, { product: Number(event.target.value) })} required><option value="">Choose product</option>{activeProducts.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}</Select>
                  {selectedProduct ? (
                    <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                      <ProductImage src={selectedProduct.image} size="sm" />
                      <span dir="auto" className="truncate">{selectedProduct.name}</span>
                    </div>
                  ) : null}
                </div>
                <Select label="Warehouse" dir="auto" value={item.warehouse || ""} onChange={(event) => updateItem(index, { warehouse: Number(event.target.value) })} required><option value="">Choose warehouse</option>{warehouses.data?.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.name}</option>)}</Select>
                <Input label="Quantity" type="number" min="1" step="1" inputMode="numeric" value={item.quantity} onChange={(event) => updateItem(index, { quantity: event.target.value })} required />
              </div>
            </div>
          );
        })}
      </div>
      <Button variant="outline" size="sm" onClick={() => setItems((current) => [...current, emptyItem()])}><Plus className="size-4" /> Add item</Button>
      <div className="flex justify-end gap-3 border-t border-slate-200 pt-5"><Button variant="outline" onClick={onCancel}>Cancel</Button><Button type="submit" isLoading={isSubmitting}>Create order</Button></div>
    </form>
  );
}
