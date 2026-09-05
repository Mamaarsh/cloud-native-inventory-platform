export const ROLES = {
  admin: "Admin",
  warehouseManager: "Warehouse Manager",
  operator: "Operator",
  auditor: "Auditor",
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

export interface User {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  groups: string[];
  is_staff: boolean;
}

export interface UserProfileUpdateRequest {
  first_name: string;
  last_name: string;
  email: string;
}

export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}

export interface PasswordChangeResponse {
  detail: string;
}

export interface OrderUser {
  id: number;
  username: string;
  email: string;
}

export interface Product {
  id: number;
  name: string;
  sku: string;
  price: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Warehouse {
  id: number;
  name: string;
  location: string;
  created_at: string;
}

export interface Inventory {
  id: number;
  product: number;
  warehouse: number;
  quantity: number;
  updated_at: string;
}

export enum OrderStatus {
  Pending = "pending",
  Processing = "processing",
  Shipped = "shipped",
  Delivered = "delivered",
  Cancelled = "cancelled",
}

export interface OrderItemProduct {
  id: number;
  name: string;
  sku: string;
}

export interface OrderItemWarehouse {
  id: number;
  name: string;
  location: string;
}

export interface OrderItem {
  id: number;
  product: OrderItemProduct;
  warehouse: OrderItemWarehouse;
  quantity: number;
  unit_price: string;
}

export interface Order {
  id: number;
  user: OrderUser;
  status: OrderStatus;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

export enum PaymentStatus {
  Pending = "pending",
  Succeeded = "succeeded",
  Failed = "failed",
  Refunded = "refunded",
}

export interface Payment {
  id: number;
  order: number;
  amount: string;
  status: PaymentStatus;
  provider: string;
  provider_reference: string | null;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: number;
  user: number;
  order: number;
  event_type: string;
  channel: string;
  status: string;
  message: string;
  idempotency_key: string;
  provider_reference: string | null;
  attempts: number;
  last_error: string;
  created_at: string;
  updated_at: string;
  sent_at: string | null;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface PageParams {
  page?: number;
  search?: string;
  ordering?: string;
}

export interface ProductQueryParams extends PageParams {
  sku?: string;
}

export interface WarehouseQueryParams extends PageParams {
  location?: string;
}

export interface InventoryQueryParams extends PageParams {
  product?: number;
  warehouse?: number;
}

export interface OrderQueryParams extends PageParams {
  status?: OrderStatus | "";
  user?: number;
}

export interface ProductRequest {
  name: string;
  sku: string;
  price: string;
  is_active: boolean;
}

export interface WarehouseRequest {
  name: string;
  location: string;
}

export interface InventoryRequest {
  product: number;
  warehouse: number;
  quantity: number;
}

export interface OrderItemCreateRequest {
  product: number;
  warehouse: number;
  quantity: number;
}

export interface OrderCreateRequest {
  items: OrderItemCreateRequest[];
}

export interface OrderStatusRequest {
  status: OrderStatus;
}

export interface TokenRequest {
  username: string;
  password: string;
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface TokenRefreshResponse {
  access: string;
}
