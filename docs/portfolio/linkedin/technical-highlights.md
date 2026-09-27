# Technical Highlights

## Application

**Implemented:** Django REST Framework and React/TypeScript application with JWT authentication, backend-enforced role permissions, products, warehouses, atomic inventory adjustments, orders, audit history, health endpoints, Celery notifications, and validated product images.

**Why:** A realistic stateful workload exposes delivery, migration, authorization, storage, and observability problems that a demonstration service cannot.

**Evidence:** `application/backend/inventory/`, `application/backend/users/`, `application/frontend/src/`, `docs/api.md`, `docs/FRONTEND_API_MAPPING.md`.

## Containers

**Implemented:** Multi-stage backend and frontend images; Gunicorn backend; unprivileged NGINX runtime on port 8080; non-root users; health checks; public local defaults with CI-overridable base images; targeted `libexpat` runtime upgrade.

**Why:** Separate build/runtime concerns, reduce privilege, preserve local portability, and remediate the scanned runtime without weakening policy.

**Evidence:** `application/backend/Dockerfile`, `application/frontend/Dockerfile`, `application/frontend/nginx.conf`, `docker-compose.yml`.

## CI/CD

**Implemented:** GitHub-to-Hamgit synchronization; trigger-only GitLab stages for test, build, security, deploy, and manual cleanup; serialized deploy; stale-release protection; unique migration Job; exact-SHA rollout checks.

**Why:** Ensure each release is tested, attributable, migration-aware, and protected from concurrent or stale deployment.

**Evidence:** `.github/workflows/gitlab-trigger.yml`, `.gitlab-ci.yml`, `docs/ci-cd.md`, `k8s/backend-migration-job.yaml`.

## Registry

**Implemented:** Separate Nexus roles: CI/base-image proxy at `192.168.122.1:8083` and hosted application images at `nexus.local:8084`.

**Why:** Keep build dependencies inside the lab path while publishing controlled application artifacts under immutable commit tags. The ports represent different repository roles and must not be conflated.

**Evidence:** `.gitlab-ci.yml`, `application/backend/Dockerfile`, `application/frontend/Dockerfile`, `.env.example`, `docs/ci-cd.md`.

## Kubernetes

**Implemented:** Two backend replicas, two frontend replicas, one Celery worker, PostgreSQL and Redis StatefulSets, Services, host-based Ingress, probes, resource limits, ServiceAccounts, and migration-first rollout.

**Why:** Exercise stateless scaling, stateful dependencies, controlled releases, and explicit runtime contracts on a kubeadm cluster.

**Evidence:** `k8s/backend-deployment.yaml`, `k8s/frontend-deployment.yaml`, `k8s/celery-deployment.yaml`, `k8s/postgres-statefulset.yaml`, `k8s/redis-statefulset.yaml`, `k8s/inventory-ingress.yaml`.

## Storage

**Implemented:** Dedicated `longhorn-media` StorageClass and a 2 GiB RWX PVC with two replicas on `application`-tagged disks. Backend mounts `/app/media` read-write; frontend mounts `/var/www/media` read-only.

**Why:** Uploaded product images must survive Pod replacement and remain consistent across multiple backend and frontend replicas without sharing writable frontend access.

**Evidence:** `k8s/longhorn-media-storageclass.yaml`, `k8s/media-pvc.yaml`, `k8s/backend-deployment.yaml`, `k8s/frontend-deployment.yaml`, `docs/kubernetes.md`.

## Security

**Implemented:** Restricted Pod Security labels, non-root execution, dropped capabilities, disabled privilege escalation, RuntimeDefault seccomp, read-only roots where compatible, token automount disabled, default-deny NetworkPolicies, least-privilege deployer RBAC, and blocking Trivy scans. A real HIGH `libexpat` CVE stopped deployment until patched.

**Why:** Make security controls release conditions and runtime boundaries rather than documentation-only intentions.

**Evidence:** `k8s/namespace.yaml`, `k8s/serviceaccounts.yaml`, `k8s/network-policies.yaml`, `k8s/gitlab-deployer-rbac.yaml`, `.gitlab-ci.yml`, `application/frontend/Dockerfile`, `docs/security.md`.

## Observability

**Implemented:** kube-prometheus-stack with Prometheus, Grafana, Alertmanager, node-exporter, kube-state-metrics, NGINX metrics, ServiceMonitor discovery, persistent monitoring storage, and dashboard-as-code.

**Why:** Provide inspectable cluster, workload, traffic, error-rate, and latency signals and keep dashboard configuration reviewable in Git.

**Evidence:** `k8s/monitoring/values-monitoring.yaml`, `k8s/monitoring/nginx-ingress-metrics-service.yaml`, `k8s/monitoring/nginx-ingress-servicemonitor.yaml`, `k8s/monitoring/dashboards/`, `docs/observability.md`.

## Networking

**Implemented:** Calico-backed NetworkPolicies, NGINX Ingress routing for `/`, `/api`, and `/media`, internal ClusterIP services, and private NGINX metrics on port 9113.

**Why:** Separate ingress routing from service-to-service authorization and avoid exposing the metrics endpoint publicly.

**Evidence:** `k8s/inventory-ingress.yaml`, `k8s/network-policies.yaml`, `k8s/*-service.yaml`, `k8s/monitoring/nginx-ingress-metrics-service.yaml`, `docs/architecture.md`.

## Documentation

**Implemented:** Architecture, API, CI/CD, Kubernetes operations, observability/PromQL, security boundaries, troubleshooting, roadmap, and portfolio material.

**Why:** Make design intent, evidence, operational constraints, and known gaps reviewable by engineers and interviewers.

**Evidence:** `README.md`, `docs/architecture.md`, `docs/api.md`, `docs/ci-cd.md`, `docs/kubernetes.md`, `docs/observability.md`, `docs/security.md`, `docs/troubleshooting.md`, `docs/roadmap.md`.
