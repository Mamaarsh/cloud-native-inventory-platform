# LinkedIn Screenshot Plan

No browser screenshot is committed yet. The application, GitLab, Grafana, and Nexus require authenticated sessions that were not available to the documentation pass; creating substitutes would be fake evidence. Capture the following from the real interfaces, then place the sanitized files in `docs/images/linkedin/`.

Use a 16:9 crop (recommended 1600×900 or 1920×1080), 100% browser zoom, and a consistent light or dark theme. Hide bookmarks, unrelated tabs, browser profiles, notifications, usernames where unnecessary, tokens, internal credentials, CI variables, and terminal history.

## 1. `application-dashboard.png`

- **Open:** `http://inventory.local:30632/products` from a machine where that lab address resolves. If routing exposes the standard Ingress port instead, use the verified local URL for `inventory.local`.
- **Prepare:** Sign in with a non-sensitive demo account. Open **Product Registry** and ensure the Printer product with its real uploaded thumbnail is visible.
- **Must show:** application navigation, Product Registry heading, Printer row/card, uploaded thumbnail, SKU/price/status context, and enough surrounding UI to demonstrate a working application.
- **Must not show:** login credentials, JWTs, developer tools, password-manager overlays, browser profile, unrelated tabs, or personal notifications.
- **Crop:** application viewport only; keep the product thumbnail near the visual center.

## 2. `gitlab-pipeline.png`

- **Open:** Hamgit project → **Build → Pipelines** → the successful pipeline for commit `c7fcdcc1` → pipeline graph.
- **Must show:** commit `c7fcdcc1`, green `test`, `build`, `security`, and `deploy` jobs, plus the manual/available `cleanup` job. Expand the graph enough to show `backend-test`, `frontend-test`, `kubernetes-agent-test`, both build jobs, both Trivy jobs, and `deploy-kubernetes`.
- **Must not show:** Settings/CI Variables, trigger tokens, runner tokens, job variables, repository credentials, or account menus.
- **Crop:** pipeline header and complete stage graph; exclude browser chrome where practical.

## 3. `kubernetes-workloads.png`

- **Capture from:** a clean terminal connected to `control-plane`.
- **Verified reference output:** [`kubernetes-workloads.txt`](kubernetes-workloads.txt). Re-run the commands before capture so the screenshot shows current state rather than copying old output.
- **Exact commands:**

  ```bash
  clear
  printf '=== Kubernetes nodes ===\n'
  kubectl get nodes
  printf '\n=== Inventory workloads ===\n'
  kubectl get deployments,statefulsets -n inventory
  printf '\n=== Inventory pods ===\n'
  kubectl get pods -n inventory -o wide
  ```

- **Must show:** all three nodes Ready; backend 2/2; frontend 2/2; Celery 1/1; PostgreSQL and Redis 1/1; every pod Running.
- **Must not show:** kubeconfig contents, shell history, environment variables, Secrets, tokens, or unrelated commands.
- **Crop:** terminal output from the first heading through the last pod; 16:9 landscape.

## 4. `grafana-cluster-monitoring.png`

- **Open:** establish `kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80`, then open `http://127.0.0.1:3000` → **Dashboards** → **Kubernetes Cluster Monitoring**.
- **Time range:** last 30 minutes or last 1 hour while application traffic exists.
- **Must show:** dashboard title and populated Node CPU, Node Memory, Pods, NGINX request rate, HTTP status, and latency panels. Generate a few safe application requests first if NGINX traffic panels are empty.
- **Must not show:** Grafana password, login form, datasource credentials, alert contact points, user menu, or unrelated dashboards.
- **Crop:** dashboard title plus the strongest populated panels; omit empty lower rows.

## 5. `nexus-repository.png`

- **Open:** `http://192.168.122.1:8081` → **Browse** → the hosted Docker repository used for application images.
- **Must show:** both `inventory/backend` and `inventory/frontend`, with the `c7fcdcc1` tag visible. A second crop may be used if Nexus cannot display both paths clearly on one screen.
- **Must not show:** administration/security pages, users, roles, repository credentials, bearer tokens, or browser developer tools.
- **Crop:** repository browser, component names, and commit-SHA tag.

## 6. Optional `trivy-security-scan.png`

- **Open:** successful pipeline for `c7fcdcc1` → `frontend-trivy` job.
- **Must show:** image tag `c7fcdcc1`, `--severity HIGH,CRITICAL`, `--ignore-unfixed`, and the successful zero-finding summary. It is useful to retain a separate private screenshot of the earlier blocked `CVE-2026-93990` job for interviews, but do not expose credentials or job variables.
- **Crop:** scan command and final report only.

## 7. Optional `longhorn-media.png`

- **Preferred UI:** Longhorn → **Volume** → `pvc-b0c341dd-063b-4d12-b5a3-f04f752ca145`.
- **Must show:** Attached, Healthy, two replicas, share-manager/RWX state, and replicas on worker-1 and worker-2.
- **Terminal alternative:**

  ```bash
  clear
  kubectl get pvc media -n inventory
  kubectl -n longhorn-system get volumes.longhorn.io \
    pvc-b0c341dd-063b-4d12-b5a3-f04f752ca145 \
    -o custom-columns=VOLUME:.metadata.name,STATE:.status.state,HEALTH:.status.robustness,REPLICAS:.spec.numberOfReplicas,SHARE:.status.shareState
  kubectl -n longhorn-system get replicas.longhorn.io \
    -l longhornvolume=pvc-b0c341dd-063b-4d12-b5a3-f04f752ca145 \
    -o custom-columns=REPLICA:.metadata.name,NODE:.spec.nodeID,STATE:.status.currentState
  ```

- **Must not show:** backup credentials, storage-node shell history, unrelated volumes, or Secret data.

## Final review before publishing

1. Confirm every screenshot reflects commit `c7fcdcc1` or a later documented commit.
2. Redact only sensitive information; do not alter health, status, or result data.
3. Check each image at LinkedIn mobile width for readable text.
4. Add only real screenshots to Git, then replace the README screenshot comments with image links.
