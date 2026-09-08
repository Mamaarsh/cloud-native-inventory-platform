# Stockline backend

Django REST Framework API and domain layer for the Cloud Native Inventory Platform.
See the [API reference](../../docs/api.md) and [architecture](../../docs/architecture.md) for repository-wide contracts.

## Technologies

- Python 3.14, Django 5.2, and Django REST Framework
- PostgreSQL 16 and psycopg
- SimpleJWT and Django Groups/Permissions
- drf-spectacular, Pillow, Gunicorn, Celery, and Redis configuration

## Structure

```text
config/       # Settings, root URLs, WSGI/ASGI, and Celery configuration
users/        # Custom User, authentication/profile APIs, Admin user APIs, and RBAC
inventory/    # Models, serializers, viewsets, services, tasks, Admin, and tests
```

Versioned domain endpoints are mounted under `/api/v1/`; authentication is under `/api/auth/`. Business mutations are centralized in services for order creation/status, stock adjustment, payments, notifications, and audit recording.

## Responsibilities

- Inactive-by-default registration, Admin approval/role assignment, JWT, profile, and password APIs
- Backend-enforced RBAC for Admin, Warehouse Manager, Operator, and Auditor
- Products and warehouses with protected deletion; validated JPEG/PNG/WebP product images up to 5 MiB
- Server-controlled inventory, atomic stock adjustment, row locking, and movement history
- Nested order creation with stock deduction, historical prices, status state machine, and status history
- One-to-one mock payment processing, notification persistence/tasks, and global application audit records
- OpenAPI documentation plus liveness, readiness, and dependency health endpoints

## Local development

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Export the required environment variables using the repository-root [`.env.example`](../../.env.example) as a non-secret reference. This project does not load `.env` files in Python; local values must be exported by the shell or supplied by the runtime.

3. Prepare the database and RBAC groups:

   ```bash
   python manage.py migrate
   python manage.py create_roles
   python manage.py createsuperuser
   python manage.py runserver
   ```

## Environment

Required database variables are `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`. Runtime configuration also includes:

- `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS`
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`
- `SECURE_SSL_REDIRECT`, secure-cookie settings, HSTS settings, and `TRUST_X_FORWARDED_PROTO`

Use untracked environment values or a secret manager. Never store passwords, signing keys, JWTs, or registry credentials in the repository.

## Commands

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py spectacular --file schema.yml --validate
```

The application-freeze baseline has migrations through `inventory.0008_auditlog` and 246 passing backend tests.

## Production runtime

The Docker image uses configurable `PYTHON_BASE_IMAGE`. Its entrypoint runs migrations and `collectstatic`, then Gunicorn serves Django on port 8000. Compose mounts:

- `/app/staticfiles` to `static_data` for Nginx `/static/` delivery;
- `/app/media` to `media_data` for Nginx `/media/` delivery; and
- PostgreSQL data to `postgres_data`.

This static/media path is verified with `DEBUG=False`. The current lab supplies base images through the Nexus Docker group; the Dockerfile does not hardcode that address.

## API operations

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI schema: `/api/schema/`
- Liveness: `/api/health/live/` (process only)
- Readiness: `/api/health/ready/` (PostgreSQL)
- Dependencies: `/api/health/dependencies/` (PostgreSQL and Redis)

## Important notes

- Orders cannot be created in Django Admin; the API/service path is authoritative for item validation and stock deduction.
- Inventory movement, order status, and audit histories are immutable through normal API/Admin paths, not against privileged database or queryset-level access.
- Product and warehouse foreign-key protection preserves referenced operational history and returns a safe `409 Conflict` from the API.
- The payment provider is a persisted mock/local implementation.
- Notification models, services, and Celery tasks exist, but the current Compose file does not deploy a Celery worker.
- Password changes do not revoke previously issued JWTs; additional blacklist/revocation work would be required.
