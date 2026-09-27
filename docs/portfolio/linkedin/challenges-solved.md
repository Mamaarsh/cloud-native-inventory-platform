# Challenges Solved

## 1. Restoring the GitLab Runner → Nexus 8083 path

**Symptoms:** Pipeline test jobs failed before their scripts ran. Docker reported `connection refused` for `http://192.168.122.1:8083/v2/` while the Nexus UI on 8081 remained reachable.

**Diagnosis:** Runner-side `nc` and `curl` isolated the failure to the registry listener. Nexus startup logs showed Docker proxy repositories had failed restoration during DNS resolution failures. After recovery, port 8083 returned TLS bytes even though CI intentionally used HTTP; protected repository metadata confirmed `docker-proxy` had `httpsPort: 8083` instead of `httpPort: 8083`. A direct pull then exposed the runner daemon's missing narrow insecure-registry entry.

**Root cause:** The proxy connector failed during a DNS outage and its persisted protocol did not match the established HTTP CI endpoint; the runner trust configuration also needed to include that endpoint.

**Fix:** Restored the existing repository, changed only `docker-proxy` from HTTPS 8083 to HTTP 8083, retained Nexus and the original topology, and configured Docker to trust the internal HTTP registry. Required base-image pulls and pipeline tests then worked.

**Lesson:** Test the path layer by layer—application health, TCP listener, Registry v2 response, connector protocol, daemon trust, then image pull. Changing image sources would have hidden rather than solved the platform defect.

## 2. Persistent product media with Longhorn RWX

**Symptoms:** Kubernetes media initially used ephemeral storage, so uploads could disappear with Pod replacement and could not be shared reliably across scaled backend/frontend replicas. The default three-replica policy also exceeded the practical capacity of the two storage-worker lab, and DiskPressure reduced schedulable space.

**Diagnosis:** PVC, Longhorn volume/replica state, disk tags, physical free-space thresholds, node conditions, NFS client availability, and share-manager behavior were inspected separately. The design needed RWX semantics rather than one RWO volume mounted by multiple Pods.

**Fix:** Added a dedicated `longhorn-media` StorageClass using `application`-tagged disks and two replicas, plus a 2 GiB RWX claim. Backend Pods mount `/app/media` read-write; frontend Pods mount `/var/www/media` read-only. NFS clients support the Longhorn share-manager path. DiskPressure was addressed through supported journal/cache cleanup rather than weakening Longhorn thresholds or deleting data.

**Result:** The volume is attached and healthy, replicas run on worker-1 and worker-2, `shareState` is running, and product thumbnails survive Pod restarts.

**Lesson:** Access mode, replica policy, physical capacity, node prerequisites, and application ownership are one storage design—not independent toggles.

## 3. Letting the Trivy gate stop a real release

**Symptoms:** `frontend-trivy` blocked the pipeline for `CVE-2026-93990`, a fixable HIGH vulnerability in `libexpat 2.8.4-r0` inside the Alpine-based unprivileged NGINX runtime.

**Diagnosis:** The immutable failed image was inspected directly, confirming the package came from the runtime layer rather than the React build output. Deployment correctly did not run because the security stage failed.

**Fix:** The Dockerfile temporarily switches to root during the build to run `apk upgrade --no-cache libexpat`, then explicitly returns to UID 101. The resulting image contained `libexpat 2.8.5-r0`, remained compatible with a read-only root filesystem, and preserved unprivileged NGINX behavior.

**Result:** The unchanged Trivy command reported zero HIGH/CRITICAL findings, the new commit-SHA image was published, and backend, Celery, and frontend rolled out successfully.

**Lesson:** A security gate is valuable when the response is to patch and revalidate the artifact—not suppress the CVE, relax severity, or deploy around the failed stage.
