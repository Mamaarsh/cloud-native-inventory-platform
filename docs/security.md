# Security

## Implemented controls

### Application

- JWT authentication with short-lived access tokens and inactive-by-default registration
- Backend-enforced group permissions for Admin, Warehouse Manager, Operator, and Auditor
- Atomic service-layer stock/order operations with database locking and immutable normal-API history views
- Product image format and 5 MiB size validation; media responses are limited to the validated `/media/products/` tree and include `X-Content-Type-Options: nosniff`
- Security headers, clickjacking denial, HTTP-only CSRF cookie, and opt-in HTTPS/HSTS settings
- Health endpoints that do not disclose credentials

Tokens are stored in browser `localStorage`. Password changes and logout do not revoke already issued tokens because blacklist/revocation is not implemented.

### Containers

- Backend uses a non-root application user and removes pip from the runtime image.
- Frontend uses `nginxinc/nginx-unprivileged` and listens on 8080.
- Both images are multi-stage builds.
- GitLab CI performs blocking Trivy image scans for fixable HIGH/CRITICAL findings.

Trivy image scanning does not replace source analysis, secret scanning, runtime detection, artifact signing, or provenance.

### Kubernetes

- The namespace enforces, warns, and audits the Restricted Pod Security standard at `v1.35`.
- Workloads use named ServiceAccounts and set `automountServiceAccountToken: false`.
- Containers run as non-root, disable privilege escalation, drop all Linux capabilities, and use `RuntimeDefault` seccomp.
- Backend/frontend/Celery declare read-only root filesystems and narrow writable mounts.
- Resource requests/limits are set on application, Redis, and PostgreSQL containers.
- Default-deny ingress/egress policies limit application flows.
- Image pull, database, and Django signing values are referenced from Secrets rather than embedded in workloads.

PostgreSQL and Redis keep writable root filesystems for image/runtime compatibility. Kubernetes controls cannot prevent a cluster administrator or storage administrator from reading workload data.

### Delivery identity

The GitLab deployer has a namespace Role for Deployments, Jobs, Pods/logs, Services, Ingresses, NetworkPolicies, and ServiceAccounts. It has no Secret verbs. The pipeline explicitly tests that `kubectl auth can-i get secrets -n inventory` returns `no`.

## Secret handling

The repository contains only placeholders. `.env`, `*.secret.yaml`, private keys, and common credential formats are ignored. `k8s/secrets.example.yaml` must be copied to an ignored file and replaced before use.

Current Secrets are conventional Kubernetes Secrets, which are base64-encoded rather than encrypted by default. Production hardening should add an external secret manager or encrypted GitOps workflow, encryption at rest, rotation procedures, and audited access.

## Network and transport

NetworkPolicies reduce east-west reachability inside `inventory`. Their effectiveness depends on the CNI implementation and cluster configuration. The current application Ingress is HTTP-only, and secure-cookie/HSTS defaults remain disabled to avoid breaking the lab's plain HTTP endpoint. Do not enable HSTS until trusted TLS termination and redirect behavior are proven.

Nexus transport must match containerd/Docker registry configuration. An HTTPS endpoint configured as an insecure HTTP registry—or the inverse—causes pull failures and can create unsafe workarounds.

## Not implemented

- Production TLS/cert-manager and a documented certificate lifecycle
- External Secrets, Vault, SOPS, or Sealed Secrets
- JWT revocation/blacklist, CSP, rate limiting, or WAF policy
- SAST, DAST, secret scanning in CI, SBOM publication, signing, or admission verification
- Centralized security logs, audit retention policy, SIEM, or runtime threat detection
- Automated backups, restore testing, disaster recovery, or production HA
- Formal threat model, penetration test, or compliance certification

## Safe public-repository review

Before publishing or committing:

```bash
git status --short
git diff --check
git grep -n -I -E '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|ghp_[A-Za-z0-9]+|glpat-[A-Za-z0-9_-]+)'
git diff -- . ':!*.lock'
```

Also review screenshots for usernames, internal URLs/IPs, repository tokens, terminal history, Kubernetes Secret values, Grafana credentials, and browser password-manager overlays.
