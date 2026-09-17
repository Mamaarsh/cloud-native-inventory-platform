# Kubernetes Monitoring

This directory contains the production-like monitoring foundation deployed on the kubeadm Kubernetes cluster.

## Stack

* Chart: `nexus-prometheus/kube-prometheus-stack`
* Chart version: `91.4.1`
* Namespace: `monitoring`
* Prometheus Operator: Enabled
* Grafana: Enabled
* Alertmanager: Enabled
* kube-state-metrics: Enabled
* node-exporter: Enabled

## Registry and Offline Image Strategy

All monitoring images are mirrored through the internal Nexus Docker registry.

Registry:

```
nexus.local:8084/monitoring/
```

The original deployment attempted to use:

```
192.168.122.1:8084
```

which caused image pull failures because Nexus serves HTTPS while containerd was configured for HTTP access.

The monitoring values file was updated so every rendered runtime image uses the internal Nexus mirror.

Verified:

* Containerd image pulls succeed from Kubernetes nodes.
* No running monitoring workload references public registries.
* No monitoring workload references `192.168.122.1:8084`.

Public registries are not required during monitoring deployment.

## Storage Configuration

Monitoring workloads use dedicated Longhorn storage.

StorageClass:

```
longhorn-monitoring
```

Configuration:

### Prometheus

* Storage size: `5Gi`
* Access mode: `ReadWriteOnce`
* Retention: `15 days`
* Replica count: `2`

### Grafana

* Storage size: `1Gi`
* Access mode: `ReadWriteOnce`
* Replica count: `2`

The dedicated Longhorn storage class was created because the original configuration expected three replicas while only two storage nodes were available.

Monitoring volumes are currently:

```
attached
healthy
```

Existing application volumes such as PostgreSQL and Redis were not modified.

## Deployment Status

Monitoring was successfully deployed using:

```bash
helm upgrade --install monitoring \
  nexus-prometheus/kube-prometheus-stack \
  --version 91.4.1 \
  --namespace monitoring \
  --create-namespace \
  -f values-monitoring.yaml \
  --wait
```

Current Helm status:

```
STATUS: deployed
REVISION: 1
```

## Running Components

The following workloads are healthy:

* Prometheus
* Grafana
* Alertmanager
* Prometheus Operator
* kube-state-metrics
* node-exporter

Validation:

```bash
kubectl get pods -n monitoring
```

Expected result:

* All monitoring pods are `Running`
* All containers are `Ready`

## Prometheus Targets

Prometheus successfully discovers and scrapes cluster metrics.

Current target health:

```
28/28 targets UP
```

Collected metrics include:

* Kubernetes API metrics
* kubelet metrics
* node metrics
* kube-state-metrics
* node-exporter metrics
* controller-manager metrics
* scheduler metrics
* etcd metrics

## Kubernetes Metrics Endpoint Configuration

Several kubeadm components originally exposed metrics only through loopback interfaces.

Updated components:

* kube-controller-manager
* kube-scheduler
* etcd
* kube-proxy

Prometheus scraping access was also allowed through firewall rules for required metrics ports.

## Access

Monitoring services are currently exposed internally using ClusterIP.

Temporary access:

Grafana:

```bash
kubectl port-forward svc/monitoring-grafana \
-n monitoring 3000:80
```

Open:

```
http://localhost:3000
```

Prometheus:

```bash
kubectl port-forward svc/monitoring-kube-prometheus-prometheus \
-n monitoring 9090:9090
```

Open:

```
http://localhost:9090
```

## Validation Commands

Helm:

```bash
helm list -n monitoring
helm status monitoring -n monitoring
```

Kubernetes:

```bash
kubectl get all -n monitoring
kubectl get pvc -n monitoring
```

Prometheus:

```bash
kubectl get servicemonitor -n monitoring
kubectl get prometheusrules -n monitoring
```

## Remaining Improvements

The monitoring foundation is deployed successfully.

Future improvements:

* Add Ingress access for Grafana and Prometheus.
* Install Metrics Server for `kubectl top`.
* Create custom Grafana dashboards.
* Build PromQL alert rules.
* Monitor application workloads such as Django, PostgreSQL and Redis.
* Review existing degraded Longhorn application volumes separately.

## Backup

Before recovery changes, the original values file was backed up:

```
values-monitoring.yaml.bak-20260918-pre-recovery
```

Additional Kubernetes metric configuration backups:

```
monitoring-backups/20260918-kube-metrics/
```