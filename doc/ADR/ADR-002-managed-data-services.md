# ADR-002: Cloud SQL and Memorystore as Managed Data Services

**Date:** 2026-05-21  
**Status:** Accepted  
**Decided by:** Lakshman (architect)  
**Documented by:** Alberto Hernandez

---

## Context

IBM ContextForge requires two data backends:

1. **PostgreSQL** — stores Config Registry data (virtual server definitions, MCP proxy registrations, OAuth 2.0 client records).
2. **Redis** — used as a cache layer by the AI Gateway (session state, rate limit counters, tool response caching).

Two provisioning approaches were evaluated:

- **Path A — In-cluster provisioning:** Deploy PostgreSQL as a StatefulSet with a PersistentVolumeClaim and Redis as a Deployment or StatefulSet inside the GKE cluster.
- **Path B — Managed services:** Use Google Cloud SQL (PostgreSQL 15) and Google Cloud Memorystore (Redis 7) as GCP-managed resources external to the cluster.

---

## Decision

**Use Google Cloud SQL (PostgreSQL 15) and Google Cloud Memorystore (Redis 7) as the data backends for ContextForge.**

In-cluster StatefulSets with PersistentVolumeClaims are explicitly excluded for Phase 1.

---

## Rationale

| Factor | In-cluster (StatefulSet + PVC) | Managed (Cloud SQL + Memorystore) |
|---|---|---|
| Backup and restore | Manual — requires operator runbook | Automated point-in-time recovery (Cloud SQL) |
| High availability | Manual replication configuration | Built-in HA configuration option |
| Security patching | Manual OS and engine upgrades | GCP-managed |
| Operational burden | High — team must own storage operations | Low — GCP SLA covers availability |
| Network connectivity | Pod-to-pod via ClusterIP | Private IP via VPC peering within GKE |
| Persistent volume management | Requires StorageClass, disk provisioning | Not applicable |
| Phase 1 team capacity | Insufficient for in-cluster data ops | Matches available capacity |

The guiding constraint from Lakshman's architecture direction: the team is building a gateway layer, not a storage platform. The data backends must be delegated to managed services to keep the operational surface minimal.

---

## Consequences

1. **Cloud SQL** is provisioned with `gcloud sql instances create` in `scripts/gke_provision.sh`. Tier defaults to `db-f1-micro` per Assumption A3 in `doc/Specify.md`. Tier is confirmed when Q6 is resolved.

2. **Memorystore** is provisioned with `gcloud redis instances create` in `scripts/gke_provision.sh`. Size defaults to 1 GB, tier BASIC.

3. The ContextForge pod connects to Cloud SQL via its **private IP** within the GKE VPC. No Cloud SQL Auth Proxy sidecar is required in Phase 1. The `CLOUDSQL_CONNECTION_STRING` environment variable carries the private IP connection string.

4. The ContextForge pod connects to Memorystore via its **private IP** within the GKE VPC. The `REDIS_HOST` environment variable carries this IP; it is populated after provisioning.

5. All connection credentials are stored in Kubernetes Secrets (`contextforge-db-credentials`, `contextforge-redis-credentials`), created by `scripts/gke_deploy.sh`. The secret shape is documented in `k8s/secrets.example.yaml`.

6. Cloud SQL Auth Proxy is not deployed in Phase 1. If the security posture requires it (e.g., when Q5 Cloud SQL Proxy is mandated), this ADR must be updated and the deployment manifest extended with a sidecar container.

---

## Unresolved Items

| Item | Resolution |
|---|---|
| Cloud SQL tier confirmation | Pending Q6 (node / capacity approval from Lakshman). Default: `db-f1-micro` |
| Memorystore IP availability after provision | `gcloud redis instances describe` outputs the IP; captured in `gke_provision.sh` post-provision output |
| Cloud SQL Auth Proxy requirement | Pending Q5 (GCP Secret Manager / security posture confirmation from Chakri) |

---

## Evidence

- ADR-001: `doc/ADR/ADR-001-gke-over-cloud-run.md` — establishes GKE as the deployment target and references this ADR for data service decisions
- Specification: `doc/Specify.md` Section 15, Assumptions A2 and A3
- Plan ticket: `doc/Plan.md`, EPIC-MF-E04, MF-E04-T01
