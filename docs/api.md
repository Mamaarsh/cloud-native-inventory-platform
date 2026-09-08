# API Reference

## Overview

The backend exposes JSON APIs through Django REST Framework. Authentication endpoints use `/api/auth/`; inventory-domain endpoints are versioned under `/api/v1/`. Except for registration, JWT token endpoints, health checks, and OpenAPI pages, requests require a bearer access token.

```http
Authorization: Bearer <access-token>
Content-Type: application/json
```

List endpoints use page-number pagination with 10 results per page unless stated otherwise:

```json
{
  "count": 24,
  "next": "http://localhost/api/v1/products/?page=2",
  "previous": null,
  "results": []
}
```

## Roles and authorization

Django Groups and DRF permission classes enforce authorization on the backend. Frontend visibility is not a security boundary.

| Area | Admin | Warehouse Manager | Operator | Auditor |
|---|---|---|---|---|
| Products | Read and manage | Read | Read | Read |
| Warehouses | Read and manage | Read | Read | Read |
| Inventory | Read, create, adjust, delete | Read, create, adjust | Read and create | Read |
| Orders | Read, create, valid transitions, pay | Read and operational transitions | Read | Read |
| Users | Approve and assign roles | — | — | — |
| Audit log | Read | — | — | Read |

The normal inventory update serializer does not allow clients to change `product`, `warehouse`, or `quantity` after creation. Stock changes use the dedicated adjustment endpoint.

## Authentication

### Register

`POST /api/auth/register/` — public.

```json
{
  "username": "newuser",
  "email": "user@example.com",
  "first_name": "محمد",
  "last_name": "جعفری",
  "password": "strong-password",
  "password_confirm": "strong-password"
}
```

The password is validated with Django's configured validators. Protected fields such as `groups`, `role`, `is_active`, `is_staff`, `is_superuser`, and permissions are rejected. A successful request returns `201`:

```json
{"detail": "Account created and awaiting administrator approval."}
```

The new account is inactive, has no group, and receives no tokens until an application Admin approves it and assigns a role.

### Obtain tokens

`POST /api/auth/token/` — public.

```json
{"username": "operator", "password": "password"}
```

Returns `access` and `refresh` JWTs for valid active accounts. Inactive or invalid credentials return `401`.

### Refresh an access token

`POST /api/auth/token/refresh/` — public.

```json
{"refresh": "<refresh-token>"}
```

### Current user

- `GET /api/auth/me/` returns `username`, `email`, `first_name`, `last_name`, `groups`, and `is_staff`.
- `PATCH /api/auth/me/` accepts only `email`, `first_name`, and `last_name`.

`username`, groups, roles, staff status, superuser status, and permissions are not editable through this endpoint.

### Change password

`POST /api/auth/change-password/` — authenticated.

```json
{
  "current_password": "old-password",
  "new_password": "new-password",
  "new_password_confirm": "new-password"
}
```

The current password must be correct, confirmation must match, and Django password validators must pass. Success returns:

```json
{"detail": "Password changed successfully."}
```

Password changes do not currently blacklist or revoke existing JWTs; the frontend clears its local tokens and requires a new login.

## User administration

These endpoints require membership in the application `Admin` group. A Django superuser without that group does not implicitly receive access.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/auth/admin/users/` | List accounts |
| `GET` | `/api/auth/admin/users/{id}/` | Inspect one account |
| `PATCH` | `/api/auth/admin/users/{id}/` | Change `is_active` and/or application `role` |

The list accepts `status=pending|active` and `ordering=<field>`. Role assignment replaces only application-role groups and accepts `Admin`, `Warehouse Manager`, `Operator`, or `Auditor`. Safeguards prevent managing superusers through this API, self-deactivation, and removal of the requesting Admin's own Admin role.

## Products

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/products/` | Paginated product list |
| `POST` | `/api/v1/products/` | Create a product |
| `GET` | `/api/v1/products/{id}/` | Product detail |
| `PUT/PATCH` | `/api/v1/products/{id}/` | Update or activate/deactivate |
| `DELETE` | `/api/v1/products/{id}/` | Permanently delete an unused product |

All authenticated users may read products; only Admin may mutate them. Fields include `id`, `name`, `sku`, `price`, `image`, `is_active`, and timestamps.

Create/update supports JSON when no image file is sent and `multipart/form-data` for an upload. Images must be actual JPEG, PNG, or WebP files and no larger than 5 MiB. `remove_image=true` explicitly removes the current image. Nginx permits `/api/` request bodies up to `6m` to accommodate multipart overhead; Django remains authoritative for the 5 MiB file rule.

Deleting a referenced product returns `409 Conflict`:

```json
{
  "detail": "This product cannot be deleted because it is referenced by inventory or order history. Deactivate it instead."
}
```

Use deactivation to retain historical references.

Filters: `sku`; search: `name`, `sku`; ordering: `name`, `price`, `created_at` (prefix with `-` for descending).

## Warehouses

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/warehouses/` | Paginated warehouse list |
| `POST` | `/api/v1/warehouses/` | Create a warehouse |
| `GET` | `/api/v1/warehouses/{id}/` | Warehouse detail |
| `PUT/PATCH` | `/api/v1/warehouses/{id}/` | Update a warehouse |
| `DELETE` | `/api/v1/warehouses/{id}/` | Delete an unused warehouse |

All four application roles may read; only Admin may mutate. Fields include `id`, `name`, `location`, and timestamps. Referenced warehouses return `409 Conflict` with a safe detail message and must be retained to preserve inventory/order history.

Filter: `location`; search: `name`, `location`; ordering: `name`, `created_at`.

## Inventory

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/inventory/` | Paginated inventory list |
| `POST` | `/api/v1/inventory/` | Create a product/warehouse record |
| `GET` | `/api/v1/inventory/{id}/` | Inventory detail |
| `PUT/PATCH` | `/api/v1/inventory/{id}/` | Standard serializer update |
| `DELETE` | `/api/v1/inventory/{id}/` | Delete a record with no movement history |
| `POST` | `/api/v1/inventory/{id}/adjust/` | Atomically adjust stock |
| `GET` | `/api/v1/inventory/{id}/movements/` | Paginated movement history |

Create requires `product`, `warehouse`, and a non-negative initial `quantity`. The record starts at zero internally and positive initial stock is applied through the stock service so it receives movement history. Admin, Warehouse Manager, and Operator may create. All roles may read. Only Admin may delete, and movement history prevents deletion.

Stock changes must use:

```json
{
  "quantity_delta": 12,
  "reason": "Cycle count correction"
}
```

Admin and Warehouse Manager may adjust. The transaction locks the inventory row, prevents negative stock, updates quantity, and returns a newly created movement (`201`) containing movement type, delta, before/after quantities, reason, optional order, performer, and timestamp. Movement history is immutable through normal API and Admin paths.

Filters: `product`, `warehouse`; search: product name/SKU and warehouse name; ordering: `quantity`, `updated_at`.

## Orders

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/orders/` | Paginated order list |
| `POST` | `/api/v1/orders/` | Create a nested order |
| `GET` | `/api/v1/orders/{id}/` | Order detail, including current payment |
| `PUT/PATCH` | `/api/v1/orders/{id}/` | Standard read-only representation; direct status changes are rejected |
| `DELETE` | `/api/v1/orders/{id}/` | Admin-only; history normally prevents deletion |
| `POST` | `/api/v1/orders/{id}/change-status/` | Apply an allowed transition |
| `GET` | `/api/v1/orders/{id}/history/` | Complete chronological status history |
| `POST` | `/api/v1/orders/{id}/pay/` | Process payment with the mock provider |

All roles may read. Only Admin may create or delete orders. Django Admin cannot create Orders; the API/service path is authoritative.

### Create an order

```json
{
  "items": [
    {"product": 1, "warehouse": 2, "quantity": 3}
  ]
}
```

The authenticated user becomes the owner and new orders always start `pending`. Within one transaction the service validates active products and positive quantities, locks inventory rows, checks/deducts stock, snapshots each product price into `unit_price`, creates movement/status history, and records audit activity. Any failure rolls back the operation.

Order responses include nested user and item data. Each item contains its product (`id`, `name`, `sku`, `image`), warehouse (`id`, `name`, `location`), quantity, and historical `unit_price`. The detail response also includes `payment`, which is an object or `null`.

### Status workflow

```text
pending -> processing -> shipped -> delivered
    \             \
     -> cancelled  -> cancelled
```

`POST .../change-status/` accepts `{"status": "processing"}`. Admin may perform every valid transition. Warehouse Manager may perform `pending → processing` and `processing → shipped`. Operator and Auditor cannot change status. Invalid transitions return `400`. Direct status changes through normal PATCH are rejected.

`GET .../history/` is intentionally unpaginated because the state machine bounds its size. History is immutable through normal application paths.

### Payment

`POST .../pay/` accepts an empty JSON object. Only Admin may execute it. Amount, status, provider, and provider reference are server-controlled. The service locks the order/payment path, persists one Payment per Order, and returns `201` for the first created result or `200` when an existing successful payment is returned idempotently. A successful payment moves a pending order to processing through the same status service. The current provider is a local/mock implementation.

Filters: `status`, `user`; search: owner username/email and item product name/SKU; ordering: `created_at`, `updated_at`, `status`.

## Audit logs

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/audit-logs/` | Paginated activity list |
| `GET` | `/api/v1/audit-logs/{id}/` | Activity detail |

Audit records expose actor, action, target type/ID, a target-label snapshot, validated JSON metadata, and timestamp. Access is read-only and restricted to application Admin and Auditor roles. Metadata rejects sensitive keys and enforces a size limit. The application records significant business and security mutations.

Filters: `action`, `target_type`, `actor`; search: target label/ID and actor username; ordering: `created_at`.

Audit and domain-history immutability applies through normal API/Admin application paths; privileged database or queryset-level operations remain outside that guarantee.

## Health endpoints

Health endpoints are public and unversioned.

| Method | Path | Meaning |
|---|---|---|
| `GET` | `/api/health/live/` | Process can answer; no dependency checks |
| `GET` | `/api/health/ready/` | PostgreSQL `SELECT 1`; `200` ready or `503` not ready |
| `GET` | `/api/health/dependencies/` | PostgreSQL and Redis diagnostic status |

Readiness intentionally excludes Redis. The dependencies response reports `healthy`, `degraded` when only Redis is unavailable, or `unhealthy` when PostgreSQL is unavailable.

## OpenAPI documentation

- Schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`
- ReDoc: `GET /api/redoc/`

The generated schema includes JWT bearer authentication, endpoint tags, request/response serializers, and documented error responses. Application-freeze schema validation passes without errors or warnings.

## Common response behavior

- `400 Bad Request` — serializer, domain, transition, stock, or upload validation failed.
- `401 Unauthorized` — missing, invalid, expired, or inactive-account credentials.
- `403 Forbidden` — authenticated user lacks the required role/action permission.
- `404 Not Found` — resource does not exist or is unavailable through the endpoint.
- `409 Conflict` — product or warehouse deletion conflicts with referenced history.
- `503 Service Unavailable` — readiness-critical PostgreSQL check failed.

Validation errors are JSON field mappings or a safe `detail` message. Server HTML is not an API contract.
