# Seven-Slide LinkedIn Carousel

Use a 1080×1350 portrait canvas, one visual idea per slide, and no more than four short text blocks. Keep source labels readable on mobile.

## Slide 1 — Cloud-Native Inventory Platform

- End-to-End DevOps Portfolio Project
- Real Django + React workload
- Source → security gate → Kubernetes → observability
- Production-oriented lab, with documented boundaries

**Visual:** rendered `architecture.svg` faded behind the title or a clean application thumbnail plus Kubernetes/CI icons.

## Slide 2 — The Application

- Products, warehouses, inventory, and orders
- JWT authentication and backend-enforced roles
- PostgreSQL + Redis + Celery
- Persistent product image upload and delivery

**Visual:** `application-dashboard.png`, centered on the Printer product and real thumbnail.

## Slide 3 — CI/CD Pipeline

- GitHub → Hamgit/GitLab
- 246 backend tests + frontend lint/build
- Nexus-backed images tagged with the commit SHA
- Migration-first Kubernetes rollout

**Visual:** `gitlab-pipeline.png`; add a small five-stage ribbon: Test → Build → Security → Deploy → Cleanup.

## Slide 4 — Kubernetes Architecture

- Three-node kubeadm cluster
- 2× frontend, 2× backend, Celery
- PostgreSQL and Redis StatefulSets
- NGINX Ingress + Calico NetworkPolicies

**Visual:** crop the runtime section of `architecture.svg` beside `kubernetes-workloads.png`.

## Slide 5 — Persistent Storage with Longhorn

- Dedicated 2 GiB RWX media volume
- Two replicas: worker-1 + worker-2
- Backend read-write; frontend read-only
- Uploads survive Pod restarts

**Visual:** `longhorn-media.png` or the terminal alternative from `SCREENSHOTS.md`, plus a small RW/RO flow.

## Slide 6 — DevSecOps + Observability

- Trivy caught a real HIGH CVE and stopped deployment
- `libexpat 2.8.4-r0` → `2.8.5-r0`
- Prometheus + Grafana + cluster exporters
- NGINX request, status, and latency metrics

**Visual:** split layout using `trivy-security-scan.png` and `grafana-cluster-monitoring.png`.

## Slide 7 — What I Learned

- Debug system boundaries, not just individual tools
- Immutable identity and migration ordering matter
- Storage semantics must match application behavior
- Honest architecture includes known limitations

**Visual:** three small icons for delivery, storage, and observability. End with:

`github.com/Mamaarsh/cloud-native-inventory-platform`
