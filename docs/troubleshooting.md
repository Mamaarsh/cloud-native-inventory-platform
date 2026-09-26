# Troubleshooting

Start with the failing boundary: build, registry, scheduling, network, storage, scrape discovery, or query semantics. Avoid broad restarts or deleting persistent resources before collecting evidence.

## Nexus HTTP/HTTPS mismatch

**Symptoms:** `http: server gave HTTP response to HTTPS client`, TLS handshake errors, or `ImagePullBackOff` despite valid credentials.

**Checks:**

```bash
kubectl describe pod <pod> -n <namespace>
crictl pull <exact-image>   # run on the affected node
```

Confirm that the registry hostname, port, certificate, and containerd mirror/TLS configuration describe the same protocol. The lab moved monitoring references away from an IP/port combination that did not match node registry configuration to `nexus.local:8084`. Do not disable verification globally as a shortcut.

## Failed Helm monitoring release

**Symptoms:** Helm reports `failed`/`pending-*`, hooks time out, or pods remain unready.

```bash
helm status monitoring -n monitoring
helm history monitoring -n monitoring
kubectl get events -n monitoring --sort-by=.lastTimestamp
kubectl get pods -n monitoring -o wide
kubectl describe pod <pod> -n monitoring
```

Separate chart rendering errors from image pulls, PVC binding, scheduling, admission, and readiness. For the application `media` PVC, confirm the Longhorn RWX share-manager and NFS client path are healthy; verify `mount.nfs` and `nfs-common` on every node that may host backend/frontend pods; never replace it with one RWO volume while multiple backend/frontend pods mount it. Fix the underlying condition, run `helm upgrade --install` with the pinned chart/version and values, and avoid deleting PVCs unless data loss is explicitly accepted.

## Longhorn replica or capacity mismatch

**Symptoms:** PVCs stay Pending, Longhorn volumes are degraded, or replicas cannot schedule.

Compare the StorageClass replica setting, disk selector, eligible storage nodes, and available capacity. Longhorn also enforces physical free space: `storageAvailable` must remain above the configured `storage-minimal-available-percentage` of `storageMaximum`; sufficient `storageScheduled` headroom alone does not make a disk schedulable. Application media must use `longhorn-media` with `diskSelector: application`, two replicas, and a 2 GiB claim. Monitoring remains on `longhorn-monitoring` and `monitoring`-tagged disks:

```bash
kubectl get storageclass longhorn-media longhorn-monitoring -o yaml
kubectl -n longhorn-system get nodes.longhorn.io worker-1 worker-2 -o yaml
kubectl -n longhorn-system get settings.longhorn.io storage-minimal-available-percentage
kubectl get pvc media -n inventory
kubectl get pvc -n monitoring
kubectl describe pvc media -n inventory
kubectl describe pvc <pvc> -n monitoring
```

A `ReplicaSchedulingFailure` on a 5 GiB, three-replica media volume indicates the default `longhorn` policy is unsuitable for this two-storage-node lab. Before replacing a newly created media claim, prove no pod mounts or references it and confirm it contains no intentional data. Never delete PostgreSQL, Redis, or monitoring claims while repairing media storage. After replacement, require two scheduled replicas and non-faulted robustness before deploying workloads. For `DiskPressure`, calculate the exact gap from the condition message before cleanup. Inspect `df`, LVM free extents, `du -x`, journal usage, and caches first. Prefer supported journal/cache cleanup; do not lower the Longhorn threshold, prune container images blindly, or remove Longhorn files.

```text
Expected isolation: application media -> application-tagged default disks
Expected isolation: monitoring      -> monitoring-tagged disks
```

Filesystem capacity and disk I/O are different signals: a filesystem can have free space while latency/throughput is unhealthy, or be nearly full while currently idle. Use filesystem metrics for capacity and device I/O metrics/Longhorn health for performance.

## Prometheus cannot scrape node/control-plane ports

**Symptoms:** node, scheduler, controller-manager, etcd, or proxy targets are DOWN with timeout/refused errors.

Check the target URL in Prometheus, component bind/listen addresses, Service/Endpoints, and host firewall rules. kubeadm control-plane components may expose metrics only on loopback by default; changing bind addresses expands exposure and must be paired with firewall/network restrictions. Repository Helm values cannot fix host-level UFW rules or static pod flags.

## ServiceMonitor is not discovered

**Symptoms:** the ServiceMonitor exists but no target appears.

Verify all four joins:

```bash
kubectl get prometheus -n monitoring -o yaml
kubectl get servicemonitor nginx-ingress -n monitoring -o yaml
kubectl get service nginx-ingress-metrics -n nginx-ingress --show-labels
kubectl get endpoints nginx-ingress-metrics -n nginx-ingress -o yaml
```

The Prometheus selector must accept `release: monitoring`; the ServiceMonitor selector must match Service labels; its namespace selector must include `nginx-ingress`; and endpoint `port: metrics` must match the named Service port.

## Port 9113 exists but NGINX metrics are unavailable

**Symptoms:** Service/Endpoints exist but connections are refused or `/metrics` is empty.

A declared container port or Service does not start a listener. Confirm the controller args contain both `-enable-prometheus-metrics` and `-enable-latency-metrics`, then check controller logs and probe the pod/Service from inside the cluster. Apply the append-only JSON patch only when the flags are absent; repeated application duplicates args.

## Grafana shows no data, zero, or NaN

- **No data** usually means no matching series: target down, selector/label mismatch, wrong metric name, or range too short.
- **Zero** means a matching expression evaluated to zero. The dashboard intentionally converts a missing 5xx numerator to zero only when calculating error percentage.
- **NaN/Inf** commonly comes from dividing by zero. Use a meaningful denominator guard such as `clamp_min(..., 1)`, while still alerting separately on target health.

Inspect the query in Prometheus, remove aggregations temporarily, and review actual label names before editing the dashboard. Never turn every absent series into zero; that hides failed scraping.

## Compose frontend is unreachable

The production frontend listens on container port 8080. The tracked mapping is `${FRONTEND_PORT:-8080}:8080`.

```bash
docker compose config --quiet
docker compose ps
docker compose logs frontend backend
curl -I http://localhost:${FRONTEND_PORT:-8080}/
```

If an older container still publishes `80:80`, recreate only this project with `docker compose up --build -d`. Do not remove unrelated containers or volumes.

## Backend is live but not ready

`/api/health/live/` is process-only; `/api/health/ready/` queries PostgreSQL. Check the database container/pod, Secret keys, Service endpoint, NetworkPolicies, and migrations. Redis failure appears in `/api/health/dependencies/` but does not fail readiness by design.

## Migration Job blocks rollout

```bash
kubectl get jobs,pods -n inventory
kubectl describe job <migration-job> -n inventory
kubectl logs job/<migration-job> -n inventory --all-containers=true
```

The pipeline deliberately stops before a workload rollout when migration fails. Fix image, database, Secret, storage, or schema issues and run a new pipeline; do not manually mark the Job complete.
