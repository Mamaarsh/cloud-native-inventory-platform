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

The multi-stage Dockerfile builds the Vite bundle with configurable `NODE_BASE_IMAGE` and serves it with configurable `NGINX_BASE_IMAGE`. Defaults use public Node and `nginxinc/nginx-unprivileged` images; GitLab CI overrides them with the Nexus proxy. NGINX listens on container port `8080` and:

- serves the SPA with a fallback to `index.html`;
- contains a `/api/` proxy to the Gunicorn backend for direct-container/Compose routing;
- contains `/static/` and `/media/` aliases used with the Compose shared volumes; and
- permits API request bodies up to `6m`, leaving Django to enforce the 5 MiB product-image file limit.

In Kubernetes, `inventory.local` Ingress routes browser `/api` requests directly to the backend Service and `/` to the frontend Service. The frontend pod is not an API hop, and NetworkPolicy does not permit frontend-to-backend TCP. The retained `/api/` proxy is therefore redundant for the deployed Ingress path.

The Kubernetes Deployment runs as UID/GID 101 with `frontend-sa`, disables automatic ServiceAccount-token mounting, disables privilege escalation, drops all capabilities, uses `RuntimeDefault` seccomp, and makes the root filesystem read-only. `/tmp` is writable through `emptyDir`; the shared 2 GiB Longhorn RWX `media` claim is mounted read-only at `/var/www/media`. Ingress routes `/media` to frontend NGINX, while backend replicas write the same claim. The dedicated `longhorn-media` class uses two replicas on `application`-tagged disks and requires Longhorn RWX/share-manager support; every node eligible for a frontend pod needs an NFS client (`nfs-common` on Ubuntu); it does not consume `monitoring`-tagged disks.

The repository-root Compose file maps `${FRONTEND_PORT:-8080}` to container port `8080` and keeps `/api`, `/static`, and `/media` same-origin through NGINX.

## Validation

```bash
npm run lint
npm run build
```

The production bundle is emitted to `dist/`. There is currently no frontend automated test suite; GitLab CI runs linting and the TypeScript/production build.

## Important notes

- Access and refresh tokens are stored in `localStorage`; logout clears the current browser session but does not revoke already-issued JWTs server-side.
- RBAC, validation, stock changes, status transitions, payments, and audit behavior are enforced by the backend.
- Compose and Kubernetes run Redis plus a Celery worker. Notification delivery currently uses the persisted mock provider; external email/SMS/chat delivery is not implemented.
