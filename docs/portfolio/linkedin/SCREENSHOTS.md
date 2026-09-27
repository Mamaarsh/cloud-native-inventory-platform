# LinkedIn Screenshot Evidence

The five primary screenshots are captured, sanitized, and integrated into the main README. They remain authentic operational evidence: processing was limited to cropping presentation noise, proportional resizing, removing image metadata, and combining the two real Nexus captures.

## Completed primary evidence

| Evidence | Canonical file | Verified content |
|---|---|---|
| Application | [`application-dashboard.png`](../../images/linkedin/application-dashboard.png) | Stockline Product Registry, Printer product, uploaded thumbnail, status, and application navigation |
| CI/CD | [`gitlab-pipeline.png`](../../images/linkedin/gitlab-pipeline.png) | Pipeline `#2097140`, commit `c7fcdcc1`, Passed, test/build/security/deploy jobs, and manual cleanup |
| Kubernetes | [`kubernetes-workloads.png`](../../images/linkedin/kubernetes-workloads.png) | Three Ready nodes; backend, frontend, Celery, PostgreSQL, and Redis Running; `inventory.local` Ingress |
| Observability | [`grafana-cluster-monitoring.png`](../../images/linkedin/grafana-cluster-monitoring.png) | Grafana Kubernetes compute dashboard with populated CPU/memory utilization, requests/limits, and namespace tables |
| Registry | [`nexus-repository.png`](../../images/linkedin/nexus-repository.png) | Real `inventory/backend` and `inventory/frontend` manifests for `c7fcdcc1` in `docker-hosted` |

The reproducible Kubernetes/Longhorn terminal reference remains available in [`kubernetes-workloads.txt`](kubernetes-workloads.txt).

## Sanitization performed

- Removed browser chrome/bookmarks from the final application presentation by selecting the viewport-only source.
- Cropped excess lower space from the GitLab pipeline while retaining every required stage and job.
- Cropped Nexus panels before blob-reference, uploader, and uploader-IP fields, then combined backend-left/frontend-right with a neutral gutter.
- Preserved terminal output, Grafana metric values, pipeline results, component names, and commit tags without retouching.
- Removed PNG metadata and retained aspect ratios.

## Publication safety checklist

Before reusing or replacing any screenshot:

1. Confirm it reflects the intended commit or a later documented release.
2. Exclude passwords, tokens, cookies, CI variables, authorization headers, private keys, account menus, unrelated tabs, and browser history.
3. Do not edit health states, metric values, job results, terminal output, component names, or image tags.
4. Keep text readable at LinkedIn mobile width.
5. Preserve the registry-role distinction: dependency proxy access and hosted application images are separate Nexus roles.

## Optional evidence not yet captured

### `trivy-security-scan.png`

Capture the successful `frontend-trivy` job for `c7fcdcc1`. Show the image tag, `--severity HIGH,CRITICAL`, `--ignore-unfixed`, and zero-finding summary. Exclude CI variables, tokens, and credentials.

### `longhorn-media.png`

Capture Longhorn's volume view for `pvc-b0c341dd-063b-4d12-b5a3-f04f752ca145`. Show Attached, Healthy, two replicas on worker-1/worker-2, and the running RWX share-manager. Exclude backup credentials and unrelated volumes.

Terminal alternative:

```bash
kubectl get pvc media -n inventory
kubectl -n longhorn-system get volumes.longhorn.io \
  pvc-b0c341dd-063b-4d12-b5a3-f04f752ca145 \
  -o custom-columns=VOLUME:.metadata.name,STATE:.status.state,HEALTH:.status.robustness,REPLICAS:.spec.numberOfReplicas,SHARE:.status.shareState
kubectl -n longhorn-system get replicas.longhorn.io \
  -l longhornvolume=pvc-b0c341dd-063b-4d12-b5a3-f04f752ca145 \
  -o custom-columns=REPLICA:.metadata.name,NODE:.spec.nodeID,STATE:.status.currentState
```
