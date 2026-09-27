# Project Descriptions

## LinkedIn Projects section

Cloud Native Inventory Platform is a production-oriented DevOps portfolio project built around a working Django REST Framework and React inventory application. I designed a GitHub-to-GitLab CI/CD path that tests the application, builds images through internal Nexus registries, blocks fixable HIGH/CRITICAL vulnerabilities with Trivy, and deploys immutable commit-SHA releases to a kubeadm Kubernetes cluster. The runtime includes PostgreSQL, Redis, Celery, NGINX Ingress, Longhorn persistence, restricted workload security controls, and Prometheus/Grafana observability. Product uploads use a two-replica Longhorn RWX volume shared by backend writers and read-only frontend consumers. The repository documents both the implementation and its production limitations.

## CV / Resume

- Designed an end-to-end GitHub-to-GitLab delivery workflow with application tests, Nexus-backed image builds, blocking Trivy gates, migration-before-rollout sequencing, and immutable commit-SHA Kubernetes releases.
- Deployed a Django/React workload with PostgreSQL, Redis, and Celery to a three-node kubeadm cluster using non-root containers, restricted Pod Security controls, least-privilege identities, probes, resource bounds, Ingress, and NetworkPolicies.
- Implemented a dedicated 2 GiB Longhorn RWX media architecture with two worker-distributed replicas, backend read-write access, frontend read-only delivery, and persistence across Pod restarts.
- Integrated kube-prometheus-stack, NGINX metrics discovery, and a version-controlled Grafana dashboard for node, pod, request, status-code, and latency signals.

## GitHub repository description

Production-oriented Django/React DevOps lab with GitLab CI/CD, Nexus, Trivy, kubeadm Kubernetes, Longhorn RWX storage, and Prometheus/Grafana observability.

## Interview elevator pitch

I built a real inventory and order-management application as the workload for an end-to-end DevOps lab. GitHub triggers GitLab CI, which runs 246 backend tests and frontend checks, builds through Nexus, blocks vulnerable images with Trivy, and deploys exact commit-SHA releases to a three-node kubeadm cluster after migrations succeed. The application runs with PostgreSQL, Redis, Celery, NGINX Ingress, least-privilege Kubernetes controls, and Prometheus/Grafana monitoring. I also solved shared product-media persistence with a two-replica Longhorn RWX volume and used a real Trivy-blocked CVE as a complete diagnose, patch, rescan, and release exercise. I describe it as production-oriented and document the remaining production gaps explicitly.
