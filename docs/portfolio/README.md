# Portfolio and LinkedIn Material

## LinkedIn post

I built **Cloud Native Inventory Platform**, an end-to-end DevOps portfolio project that uses a real Django and React inventory application to demonstrate the full path from source code to an observable Kubernetes workload.

The application includes JWT authentication, backend-enforced RBAC, products and warehouses, transactional stock movements, order workflows, audit history, health endpoints, Celery tasks, and OpenAPI documentation. The platform work was the main focus:

- Multi-stage Docker images with Gunicorn and unprivileged NGINX
- GitHub Actions synchronization into a GitLab/Hamgit delivery pipeline
- Backend tests plus frontend lint/build quality gates
- Nexus-proxied builds and hosted application images
- Blocking Trivy scans for fixable HIGH/CRITICAL image vulnerabilities
- Exact commit-SHA Kubernetes releases with migration-before-rollout
- Non-root workloads, restricted Pod Security, least-privilege ServiceAccounts/RBAC, and default-deny NetworkPolicies
- PostgreSQL and Redis StatefulSets on Longhorn
- kube-prometheus-stack with Prometheus, Grafana, Alertmanager, node-exporter, and kube-state-metrics
- Declarative F5 NGINX Ingress metrics through a ClusterIP Service and ServiceMonitor
- A Grafana dashboard as code for node, pod, traffic, connection, error-rate, and p50/p95/p99 latency signals

This is a **production-oriented lab implementation**, not a claim that a portfolio cluster is production. The repository documents its boundaries honestly: TLS, external secret management, centralized logging, automated disaster recovery, object-storage media delivery, and production HA remain roadmap work.

The most valuable lesson was that platform engineering is about the joins between systems: immutable artifacts, deployment identity, migration ordering, storage behavior, metric discovery, and documentation that matches the actual configuration.

Repository: `https://github.com/Mamaarsh/cloud-native-inventory-platform`

#DevOps #Kubernetes #Docker #CICD #Prometheus #Grafana #Django #React #PlatformEngineering #CloudNative

## Short LinkedIn version

I built Cloud Native Inventory Platform, a production-oriented DevOps lab around a real Django/React workload. It demonstrates multi-stage containers, GitHub-to-GitLab CI/CD, Nexus, blocking Trivy scans, exact-SHA Kubernetes deployments, migration Jobs, Longhorn state, least-privilege security controls, and kube-prometheus-stack observability. NGINX request/connection/latency metrics feed a version-controlled Grafana dashboard with p50/p95/p99 views. The repository also documents the honest gaps—TLS, external secrets, centralized logs, automated DR, object-storage media delivery, and production HA.

## Suggested carousel order

1. Application dashboard — establishes that the platform supports a real workload.
2. GitLab pipeline — shows test, build, security, deploy, and cleanup stages.
3. Kubernetes workloads — shows backend/frontend/Celery and stateful dependencies healthy.
4. Grafana Kubernetes Cluster Monitoring — shows infrastructure plus NGINX traffic/latency panels.
5. Nexus repository — shows immutable commit-SHA application images.
6. Optional Prometheus NGINX target/query — proves metric discovery.
7. Optional Trivy job — demonstrates the blocking security gate.

## GitHub description

Production-oriented Django/React DevOps lab with Docker, GitHub-to-GitLab CI/CD, Nexus, Trivy, Kubernetes, Longhorn, Prometheus, Grafana, and NGINX metrics.

## Suggested GitHub topics

`devops`, `kubernetes`, `docker`, `django`, `react`, `gitlab-ci`, `github-actions`, `nexus`, `trivy`, `prometheus`, `grafana`, `celery`, `postgresql`, `platform-engineering`, `observability`

## CV / resume bullets

- Built an end-to-end production-oriented delivery lab for a Django/React inventory platform using Docker, GitHub Actions, GitLab CI, Nexus, Trivy, and kubeadm Kubernetes.
- Implemented immutable commit-SHA deployments with serialized releases, pre-rollout Django migration Jobs, stale-release protection, and verified backend/Celery/frontend rollouts.
- Hardened Kubernetes workloads with non-root execution, dropped capabilities, seccomp, Restricted Pod Security, dedicated ServiceAccounts, least-privilege deployer RBAC, and default-deny NetworkPolicies.
- Deployed kube-prometheus-stack with Longhorn persistence and integrated F5 NGINX Ingress request, connection, and latency histograms through a ServiceMonitor.
- Created a version-controlled Grafana dashboard covering node/pod resource signals, HTTP status rates, 5xx percentage, and upstream p50/p95/p99 latency.

## 30-second interview explanation

I built a full-stack inventory application as a realistic workload, then designed the DevOps lifecycle around it. GitHub triggers GitLab CI, which tests the application, builds images through Nexus, blocks vulnerable images with Trivy, and deploys exact commit-SHA versions through a least-privilege Kubernetes Agent. A migration Job must succeed before backend, Celery, and frontend rollouts. The kubeadm lab uses NGINX Ingress, MetalLB, Longhorn, NetworkPolicies, and kube-prometheus-stack. I also made NGINX metrics and the Grafana dashboard declarative. I document it as a production-style lab and call out the production gaps instead of hiding them.

## 2-minute technical explanation

The workload is a Django REST API and React/TypeScript frontend backed by PostgreSQL. Redis transports Celery notification tasks. The backend contains the authoritative RBAC and transactional inventory/order logic, so the UI is not trusted for enforcement.

For local use, Compose builds against public base images, starts PostgreSQL, Redis, backend, Celery, and an unprivileged NGINX frontend on port 8080. The same Dockerfiles accept build arguments so the lab CI uses Nexus-proxied bases without reducing public reproducibility.

On a push to GitHub main, an Action synchronizes the Hamgit/GitLab mirror and triggers a pipeline. The test stage runs Django checks and 246 tests against PostgreSQL plus frontend lint/build. Build jobs publish commit-SHA and `latest` tags to Nexus; Trivy scans the exact SHA images and blocks fixable HIGH/CRITICAL findings. The deploy stage is serialized, confirms the release is not known stale, renders immutable images into temporary manifests, runs a unique migration Job, then rolls out backend, Celery, and frontend with status checks. The deployer can update workloads but cannot read Secrets.

In Kubernetes, restricted Pod Security, non-root users, dropped capabilities, seccomp, read-only roots where compatible, dedicated ServiceAccounts, resource bounds, and default-deny NetworkPolicies reduce workload privilege. Product media uses a dedicated two-replica, 2 GiB Longhorn RWX class restricted to `application`-tagged disks, separate from `monitoring` storage. PostgreSQL and Redis are single-replica StatefulSets on Longhorn, which is appropriate for the lab but not production HA.

For observability, kube-prometheus-stack supplies Prometheus, Grafana, Alertmanager, node-exporter, kube-state-metrics, and operator-managed discovery. I enabled F5 NGINX Prometheus and latency metrics, kept port 9113 private behind a ClusterIP Service, and added a `release=monitoring` ServiceMonitor. The dashboard is version controlled and uses counter rates plus histogram buckets for average and p50/p95/p99 upstream latency. The next serious production steps would be TLS, external secrets, object-storage media delivery, logs, tested backups/restore, alert routing, and HA.
