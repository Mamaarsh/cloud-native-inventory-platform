# Portfolio Architecture

This diagram presents the verified delivery, runtime, storage, and observability paths of the Cloud Native Inventory Platform. It describes a production-oriented kubeadm lab, not a public-cloud or production-HA deployment.

```mermaid
flowchart TB
  Developer([Developer]) --> GitHub[GitHub main]
  GitHub --> Action[GitHub Actions sync and trigger]
  Action --> GitLab[Hamgit / GitLab CI]

  subgraph Pipeline[GitLab CI/CD]
    direction LR
    Test[Test<br/>Django 246 tests<br/>Frontend lint and build<br/>Kubernetes Agent check]
    Build[Build<br/>Nexus-proxied bases]
    Scan[Trivy security gate<br/>HIGH / CRITICAL]
    Deploy[Deploy<br/>Migration Job<br/>Exact commit SHA]
    Test --> Build --> Scan --> Deploy
  end

  GitLab --> Pipeline
  Proxy[(Nexus proxy<br/>192.168.122.1:8083)] --> Build
  Build --> Hosted[(Nexus hosted images<br/>nexus.local:8084)]
  Hosted --> Deploy

  subgraph Cluster[kubeadm Kubernetes cluster]
    Ingress[NGINX Ingress]
    Frontend[Frontend replicas x2<br/>React + unprivileged NGINX]
    Backend[Backend replicas x2<br/>Django + Gunicorn]
    Celery[Celery worker]
    PostgreSQL[(PostgreSQL StatefulSet)]
    Redis[(Redis StatefulSet)]

    Ingress -->|/| Frontend
    Ingress -->|/api| Backend
    Ingress -->|/media| Frontend
    Backend --> PostgreSQL
    Backend --> Redis
    Celery --> PostgreSQL
    Celery --> Redis

    Media[(Longhorn RWX media PVC<br/>2 GiB / two replicas)]
    Backend -->|/app/media RW| Media
    Media -->|/var/www/media RO| Frontend
    Media --> Replica1[worker-1 replica]
    Media --> Replica2[worker-2 replica]
  end

  Deploy --> Cluster

  subgraph Observability[Observability]
    NodeExporter[node-exporter]
    KSM[kube-state-metrics]
    NginxMetrics[NGINX metrics]
    ServiceMonitor[ServiceMonitor]
    Prometheus[(Prometheus)]
    Grafana[Grafana<br/>Kubernetes Cluster Monitoring]

    NodeExporter --> Prometheus
    KSM --> Prometheus
    NginxMetrics --> ServiceMonitor --> Prometheus
    Prometheus --> Grafana
  end

  Cluster -. metrics .-> Observability
```

## Reading the diagram

- CI pulls build/test dependencies through the internal Nexus proxy on `192.168.122.1:8083`; it publishes application images to the separate hosted registry exposed as `nexus.local:8084`.
- Trivy scans exact commit-SHA images before the deploy stage can run.
- NGINX Ingress routes browser, API, and media traffic. The frontend reads the same media volume that backend replicas write.
- Prometheus discovers infrastructure and NGINX signals; Grafana loads the version-controlled dashboard.

Rendered versions: [SVG](architecture.svg) and [PNG](architecture.png).
