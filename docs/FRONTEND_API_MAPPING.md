# Frontend–API Mapping

This document maps the implemented React UI to the authoritative Django REST Framework contracts. It is a source-level integration reference, not a replacement for the generated [OpenAPI schema](api.md#openapi-documentation).

## Shared conventions

| Concern | Frontend implementation | Backend behavior |
|---|---|---|
| API root | `VITE_API_URL`, normally `/api` | Auth under `/api/auth/`; domain API under `/api/v1/` |
| HTTP client | `src/api/client.ts` Axios instance | JSON by default; multipart accepted for product images |
| Authentication | `AuthProvider`, `token-storage`, request/response interceptors | SimpleJWT access/refresh tokens |
| Server state | Hooks in `src/hooks/` using TanStack Query | Paginated DRF list responses, normally 10/page |
| Roles | `ProtectedRoute`, `RoleProtectedRoute`, `RoleGuard` | DRF permission classes are authoritative |
| Errors | `src/lib/api-error.ts` | Field errors and safe `detail` JSON responses |
| Media | `ProductImage` + `src/lib/media-url.ts` | Product `image` is a media URL or `null` |

The client retries one eligible `401` after refreshing the access token. If refresh fails, it clears the local session and redirects to `/login`. Tokens are stored in `localStorage`; client logout does not revoke issued JWTs on the server.

List pages debounce search by approximately 300 ms, preserve previous query data during background refetches, and use DRF `count`, `next`, `previous`, and `results`.

## Public authentication

| Frontend | Client function | Backend path | Contract |
|---|---|---|---|
| `LoginPage` (`/login`) | `requestTokens` | `POST /api/auth/token/` | `{username,password}` → `{access,refresh}`; inactive/invalid accounts receive `401` |
| Automatic refresh | Axios refresh client | `POST /api/auth/token/refresh/` | `{refresh}` → `{access}` |
| `RegisterPage` (`/register`) | `registerUser` | `POST /api/auth/register/` | Safe registration fields → `201` detail; no tokens |

Registration sends only `username`, `email`, `first_name`, `last_name`, `password`, and `password_confirm`. The backend validates the password, rejects protected role/privilege fields, creates the user inactive, and assigns no group. The success page explains that Admin approval is required.

Persian/Unicode first and last names are sent unchanged. Password fields use appropriate autocomplete attributes and are never persisted as application state beyond the form lifetime.

## Account and session

| Frontend | Client function | Backend path | Contract |
|---|---|---|---|
| `AuthProvider`, Header, Account menu | `getCurrentUser` | `GET /api/auth/me/` | `User`: username, email, names, groups, staff flag |
| `AccountPage` profile form | `updateCurrentUserProfile` | `PATCH /api/auth/me/` | Sends only email, first name, and last name; returns updated `User` |
| `AccountPage` password form | `changeCurrentUserPassword` | `POST /api/auth/change-password/` | Current/new/confirmation → success detail |

After profile update, the Auth provider updates the shared current-user value so the page and account menu synchronize without a reload. After password success, the UI clears local tokens through the existing logout mechanism and returns to login. Already-issued JWTs remain valid server-side until expiry.

## Dashboard

`DashboardPage` composes existing list APIs rather than calling a separate dashboard endpoint:

- all Products and Warehouses are fetched across pages for accurate catalog/location totals and label lookup;
- page 1 of Inventory ordered by quantity drives the loaded stock-attention sample;
- page 1 of Orders ordered newest-first drives recent orders;
- page 1 filtered to `status=pending` supplies the pending count.

The page does not claim the loaded Inventory sample is a global quantity total. Images use data already returned by Product or nested Order responses; there are no image-specific API calls.

## Products

Frontend files: `ProductsPage`, `ProductDetailPage`, `ProductForm`, `ProductImage`, `useProducts`, and `products-api.ts`.

| UI operation | Method and path | Request/response | Permission |
|---|---|---|---|
| List/search/filter | `GET /api/v1/products/` | Paginated `Product[]`; `search`, `sku`, `ordering`, `page` | Any authenticated user |
| Detail | `GET /api/v1/products/{id}/` | `Product` | Any authenticated user |
| Create | `POST /api/v1/products/` | Product fields; multipart only when a file is present | Admin |
| Edit/activate/deactivate | `PATCH /api/v1/products/{id}/` | Changed fields; optional image or `remove_image=true` | Admin |
| Delete | `DELETE /api/v1/products/{id}/` | `204` or safe `409` detail | Admin |

`Product` includes `image: string | null`. `ProductImage` resolves allowed product media paths against the configured backend origin, keeps null/broken-image fallbacks, and renders consistent sizes. Product forms preview selected files and accept only JPEG/PNG/WebP up to 5 MiB before submission; Django repeats authoritative content/size validation.

The frontend does not manually set multipart `Content-Type`, allowing the browser to add its boundary. Image removal is sent only after an explicit user action. A `409` protected-deletion message remains visible in the busy-safe confirmation modal and advises deactivation; HTML/non-JSON errors are replaced by safe generic text.

## Warehouses

Frontend files: `WarehousesPage`, `useWarehouses`, and `warehouses-api.ts`.

| UI operation | Method and path | Request/response | Permission |
|---|---|---|---|
| List/search/filter | `GET /api/v1/warehouses/` | Paginated `Warehouse[]`; `search`, `location`, `ordering`, `page` | All application roles |
| Create | `POST /api/v1/warehouses/` | `{name,location}` → `Warehouse` | Admin |
| Edit | `PATCH /api/v1/warehouses/{id}/` | Changed fields → `Warehouse` | Admin |
| Delete | `DELETE /api/v1/warehouses/{id}/` | `204` or safe `409` detail | Admin |

Admin mutation controls are hidden from read-only roles. Referenced warehouses cannot be deleted; the modal surfaces the backend detail safely and remains open on failure.

## Inventory

Frontend files: `InventoryPage`, `InventoryForm`, `InventoryAdjustmentForm`, `InventoryMovementHistory`, `useInventory`, and `inventory-api.ts`.

| UI operation | Method and path | Request/response | Permission |
|---|---|---|---|
| List/search/filter | `GET /api/v1/inventory/` | Paginated records; product/warehouse/search/ordering/page | All application roles |
| Create | `POST /api/v1/inventory/` | `{product,warehouse,quantity}` → Inventory | Admin, Warehouse Manager, Operator |
| Generic update | `PATCH /api/v1/inventory/{id}/` | Identity/quantity changes rejected | Admin, Warehouse Manager at permission layer |
| Delete | `DELETE /api/v1/inventory/{id}/` | `204`; movement history prevents deletion | Admin |
| Adjust | `POST /api/v1/inventory/{id}/adjust/` | `{quantity_delta,reason}` → movement (`201`) | Admin, Warehouse Manager |
| History | `GET /api/v1/inventory/{id}/movements/` | Paginated newest-first movements | All application roles |

The create form can provide initial quantity; the backend creates the record at zero and applies initial stock through the movement service. Subsequent stock changes use only the adjustment form. Product/warehouse labels and images are resolved from existing product/warehouse queries because Inventory carries their IDs.

Adjustment results expose `quantity_delta`, `quantity_before`, `quantity_after`, reason, movement type, optional `order_id`, performer, and timestamp. The UI invalidates Inventory and movement queries after success. The backend locks the row and rejects negative resulting stock.

## Orders

Frontend files: `OrdersPage`, `OrderCreateForm`, `OrderDetailPage`, `OrderStatusTimeline`, `useOrders`, and `orders-api.ts`.

| UI operation | Method and path | Request/response | Permission |
|---|---|---|---|
| List/search/filter | `GET /api/v1/orders/` | Paginated nested Orders; status/user/search/ordering/page | All application roles |
| Create | `POST /api/v1/orders/` | `{items:[{product,warehouse,quantity}]}` → Order | Admin |
| Detail | `GET /api/v1/orders/{id}/` | `OrderDetail`, including `payment` object or `null` | All application roles |
| Change status | `POST /api/v1/orders/{id}/change-status/` | `{status}` → updated Order | Admin; limited Warehouse Manager transitions |
| Status timeline | `GET /api/v1/orders/{id}/history/` | Complete chronological history array | All application roles |
| Pay | `POST /api/v1/orders/{id}/pay/` | `{}` → Payment (`201` or idempotent `200`) | Admin |

Order list rows remain fully mouse/keyboard navigable while nested interactive controls stop row navigation. List/detail item models include nested product `id`, `name`, `sku`, `image`; nested warehouse `id`, `name`, `location`; `quantity`; and historical `unit_price`. The detail page calculates line subtotals and total from snapshots and displays larger product images.

Create never sends a user or status. The backend assigns the authenticated owner, starts pending, validates active products/positive quantities, locks/deducts stock, snapshots prices, and rolls back on failure.

Status actions are derived from the known state machine and current role. The clicked transition alone shows a spinner while other actions are disabled. Admin may make any valid transition; Warehouse Manager may move pending to processing or processing to shipped; Operator and Auditor receive no transition controls. Backend validation remains authoritative.

Payment data is present only on `OrderDetail`, not assumed on list/create responses. The Admin-only action sends an empty object; payment amount and provider fields are server-controlled. A successful pending payment advances status through the backend transition service, so related order/history queries are refreshed.

## Admin users

Frontend files: `UsersPage`, `UserAccessForm`, `useAdminUsers`, and `admin-users-api.ts`. Route `/users` is guarded for the application Admin role.

| UI operation | Method and path | Contract |
|---|---|---|
| List/filter | `GET /api/auth/admin/users/` | Paginated accounts; `status=pending|active`, page |
| Inspect | `GET /api/auth/admin/users/{id}/` | Full safe Admin user response |
| Approve/deactivate/role | `PATCH /api/auth/admin/users/{id}/` | Sends only `is_active` and/or one application `role` |

The UI does not expose staff, superuser, permission, or arbitrary-group controls. The backend blocks superuser management, self-deactivation, and removal of the requesting Admin's own Admin role.

## Audit log

Frontend files: `AuditLogPage`, `useAuditLogs`, and `audit-logs-api.ts`. Route `/audit-log` is visible only to Admin and Auditor.

| UI operation | Method and path | Contract |
|---|---|---|
| List/filter/search | `GET /api/v1/audit-logs/` | Paginated read-only entries; action, target type, actor, search, ordering, page |

Each entry includes actor or `null`, action, target type/ID, target-label snapshot, validated metadata, and time. No create/edit/delete client exists. Metadata is rendered defensively and backend access is read-only.

## Health, schema, and notifications

The current SPA does not poll health endpoints or claim live connectivity. Operational endpoints remain available to infrastructure:

- `/api/health/live/`
- `/api/health/ready/`
- `/api/health/dependencies/`
- `/api/schema/`, `/api/docs/`, and `/api/redoc/`

There is no public Notification API and no frontend notification inbox. The backend model/service/task exists, but the current Compose runtime has no Celery worker; the UI does not claim asynchronous delivery.

## Permission-aware presentation

| Frontend capability | Admin | Warehouse Manager | Operator | Auditor |
|---|---|---|---|---|
| View main domain pages | Yes | Yes | Yes | Yes |
| Product/warehouse mutation controls | Yes | No | No | No |
| Create Inventory | Yes | Yes | Yes | No |
| Adjust Inventory | Yes | Yes | No | No |
| Create/pay Order | Yes | No | No | No |
| Change Order status | All valid | Processing/shipping transitions | No | No |
| Users route | Yes | No | No | No |
| Audit Log route | Yes | No | No | Yes |

This matrix describes presentation and navigation. Every request is independently authorized by backend permission classes.

## Error and feedback behavior

- Backend field errors are attached to the corresponding forms where possible.
- Safe JSON `detail` messages are shown for business conflicts such as protected deletion.
- Raw HTML responses are never rendered; unexpected text/server responses use generic safe messages.
- `401` may trigger a single token refresh; terminal authentication failure clears local auth state.
- `403`, `404`, validation errors, loading, empty/filter-empty states, and mutation success are presented through shared components.
- Success announcements use restrained application-level feedback with `aria-live="polite"`.

## Contract boundaries

- The UI does not implement independent stock, transition, payment, role, or audit rules as a substitute for backend validation.
- Product images reuse URLs already returned in products and nested order items; Inventory uses its existing Product lookup. No extra media API exists.
- Histories and AuditLog are immutable through normal APIs/Admin, not necessarily against privileged database access.
- Frontend validation improves UX but Django/DRF remains authoritative.
- The frontend currently has no automated test suite; integration is validated by lint/build checks and manual E2E against the backend.
