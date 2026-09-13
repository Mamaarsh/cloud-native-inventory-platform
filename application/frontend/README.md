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

Relative `/api` and `/media` paths keep browser requests same-origin. Product image rendering accepts backend media URLs and safely falls back when an image is absent or broken.

## Production runtime

The multi-stage Dockerfile builds the Vite bundle with configurable `NODE_BASE_IMAGE` and serves it with configurable `NGINX_BASE_IMAGE`. Defaults use the Nexus proxy on port `8083` and `nginxinc/nginx-unprivileged:alpine`. NGINX listens on container port `8080` and:

- serves the SPA with a fallback to `index.html`;
- contains a `/api/` proxy to the Gunicorn backend for direct-container/Compose routing;
- contains `/static/` and `/media/` aliases used with the Compose shared volumes; and
- permits API request bodies up to `6m`, leaving Django to enforce the 5 MiB product-image file limit.

In Kubernetes, `inventory.local` Ingress routes browser `/api` requests directly to the backend Service and `/` to the frontend Service. The frontend pod is not an API hop, and NetworkPolicy does not permit frontend-to-backend TCP. The retained `/api/` proxy is therefore redundant for the deployed Ingress path.

The Kubernetes Deployment runs as UID/GID 101 with `frontend-sa`, disables automatic ServiceAccount-token mounting, disables privilege escalation, drops all capabilities, uses `RuntimeDefault` seccomp, and makes the root filesystem read-only. Only `/tmp` is mounted writable through `emptyDir`.

Kubernetes does not mount the backend media/static `emptyDir` volumes into the frontend pod. Uploaded media is currently ephemeral and not a reliable multi-replica Kubernetes delivery path.

The repository-root Compose file still overrides the frontend base to `nginx:alpine` and maps host `80` to container `80`, which does not match this port-8080 unprivileged configuration. Reconcile those Compose values before using it as an end-to-end frontend runtime.

## Validation

```bash
npm run lint
npm run build
```

The production bundle is emitted to `dist/`. There is currently no frontend automated test suite; GitLab CI runs linting and the TypeScript/production build.

## Important notes

- Access and refresh tokens are stored in `localStorage`; logout clears the current browser session but does not revoke already-issued JWTs server-side.
- RBAC, validation, stock changes, status transitions, payments, and audit behavior are enforced by the backend.
- Compose does not run a Celery worker. Kubernetes deploys neither Redis nor a worker, so asynchronous notification delivery remains future operational work.
