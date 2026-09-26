# CI/CD

## Source handoff

A push to GitHub `main` starts `.github/workflows/gitlab-trigger.yml`. The workflow checks out full history, force-syncs `main` to the Hamgit/GitLab mirror using `HAMGIT_USERNAME` and `HAMGIT_TOKEN`, then calls the GitLab trigger API with `GITLAB_TRIGGER_TOKEN`. These values are GitHub Actions Secrets and are not stored in the repository.

GitLab accepts only pipelines whose source is `trigger`. Direct pushes to the mirror therefore do not execute `.gitlab-ci.yml` under the current workflow rules.

## Pipeline stages and jobs

The exact stage order is:

```text
test → build → security → deploy → cleanup
```

### Test

- `backend-test`: installs Python requirements, runs `manage.py check`, collects static assets, and executes the complete Django suite against a PostgreSQL 16 service.
- `frontend-test`: runs `npm ci`, ESLint, TypeScript compilation, and a Vite production build.
- `kubernetes-agent-test`: selects the GitLab Agent context, confirms the `inventory` namespace is readable, verifies deployment patch permission, and requires Secret read access to be denied.

### Build

- `backend-build` builds the backend using the lab Nexus Python base.
- `frontend-build` uses Nexus-proxied Node and `nginxinc/nginx-unprivileged` bases.
- Both jobs authenticate to the hosted registry and publish `$CI_COMMIT_SHORT_SHA` plus `latest`.

The Dockerfiles themselves default to public images for portability. Explicit CI build arguments retain the offline/internal Nexus path.

### Security

`backend-trivy` and `frontend-trivy` scan the exact commit-SHA images. `--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1` blocks the release when a fixable HIGH/CRITICAL OS or package finding is detected. This is image scanning, not a claim of SAST, DAST, SBOM signing, or dependency-update automation.

### Deploy

`deploy-kubernetes` uses `resource_group: inventory-kubernetes` and is non-interruptible so releases cannot mutate the namespace concurrently. It then:

1. Best-effort checks whether the pipeline commit is still the default-branch head. A confirmed stale release exits before mutation; an API/parse failure continues with a warning.
2. Validates commit and numeric pipeline/job identifiers.
3. Reconciles ServiceAccounts, Services, Ingress, and NetworkPolicies.
4. Renders an exact backend image and a unique migration Job name into a temporary directory.
5. Creates the Job, waits up to 660 seconds, and prints description/logs on failure.
6. Renders exact-SHA backend, Celery, and frontend Deployments.
7. Applies and waits for each rollout in that order.

The pipeline does not apply namespace bootstrap, ConfigMap, Secrets, PostgreSQL, Redis, NGINX controller resources, monitoring, or GitLab Agent installation.

### Cleanup

`cleanup` is manual. It first requires the protected Nexus container label, then prunes stopped containers, dangling/old unused images, and old build cache from the runner after 168 hours. It does not delete running containers, Kubernetes resources, or Nexus artifacts and does not prove a registry retention policy.

## Required CI variables

The GitLab configuration expects `NEXUS_REGISTRY`, `NEXUS_USERNAME`, and `NEXUS_PASSWORD` as protected/masked CI variables, plus GitLab-provided variables and the Agent-injected `KUBECONFIG`. Do not place their values in YAML.

## Rollback model

Kubernetes Deployment revisions are retained (`revisionHistoryLimit: 5`), but schema migrations can be forward-only. A safe rollback must confirm database compatibility, then deploy a previously scanned immutable image. Automated migration rollback is not implemented.

## Validation

```bash
# Syntax/structure inspection
sed -n '1,420p' .gitlab-ci.yml

# GitLab's CI Lint should be used before merging pipeline changes.
# The repository cannot reproduce runner tags, Nexus, Agent, or cluster access locally.
```
