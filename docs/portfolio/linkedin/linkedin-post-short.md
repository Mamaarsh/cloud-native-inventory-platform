# Short LinkedIn Post

I built **Cloud Native Inventory Platform** to connect DevOps tools around a real workload instead of learning them in isolation.

The Django/React application uses PostgreSQL, Redis, and Celery for inventory, orders, audit history, and product images. GitHub triggers a GitLab CI pipeline that runs 246 backend tests, frontend lint/build checks, creates commit-SHA images through Nexus, blocks fixable HIGH/CRITICAL findings with Trivy, runs migrations, and deploys to a kubeadm Kubernetes cluster.

The most useful work came from real failures: restoring the GitLab Runner → Nexus HTTP registry path, designing a two-replica Longhorn RWX volume shared safely by backend and frontend Pods, and fixing `CVE-2026-93990` after Trivy correctly stopped deployment. The patched image passed the unchanged gate and was then released.

Prometheus, Grafana, node-exporter, kube-state-metrics, and NGINX metrics provide the observability layer. It is a production-oriented lab with its remaining TLS, secrets, logging, tracing, HA, and DR gaps documented openly.

https://github.com/Mamaarsh/cloud-native-inventory-platform

#DevOps #Kubernetes #GitLabCI #DevSecOps #Prometheus #CloudNative
