# Kubernetes Monitoring

This directory is the declarative monitoring layer for the kubeadm lab. It contains the pinned Helm values, NGINX metrics discovery, and the Grafana dashboard source. See the full [observability guide](../../docs/observability.md) for metric semantics and PromQL.

## Verified repository configuration

| Setting | Tracked value |
|---|---|
| Helm repository alias | `nexus-prometheus` |
| Chart | `kube-prometheus-stack` |
| Chart version | `91.4.1` |
| Release / namespace | `monitoring` / `monitoring` |
| Prometheus retention | `15d` |
| Prometheus storage | `5Gi`, RWO, `longhorn-monitoring` |
| Grafana storage | `1Gi`, RWO, `longhorn-monitoring` |
| Dashboard sidecar label | `grafana_dashboard: "1"` |
| Runtime image registry | `nexus.local:8084/monitoring/...` |

Enabled components are Prometheus, Grafana, Alertmanager, Prometheus Operator, kube-state-metrics, and node-exporter. The values also pin mirrored images for supporting sidecars/webhook jobs. The StorageClass and its replica policy are external; the lab expects `longhorn-monitoring` to use two replicas across worker nodes, but verify that on the target cluster.

The last recorded lab setup reported a deployed release and healthy standard cluster targets. This repository's currently configured kubectl context may not be that lab, so those observations are not a substitute for current runtime checks.

## Files

```text
values-monitoring.yaml                 Helm values and mirrored image pins
nginx-ingress-metrics-json-patch.yaml Append-only metrics/latency flags
nginx-ingress-metrics-service.yaml    Private :9113 ClusterIP Service
nginx-ingress-servicemonitor.yaml     Prometheus Operator discovery
dashboards/                            Dashboard JSON and ConfigMap generator
```

## Install or upgrade the stack

The repository alias points to the internal chart mirror:

```bash
helm repo list
helm search repo nexus-prometheus/kube-prometheus-stack --versions

helm upgrade --install monitoring \
  nexus-prometheus/kube-prometheus-stack \
  --version 91.4.1 \
  --namespace monitoring \
  --create-namespace \
  -f k8s/monitoring/values-monitoring.yaml \
  --wait
```

The chart and image mirror require the lab Nexus. This monitoring install is not part of the public Compose quick start.

## Enable NGINX metrics

The F5 NGINX controller is installed outside this repository. Check its name, container order, labels, and existing args before using the lab-specific patch:

```bash
kubectl get deployment nginx-ingress -n nginx-ingress -o yaml
kubectl patch deployment nginx-ingress -n nginx-ingress \
  --type=json \
  --patch-file k8s/monitoring/nginx-ingress-metrics-json-patch.yaml
kubectl rollout status deployment/nginx-ingress -n nginx-ingress

kubectl apply -f k8s/monitoring/nginx-ingress-metrics-service.yaml
kubectl apply -f k8s/monitoring/nginx-ingress-servicemonitor.yaml
```

The patch appends `-enable-prometheus-metrics` and `-enable-latency-metrics` without replacing existing arguments. It is not idempotent when flags already exist, so inspect first. The LoadBalancer Service continues to expose only ports 80 and 443; metrics remain cluster-internal.

## Provision the dashboard

```bash
jq empty k8s/monitoring/dashboards/kubernetes-cluster-monitoring.json
kubectl kustomize k8s/monitoring/dashboards
kubectl apply -k k8s/monitoring/dashboards
```

Kustomize creates `grafana-dashboard-kubernetes-cluster-monitoring` with the sidecar label. Grafana loads **Kubernetes Cluster Monitoring** from the ConfigMap.

## Validate

```bash
helm template monitoring nexus-prometheus/kube-prometheus-stack \
  --version 91.4.1 \
  --namespace monitoring \
  -f k8s/monitoring/values-monitoring.yaml >/tmp/monitoring-rendered.yaml

kubectl get pods,pvc -n monitoring
kubectl get service,endpoints -n nginx-ingress nginx-ingress-metrics
kubectl get servicemonitor -n monitoring nginx-ingress
```

Check Prometheus **Status → Targets** for the NGINX ServiceMonitor and query:

```promql
nginx_ingress_nginx_http_requests_total
nginx_ingress_nginx_connections_active
nginx_ingress_controller_upstream_server_response_latency_ms_count
nginx_ingress_controller_nginx_last_reload_status
```

## Access

Services remain ClusterIP-only. Use temporary port-forwarding:

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090
```

Grafana credentials come from the Helm-managed Kubernetes Secret. Do not record or commit them.

## Boundaries

- Metrics Server is separate and not represented here.
- Alertmanager runs, but no custom notification receivers are configured in Git.
- There are no application/DB/broker exporters or custom PrometheusRule resources yet.
- Host firewall rules and kubeadm control-plane metric bind addresses are external cluster configuration.
- No public Grafana/Prometheus Ingress, centralized logging, distributed tracing, or monitoring backup workflow is implemented.
