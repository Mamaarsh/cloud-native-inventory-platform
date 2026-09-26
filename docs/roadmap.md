# Roadmap

The v1.0 repository demonstrates a coherent production-style lab. The following work is intentionally not presented as complete.

## Priority 1 — data and access safety

- Introduce external/encrypted secret management with rotation procedures.
- Add production TLS, secure proxy settings, secure cookies, and certificate automation.
- Implement PostgreSQL/Redis backup schedules, off-cluster copies, restore runbooks, and tested recovery objectives.
- Migrate the lab Longhorn RWX media volume to production object storage with an appropriate delivery, backup, and lifecycle design.

## Priority 2 — deeper observability

- Export Django request/business metrics and PostgreSQL/Redis/Celery metrics.
- Add reviewed PrometheusRule alerts and real Alertmanager notification routes.
- Add centralized structured logs and correlation identifiers; evaluate traces after logging is stable.
- Capacity-test the 5 GiB/15-day Prometheus configuration and size it from measured ingestion.

## Priority 3 — delivery and supply chain

- Add source/dependency scanning, secret detection, SBOM publication, image signing, and admission verification.
- Add frontend unit/component tests and browser-level end-to-end coverage.
- Package environment differences with Kustomize or Helm and validate manifests in CI.
- Replace force synchronization where organizational constraints allow a safer mirror strategy.

## Priority 4 — resilience and scale

- Evaluate managed or operator-backed PostgreSQL and Redis HA.
- Add topology spread constraints, PodDisruptionBudgets, autoscaling inputs, and controlled disruption tests.
- Run repeatable load, node-loss, dependency-failure, rollback, backup, and restore exercises.
- Define SLOs from measured behavior before assigning alert thresholds.

These are roadmap items, not claims about the current repository or lab.
