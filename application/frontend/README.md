# Stockline frontend

React and TypeScript operations UI for the Cloud Native Inventory Platform.
The exact backend contract and role matrix are documented in
[`../../docs/FRONTEND_API_MAPPING.md`](../../docs/FRONTEND_API_MAPPING.md).

## Technologies

- React, TypeScript, and Vite
- TanStack Query for server state
- Tailwind CSS and shared accessible UI components
- Axios with JWT refresh handling
- Nginx for the production SPA and reverse proxy

## Structure

```text
src/
├── api/          # Typed backend clients and shared Axios configuration
├── auth/         # Session context, token storage, and route/role guards
├── components/   # Domain and shared UI components
├── feedback/     # Accessible success announcements
├── hooks/        # TanStack Query hooks and UI helpers
├── lib/          # Formatting, roles, media URLs, and safe API errors
├── pages/        # Routed application screens
├── routes/       # Public and protected routes
└── types/        # API and domain types
```

## Responsibilities

- Login, registration, JWT refresh, protected routes, and role-aware navigation
- Dashboard, Products/Product Detail, Warehouses, and Inventory screens
- Transactional inventory adjustment and stock-movement history
- Orders, nested order creation, Order Detail, status timeline, and payment actions
- Account/profile and password management, Admin user approval/roles, and Audit Log
- Pagination, debounced search, filters, loading/empty states, safe API errors, and product images

Backend permission checks remain authoritative; frontend guards only control navigation and presentation.

## Local development

1. Install dependencies:

   ```bash
   npm ci
   ```

2. Create an untracked local environment file from the example:

   ```bash
   cp .env.example .env
   ```

3. Start Django on `http://localhost:8000`, add the proxy target below to `.env`, then start Vite:

   ```dotenv
   VITE_API_URL=/api
   VITE_API_PROXY_TARGET=http://localhost:8000
   ```

   ```bash
   npm run dev
   ```

## Environment

- `VITE_API_URL` is the browser-visible API root and normally remains `/api`.
- `VITE_API_PROXY_TARGET` is a development-only Vite proxy target; it is not embedded in production builds.

Relative `/api` and `/media` paths keep the UI compatible with same-origin Docker/Nginx deployment. Product image rendering accepts backend media URLs and safely falls back when an image is absent or broken.

## Production runtime

The multi-stage Dockerfile builds the Vite bundle with configurable `NODE_BASE_IMAGE` and serves it with configurable `NGINX_BASE_IMAGE`. Nginx:

- serves the SPA with a fallback to `index.html`;
- proxies `/api/` to the Gunicorn backend;
- serves `/static/` and `/media/` directly from read-only Compose volumes; and
- permits API request bodies up to `6m`, leaving Django to enforce the 5 MiB product-image file limit.

The current lab resolves base images through Nexus; the registry address is supplied at build time rather than hardcoded in the Dockerfile.

## Validation

```bash
npm run lint
npm run build
```

The production bundle is emitted to `dist/`. There is currently no frontend automated test suite; validation uses linting, TypeScript/production builds, and manual E2E testing.

## Important notes

- Access and refresh tokens are stored in `localStorage`; logout clears the current browser session but does not revoke already-issued JWTs server-side.
- RBAC, validation, stock changes, status transitions, payments, and audit behavior are enforced by the backend.
- The current Compose stack does not run a Celery worker, so deployed asynchronous notification delivery remains future operational work.
