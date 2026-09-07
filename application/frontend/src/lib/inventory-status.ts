export const LOW_STOCK_THRESHOLD = 10;

export interface InventoryStatus {
  label: "Out of stock" | "Low stock" | "In stock";
  tone: "red" | "amber" | "green";
}

export function getInventoryStatus(quantity: number): InventoryStatus {
  if (quantity === 0) {
    return { label: "Out of stock", tone: "red" };
  }

  if (quantity < LOW_STOCK_THRESHOLD) {
    return { label: "Low stock", tone: "amber" };
  }

  return { label: "In stock", tone: "green" };
}

export function needsStockAttention(quantity: number): boolean {
  return quantity < LOW_STOCK_THRESHOLD;
}
