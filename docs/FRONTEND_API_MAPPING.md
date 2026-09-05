# Frontend API Mapping

This document maps the frontend to the Django REST Framework API as it exists in
the repository. It is the contract used by the React application; no backend
behavior is inferred from UI requirements when it differs from the code.

## Base URL and conventions

- The frontend treats `VITE_API_URL` as the API root (for example `/api` or
  `http://localhost:8000/api`).
- Authentication endpoints are below `/auth/` relative to that root.
- Inventory resources are below `/v1/` relative to that root.
- Collection endpoints use DRF page-number pagination:

  ```json
  {
    "count": 42,
    "next": "http://localhost:8000/api/v1/products/?page=2",
    "previous": null,
    "results": []
  }
  ```

- The configured page size is 10.
- Protected requests use `Authorization: Bearer <access-token>`.
- Successful deletes return HTTP 204 with no response body.
- Validation errors use normal DRF field-error objects. Authentication and
  permission failures generally use `{ "detail": "..." }`.
- Decimal values such as product price and order-item unit price are serialized
  as strings.

## Authentication

| Method | Path | Authentication | Request | Success response |
| --- | --- | --- | --- | --- |
| POST | `/auth/token/` | Public | `{ "username": string, "password": string }` | `{ "access": string, "refresh": string }` |
| POST | `/auth/token/refresh/` | Public | `{ "refresh": string }` | `{ "access": string }` |
| GET | `/auth/me/` | Bearer token | none | Current-user object below |

Current-user response:

```json
{
  "username": "alex",
  "email": "alex@example.com",
  "first_name": "Alex",
  "last_name": "Morgan",
  "groups": ["Warehouse Manager"],
  "is_staff": false
}
```

The response does not expose a user ID or `is_superuser` flag. Frontend role
checks therefore use group names and remain a UX convenience; the API is the
authorization authority.

## Products

Base path: `/v1/products/`

| Method | Path | Allowed by backend | Request/response notes |
| --- | --- | --- | --- |
| GET | `/v1/products/` | Any authenticated user | Paginated product list |
| POST | `/v1/products/` | Admin | Writable fields: `name`, `sku`, `price`, `is_active` |
| GET | `/v1/products/{id}/` | Any authenticated user | Product object |
| PUT/PATCH | `/v1/products/{id}/` | Admin | Same writable fields; PATCH may be partial |
| DELETE | `/v1/products/{id}/` | Admin | HTTP 204 |

Product shape:

```json
{
  "id": 1,
  "name": "Barcode Scanner",
  "sku": "SCN-001",
  "price": "149.99",
  "is_active": true,
  "created_at": "2026-09-05T10:00:00Z",
  "updated_at": "2026-09-05T10:00:00Z"
}
```

Query parameters:

- `sku` — exact filter
- `search` — searches name and SKU
- `ordering` — `name`, `price`, or `created_at`; prefix with `-` for descending
- `page` — page number

## Warehouses

Base path: `/v1/warehouses/`

| Method | Path | Allowed by backend | Request/response notes |
| --- | --- | --- | --- |
| GET | `/v1/warehouses/` | Admin, Warehouse Manager, Operator, Auditor | Paginated warehouse list |
| POST | `/v1/warehouses/` | Admin | Writable fields: `name`, `location` |
| GET | `/v1/warehouses/{id}/` | Admin, Warehouse Manager, Operator, Auditor | Warehouse object |
| PUT/PATCH | `/v1/warehouses/{id}/` | Admin | Same writable fields; PATCH may be partial |
| DELETE | `/v1/warehouses/{id}/` | Admin | HTTP 204 |

Warehouse shape:

```json
{
  "id": 1,
  "name": "Central Warehouse",
  "location": "Tehran",
  "created_at": "2026-09-05T10:00:00Z"
}
```

Query parameters:

- `location` — exact filter
- `search` — searches name and location
- `ordering` — `name` or `created_at`; prefix with `-` for descending
- `page` — page number

## Inventory

Base path: `/v1/inventory/`

| Method | Path | Allowed by backend | Request/response notes |
| --- | --- | --- | --- |
| GET | `/v1/inventory/` | Admin, Warehouse Manager, Operator, Auditor | Paginated inventory list |
| POST | `/v1/inventory/` | Admin, Warehouse Manager, Operator | Writable: `product`, `warehouse`, `quantity` |
| GET | `/v1/inventory/{id}/` | Admin, Warehouse Manager, Operator, Auditor | Inventory object |
| PUT/PATCH | `/v1/inventory/{id}/` | Admin, Warehouse Manager | Same writable fields; PATCH may be partial |
| DELETE | `/v1/inventory/{id}/` | Admin | HTTP 204 |

Inventory shape uses foreign-key IDs rather than nested product/warehouse data:

```json
{
  "id": 1,
  "product": 3,
  "warehouse": 2,
  "quantity": 25,
  "updated_at": "2026-09-05T10:00:00Z"
}
```

Query parameters:

- `product` — product ID
- `warehouse` — warehouse ID
- `search` — product name/SKU or warehouse name
- `ordering` — `quantity` or `updated_at`; prefix with `-` for descending
- `page` — page number

## Orders

Base path: `/v1/orders/`

| Method | Path | Allowed by backend | Request/response notes |
| --- | --- | --- | --- |
| GET | `/v1/orders/` | Admin, Warehouse Manager, Operator, Auditor | Paginated order list |
| POST | `/v1/orders/` | Admin | Nested creation payload; authenticated user is assigned server-side |
| GET | `/v1/orders/{id}/` | Admin, Warehouse Manager, Operator, Auditor | Nested order response |
| PUT/PATCH | `/v1/orders/{id}/` | Admin, Warehouse Manager | No ordinary mutable fields; status changes are explicitly rejected and must use the action below |
| DELETE | `/v1/orders/{id}/` | Admin | HTTP 204 |
| POST | `/v1/orders/{id}/change-status/` | Admin; Warehouse Manager for two transitions only | `{ "status": OrderStatus }`; returns the updated nested order |
| POST | `/v1/orders/{id}/pay/` | Admin | Body must be `{}`; returns payment object |

Order creation request:

```json
{
  "items": [
    { "product": 1, "warehouse": 2, "quantity": 3 }
  ]
}
```

Creation constraints enforced by the backend include a non-empty item list,
unique product/warehouse pairs, active products, positive quantities, and enough
warehouse stock. New orders always start as `pending`; the client cannot provide
the user or status.

Order response:

```json
{
  "id": 7,
  "user": {
    "id": 4,
    "username": "alex",
    "email": "alex@example.com"
  },
  "status": "pending",
  "created_at": "2026-09-05T10:00:00Z",
  "updated_at": "2026-09-05T10:00:00Z",
  "items": [
    {
      "id": 12,
      "product": { "id": 1, "name": "Barcode Scanner", "sku": "SCN-001" },
      "warehouse": { "id": 2, "name": "Central Warehouse", "location": "Tehran" },
      "quantity": 3,
      "unit_price": "149.99"
    }
  ]
}
```

Query parameters:

- `status` — exact status filter
- `user` — user ID
- `search` — user username/email or item product name/SKU
- `ordering` — `created_at`, `updated_at`, or `status`; prefix with `-` for descending
- `page` — page number

### Order status workflow

Valid state transitions are:

- `pending` → `processing` or `cancelled`
- `processing` → `shipped` or `cancelled`
- `shipped` → `delivered`
- `delivered` and `cancelled` are terminal

Admin may perform every valid transition. Warehouse Manager may only perform
`pending` → `processing` and `processing` → `shipped`. Operator and Auditor
cannot change status.

### Payments

Payment response returned by the order `pay` action:

```json
{
  "id": 5,
  "order": 7,
  "amount": "449.97",
  "status": "succeeded",
  "provider": "mock",
  "provider_reference": "pay_...",
  "created_at": "2026-09-05T10:02:00Z",
  "updated_at": "2026-09-05T10:02:01Z"
}
```

The current backend has no payment list/detail endpoint and does not embed a
payment in an order response. Consequently, the UI can display the result of a
payment made in the current session, but cannot reload historical payment state.
It calculates the visible order total from historical `unit_price × quantity`.

## Notifications

The backend has a Notification model, but it does not expose a notification REST
endpoint or serializer. The frontend defines the domain type for future use but
does not issue unsupported notification requests.

## Health endpoints

These endpoints are public and are not used as application data endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health/live/` | Process liveness; `{ "status": "ok" }` |
| GET | `/health/ready/` | Database readiness |
| GET | `/health/dependencies/` | Database/Redis diagnostic status |

## Role discrepancy resolved in favor of backend behavior

The frontend brief describes Warehouse Manager as able to “manage warehouse
operations.” The actual backend only permits Admin to create, update, or delete
Warehouse records. Warehouse Manager can create/update Inventory and perform its
two explicit order-status transitions. Operator can create Inventory but cannot
update it. Order creation and payment are Admin-only because both are POST actions
governed by `OrderPermission`. The UI follows these backend rules so it does not
offer controls that will predictably receive HTTP 403 responses.
