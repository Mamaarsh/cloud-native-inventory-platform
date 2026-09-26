# Observability

## Implemented stack

`k8s/monitoring/values-monitoring.yaml` targets `nexus-prometheus/kube-prometheus-stack` chart `91.4.1` in namespace `monitoring`, release name `monitoring`. It enables:

- Prometheus Operator and Prometheus
- Grafana with dashboard/datasource sidecars
- Alertmanager
- kube-state-metrics
- Prometheus node-exporter
- The chart's Kubernetes control-plane and kubelet/cAdvisor monitors

Images are pinned in the values file and mirrored under `nexus.local:8084/monitoring/`. Prometheus retains 15 days on a 5 GiB PVC; Grafana requests 1 GiB. Both use the externally provisioned `longhorn-monitoring` StorageClass. The repository does not define that StorageClass; the lab description states it uses two Longhorn replicas across workers, which must be rechecked on the target cluster.

Alertmanager is installed, but this repository does not configure custom receivers or prove email/chat/pager delivery. Metrics Server is not installed by these manifests. Prometheus stores time series; Metrics Server serves the Kubernetes resource metrics API used by `kubectl top` and autoscalers.

## What Prometheus scrapes

The stack is configured to discover standard cluster targets including the API server, kubelet/cAdvisor, kube-state-metrics, node-exporter, and enabled control-plane endpoints. Lab-specific bind addresses and firewall access are external bootstrap work. NGINX uses an explicit ServiceMonitor tracked here.

### NGINX discovery chain

```text
F5 NGINX controller
  -enable-prometheus-metrics
  -enable-latency-metrics
  listens on :9113/metrics
       ↓
nginx-ingress-metrics Service (ClusterIP, port name: metrics)
       ↓
nginx-ingress ServiceMonitor (label: release=monitoring)
       ↓
Prometheus Operator generates scrape configuration
       ↓
Prometheus stores series → Grafana queries them
```

The controller installation is not owned by this repository. `nginx-ingress-metrics-json-patch.yaml` appends flags to the existing controller rather than inventing a duplicate Deployment. It assumes Deployment `nginx-ingress` and controller container index `0`; inspect those facts first:

```bash
kubectl -n nginx-ingress get deployment nginx-ingress \
  -o jsonpath='{.spec.template.spec.containers[0].name}{"\n"}{.spec.template.spec.containers[0].args}{"\n"}'

kubectl -n nginx-ingress patch deployment nginx-ingress \
  --type=json \
  --patch-file k8s/monitoring/nginx-ingress-metrics-json-patch.yaml

kubectl apply -f k8s/monitoring/nginx-ingress-metrics-service.yaml
kubectl apply -f k8s/monitoring/nginx-ingress-servicemonitor.yaml
```

Do not reapply the JSON patch if both flags are already present; JSON Patch appends list entries. Confirm the rollout and endpoint without exposing it through the public LoadBalancer:

```bash
kubectl rollout status deployment/nginx-ingress -n nginx-ingress
kubectl get service nginx-ingress-metrics -n nginx-ingress
kubectl get servicemonitor nginx-ingress -n monitoring -o yaml
```

## Metric types and PromQL

A **Gauge** can rise or fall directly. CPU/memory capacity, active connections, and reload status are gauges; graph their value or aggregate it with `sum`, `avg`, `min`, or `max` as appropriate.

A **Counter** only increases until a process restarts. Request totals, accepted connections, CPU seconds, and restart totals are counters. Use `rate(counter[$__rate_interval])` for a per-second trend. Use `increase(counter[window])` when the question is “how many during this window?” Grafana's `$__rate_interval` adapts to panel range and scrape interval.

A **Histogram** emits:

- `_bucket`: cumulative observation counts by upper bound `le`
- `_sum`: sum of observed values
- `_count`: number of observations

Average latency is `rate(_sum) / rate(_count)`. Percentiles use `histogram_quantile()` over rates of buckets while preserving `le`. p50 is the median; p95 and p99 expose progressively slower tail behavior. They are estimates based on bucket boundaries, not exact stored request samples.

## Representative queries

Node CPU usage percent:

```promql
100 - (
  avg by (instance) (
    rate(node_cpu_seconds_total{mode="idle"}[$__rate_interval])
  ) * 100
)
```

Node memory usage percent:

```promql
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
```

Top pod CPU:

```promql
topk(5,
  sum by (namespace, pod) (
    rate(container_cpu_usage_seconds_total{
      container!="", container!="POD", pod!=""
    }[$__rate_interval])
  )
)
```

NGINX request rate:

```promql
sum(rate(nginx_ingress_nginx_http_requests_total[$__rate_interval]))
```

NGINX average upstream latency in milliseconds:

```promql
sum by (upstream) (
  rate(nginx_ingress_controller_upstream_server_response_latency_ms_sum[$__rate_interval])
)
/
clamp_min(
  sum by (upstream) (
    rate(nginx_ingress_controller_upstream_server_response_latency_ms_count[$__rate_interval])
  ),
  1
)
```

p95 upstream latency:

```promql
histogram_quantile(
  0.95,
  sum by (le, upstream) (
    rate(nginx_ingress_controller_upstream_server_response_latency_ms_bucket[$__rate_interval])
  )
)
```

Zero-safe 5xx percentage:

```promql
100 * (
  sum(rate(nginx_ingress_nginx_http_requests_total{status=~"5.."}[$__rate_interval]))
  or vector(0)
)
/
clamp_min(
  (sum(rate(nginx_ingress_nginx_http_requests_total[$__rate_interval])) or vector(0)),
  1
)
```

`or vector(0)` turns a missing 5xx series into zero. It must not be used indiscriminately: a completely missing scrape target is operationally different from a healthy target reporting no errors.

## Dashboard as code

The source dashboard is [kubernetes-cluster-monitoring.json](../k8s/monitoring/dashboards/kubernetes-cluster-monitoring.json). It covers:

- Node CPU, memory, root filesystem, receive, and transmit utilization
- Top pods by CPU/memory, namespace pod counts, and restart activity
- NGINX requests, active/accepted connections, average and p50/p95/p99 upstream latency
- Request rates by status, zero-safe 5xx percentage, and controller reload status

Grafana's sidecar selector is explicit in the Helm values: `grafana_dashboard=1`. Kustomize generates the matching ConfigMap without duplicating dashboard JSON:

```bash
jq empty k8s/monitoring/dashboards/kubernetes-cluster-monitoring.json
kubectl kustomize k8s/monitoring/dashboards
kubectl apply -k k8s/monitoring/dashboards
```

## Installation and validation

```bash
helm upgrade --install monitoring \
  nexus-prometheus/kube-prometheus-stack \
  --version 91.4.1 \
  --namespace monitoring \
  --create-namespace \
  -f k8s/monitoring/values-monitoring.yaml \
  --wait

kubectl get pods,pvc -n monitoring
kubectl get servicemonitor -n monitoring
kubectl get endpoints nginx-ingress-metrics -n nginx-ingress
```

Temporary access remains ClusterIP-only:

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090
```

In Prometheus, verify the ServiceMonitor target is UP and run the exact metric names before judging a blank dashboard. In Grafana, select the provisioned Prometheus datasource and confirm the dashboard appears under sidecar-provisioned dashboards.

## Known limitations

- No Django, PostgreSQL, Redis, Celery, or business KPI exporter is configured.
- No custom PrometheusRule or custom Alertmanager notification receiver is tracked.
- Live PromQL and target validation requires the actual kubeadm lab; a different local context is not evidence.
- Prometheus storage is 5 GiB with 15-day retention; actual usable history also depends on ingestion volume.
- Dashboard NGINX panels depend on F5 metric labels and latency metrics being enabled; validate labels after controller upgrades.
- Logs and traces are not centralized.
