# Kubernetes Deployment

## Prerequisites

The lab deployment expects:

- A kubeadm Kubernetes cluster with Calico (or equivalent NetworkPolicy enforcement)
- F5 NGINX Ingress Controller in `nginx-ingress`
- MetalLB and a suitable address pool
- Longhorn installed on `worker-1` and `worker-2`; default disks tagged `application` and monitoring disks tagged `monitoring`
- An NFS client on every node that may mount RWX media (`nfs-common` on Ubuntu)
- External StorageClasses `longhorn` and `longhorn-monitoring`; this repository defines `longhorn-media`
- Nexus DNS/reachability for `nexus.local:8083` and `nexus.local:8084`
- A GitLab Kubernetes Agent authorized by `.gitlab/agents/inventory-lab/config.yaml`
- DNS or a workstation hosts entry for `inventory.local`

The repository does not provision these dependencies.

## Resource inventory

| Resource | Namespace | Git owner | Normal reconciler |
|---|---|---|---|
| Namespace and Pod Security labels | `inventory` | `k8s/namespace.yaml` | Platform bootstrap |
| Workload ServiceAccounts | `inventory` | `k8s/serviceaccounts.yaml` | CI for application identities; bootstrap for stateful identities |
| ConfigMap and Secrets | `inventory` | ConfigMap/template only | Platform bootstrap |
| PostgreSQL and Redis | `inventory` | StatefulSets/Services | Platform bootstrap |
| Media StorageClass and RWX PVC | cluster-wide/`inventory` | `k8s/longhorn-media-storageclass.yaml`, `k8s/media-pvc.yaml` | Platform bootstrap |
| Backend, Celery, frontend | `inventory` | Deployments | GitLab CI with exact-SHA images |
| Application Services/Ingress/NetworkPolicies | `inventory` | Manifests | GitLab CI |
| NGINX metrics resources | `nginx-ingress`/`monitoring` | `k8s/monitoring` | Platform bootstrap |
| Monitoring stack | `monitoring` | Helm values | Helm/platform bootstrap |

## Longhorn media-storage bootstrap

`longhorn-media` isolates application uploads from monitoring storage. It selects only disks tagged `application`, uses two replicas, and must never select the `monitoring` disks. Disk tags are Longhorn node configuration, so inspect the exact disk keys before changing them:

```bash
kubectl config current-context
kubectl -n longhorn-system get nodes.longhorn.io worker-1 worker-2 -o yaml
ssh worker-1 'command -v mount.nfs && dpkg-query -W nfs-common'
ssh worker-2 'command -v mount.nfs && dpkg-query -W nfs-common'
```

On the verified lab topology, add `application` only to `default-disk-40b99aaa40454e73` on each worker while preserving every existing tag and leaving `monitoring-disk` tagged only `monitoring`. If the exact keys or current tags differ, stop and adjust deliberately instead of copying a patch blindly. With the verified empty default-disk tag arrays, the narrow patches are:

```bash
kubectl -n longhorn-system patch nodes.longhorn.io worker-1 --type=json \
  -p='[{"op":"add","path":"/spec/disks/default-disk-40b99aaa40454e73/tags","value":["application"]}]'
kubectl -n longhorn-system patch nodes.longhorn.io worker-2 --type=json \
  -p='[{"op":"add","path":"/spec/disks/default-disk-40b99aaa40454e73/tags","value":["application"]}]'
```

Re-read both Longhorn node objects and confirm the default disks have `application` while the monitoring disks still have `monitoring`. The repository intentionally does not automate cluster disk tagging.

## Bootstrap sequence

Review every placeholder before applying anything. The StorageClass must exist before its PVC, and the PVC must be `Bound` and healthy before application rollout:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccounts.yaml
kubectl apply -f k8s/backend-configmap.yaml
kubectl apply -f k8s/longhorn-media-storageclass.yaml

cp k8s/secrets.example.yaml k8s/inventory.secret.yaml
# Edit the ignored file with unique values, then:
kubectl apply -f k8s/inventory.secret.yaml

# Create the registry pull Secret without committing its value.
kubectl -n inventory create secret docker-registry nexus-registry-secret \
  --docker-server='<registry-host>' \
  --docker-username='<username>' \
  --docker-password='<password>'

kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-service.yaml
kubectl apply -f k8s/redis-statefulset.yaml
kubectl apply -f k8s/media-pvc.yaml
```

Passing a password on the command line can expose it through shell history or process inspection. Prefer a protected automation mechanism or an interactive/temporary input method in a real environment.

After the prerequisites are healthy, use the GitLab pipeline for migration and application rollout. Applying workload manifests directly will retain the deliberately invalid `ci-render-required` image tag.

## Runtime Secrets

The workloads reference three resources that must exist at runtime:

- `database-secret`: `DB_USER`, `DB_PASSWORD`
- `backend-secret`: `SECRET_KEY`
- `nexus-registry-secret`: Docker registry authentication

`k8s/secrets.example.yaml` is a non-secret template. There is no External Secrets, SOPS, Sealed Secrets, or Vault integration yet.

## Routing and ports

| Path | Kubernetes Service | Pod port |
|---|---|---:|
| `/` | `frontend:80` | 8080 |
| `/api` | `backend:8000` | 8000 |
| `/admin` | `backend:8000` | 8000 |
| `/static` | `backend:8000` | 8000 |
| `/media` | `frontend:80` | 8080 |

The external `k8s/nginx-ingress-service.yaml` exposes only HTTP/HTTPS. Port 9113 remains private through the separate ClusterIP metrics Service.

## Stateful services

PostgreSQL and Redis each use one replica and one 1 GiB RWO PVC. Redis enables AOF with `appendfsync everysec`. These settings favor a small lab footprint and do not provide application-level HA, backups, point-in-time recovery, or cross-cluster disaster recovery.

Product media uses the dedicated `longhorn-media` StorageClass and a 2 GiB RWX PVC. Longhorn serves this RWX volume through a share-manager, so `nfs-common` must be installed on every node that may run a backend or frontend pod. The class selects only `application`-tagged default disks and requests two replicas, keeping uploads away from `monitoring`-tagged disks. Apply the StorageClass before the PVC, then verify the claim is `Bound`, its Longhorn volume is schedulable and not faulted, and the RWX share-manager/NFS path is healthy before application rollout. Do not substitute one RWO claim while multiple pods are running.

## NetworkPolicy flows

Default ingress and egress are denied. Explicit policies allow:

```text
nginx-ingress → frontend:8080
nginx-ingress → backend:8000
backend/migration/Celery → PostgreSQL:5432
backend/Celery → Redis:6379
backend/migration/frontend/Celery → CoreDNS:53 UDP/TCP
```

The legacy `allow-backend-from-frontend` policy is an intentionally empty compatibility tombstone. It grants no traffic.

## Manifest validation

Client-side validation can parse built-in resource kinds without contacting the lab. ServiceMonitor requires its CRD for schema-aware server validation.

```bash
kubectl apply --dry-run=client --validate=false -f k8s/namespace.yaml
for file in k8s/*.yaml; do
  [ "$file" = "k8s/gitlab-agent-values.yaml" ] || \
    kubectl apply --dry-run=client --validate=false -f "$file"
done
kubectl kustomize k8s/monitoring/dashboards >/tmp/dashboard-configmap.yaml
```

Before a real release, use `--dry-run=server` against the intended lab context and inspect selectors/endpoints:

```bash
for file in k8s/*.yaml; do
  [ "$file" = "k8s/gitlab-agent-values.yaml" ] || \
    kubectl apply --dry-run=server -f "$file"
done
kubectl get pods,svc,endpoints,pvc -n inventory -o wide
kubectl get networkpolicy -n inventory
```

## Operational limitations

- Shared media depends on two eligible `application`-tagged disks, `nfs-common` on every mounting node, and a healthy Longhorn RWX/share-manager path; capacity, media backups, and lifecycle automation remain manual.
- Longhorn can reject a replica when physical free space falls below `storage-minimal-available-percentage`, even when `storageScheduled` appears sufficient; monitor both filesystem and Longhorn disk availability.
- Monitoring disks remain isolated through the `monitoring` selector and must not be used for application media.
- Object storage and CDN-style delivery are not implemented.
- The Ingress has no TLS stanza.
- Stateful services and workers have no PodDisruptionBudgets or topology spread constraints.
- PostgreSQL and Redis upgrades/backups are manual platform operations.
- Raw YAML is used for the application; there is no application Helm chart or environment overlay.
