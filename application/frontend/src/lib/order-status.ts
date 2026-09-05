import { OrderStatus } from "@/types";

const transitions: Record<OrderStatus, OrderStatus[]> = {
  [OrderStatus.Pending]: [OrderStatus.Processing, OrderStatus.Cancelled],
  [OrderStatus.Processing]: [OrderStatus.Shipped, OrderStatus.Cancelled],
  [OrderStatus.Shipped]: [OrderStatus.Delivered],
  [OrderStatus.Delivered]: [],
  [OrderStatus.Cancelled]: [],
};

export function allowedStatusTransitions(
  current: OrderStatus,
  isAdmin: boolean,
  isWarehouseManager: boolean,
): OrderStatus[] {
  if (isAdmin) return transitions[current];
  if (!isWarehouseManager) return [];
  if (current === OrderStatus.Pending) return [OrderStatus.Processing];
  if (current === OrderStatus.Processing) return [OrderStatus.Shipped];
  return [];
}
