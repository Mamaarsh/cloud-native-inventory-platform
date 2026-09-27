# English LinkedIn Post

I wanted to stop learning DevOps tools in isolation and make them work together around a real application—not another collection of disconnected YAML files or a Hello World service.

That became **Cloud Native Inventory Platform**, a production-oriented portfolio project built around a Django REST Framework and React inventory application. The workload includes JWT authentication, backend-enforced roles, products and warehouses, transactional stock movements, order history, audit logs, product image uploads, PostgreSQL, Redis, and Celery.

For local development, Docker Compose runs the complete stack. In the delivery path, a push to GitHub is synchronized to Hamgit/GitLab by GitHub Actions. GitLab CI runs 246 backend tests, frontend lint and production build checks, and a Kubernetes Agent permission test. It then builds images from Nexus-proxied base images, publishes immutable commit-SHA tags to the hosted Nexus registry, and scans those exact images with Trivy. A release proceeds only after the HIGH/CRITICAL security gate passes; Django migrations run before backend, Celery, and frontend rollouts on the kubeadm cluster.

Three engineering problems made the project especially useful.

First, GitLab Runner lost access to the internal Nexus Docker endpoint on port 8083. Layer-by-layer checks showed that Nexus had failed to restore its proxy repositories during a DNS outage and later exposed the connector as HTTPS while the established CI endpoint was HTTP. I restored the existing architecture by correcting the Nexus connector and the runner’s narrow registry trust configuration rather than bypassing Nexus.

Second, uploaded product images needed to survive restarts and remain consistent across multiple backend and frontend Pods. I replaced ephemeral media storage with a dedicated 2 GiB Longhorn RWX volume. It uses two replicas distributed across worker-1 and worker-2, backend Pods mount `/app/media` read-write, and frontend Pods serve the same files from `/var/www/media` read-only.

Third, the security gate caught a real fixable HIGH issue: `CVE-2026-93990` in `libexpat 2.8.4-r0`. The pipeline correctly stopped before deployment. I patched the unprivileged NGINX runtime to `libexpat 2.8.5-r0`, kept the container running as UID 101, reran the unchanged Trivy policy, and deployed only after the scan passed.

Observability uses kube-prometheus-stack, Prometheus, Grafana, node-exporter, kube-state-metrics, and NGINX Ingress metrics discovered through a ServiceMonitor. The Kubernetes Cluster Monitoring dashboard is maintained as code.

This is deliberately described as a production-oriented lab, not a production-ready platform. Automated TLS, external secret management, centralized logging, tracing, production data HA, and a complete backup/DR lifecycle remain explicit roadmap items.

Code and documentation:
https://github.com/Mamaarsh/cloud-native-inventory-platform

#DevOps #Kubernetes #Docker #CICD #GitLabCI #DevSecOps #Prometheus #Grafana #CloudNative #Linux
