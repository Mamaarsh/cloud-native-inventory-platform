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

export interface UserRegistrationRequest {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  password_confirm: string;
}

export interface UserRegistrationResponse {
  detail: string;
}

export type AdminUserStatus = "pending" | "active";

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  groups: string[];
  date_joined: string;
  is_staff: boolean;
}

export interface AdminUserQueryParams {
  page?: number;
  status?: AdminUserStatus;
}

export interface AdminUserUpdateRequest {
  is_active?: boolean;
  role?: Role;
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
  image: string | null;
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

export enum InventoryMovementType {
  InitialStock = "initial_stock",
  ManualAdjustment = "manual_adjustment",
  OrderDeduction = "order_deduction",
}

export interface InventoryMovementActor {
  id: number;
  username: string;
}

export interface InventoryMovement {
  id: number;
  inventory: number;
  movement_type: InventoryMovementType;
  quantity_delta: number;
  quantity_before: number;
  quantity_after: number;
  reason: string;
  order_id: number | null;
  performed_by: InventoryMovementActor | null;
  created_at: string;
}

export interface InventoryAdjustmentRequest {
  quantity_delta: number;
  reason: string;
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
  image: string | null;
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

export interface OrderDetail extends Order {
  payment: Payment | null;
}

export interface OrderStatusHistoryActor {
  id: number;
  username: string;
}

export interface OrderStatusHistoryEntry {
  id: number;
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  performed_by: OrderStatusHistoryActor | null;
  created_at: string;
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
  image?: File;
  remove_image?: boolean;
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
