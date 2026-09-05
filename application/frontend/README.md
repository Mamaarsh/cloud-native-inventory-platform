# Stockline frontend

React and TypeScript operations UI for the Cloud Native Inventory Platform.
The exact backend contract and role matrix are documented in
[`../FRONTEND_API_MAPPING.md`](../FRONTEND_API_MAPPING.md).

## Local development

1. Install dependencies:

   ```bash
   npm install
   ```

2. Create an untracked local environment file from the example:

   ```bash
   cp .env.example .env
   ```

3. Start Django on `http://localhost:8000`, then start the frontend:

   ```bash
   npm run dev
   ```

The example uses `VITE_API_URL=/api` and Vite proxies `/api` to the target in
`VITE_API_PROXY_TARGET`. This avoids requiring backend CORS changes during local
development and keeps all frontend endpoint paths compatible with both
`/api/auth/` and `/api/v1/`.

For a same-origin production deployment, set `VITE_API_URL` to the public API
root (normally `/api`) when building. If the frontend and backend use different
origins, the backend/reverse proxy must explicitly allow the frontend origin;
this repository intentionally does not alter backend CORS configuration.

## Validation

```bash
npm run lint
npm run build
```

The production bundle is emitted to `dist/`. The hosting server must provide an
SPA fallback to `index.html` for client-side routes such as `/orders/42`.
