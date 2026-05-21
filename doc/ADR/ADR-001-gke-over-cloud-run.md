# ADR-001: GKE over Cloud Run as the ContextForge Deployment Target

**Date:** 2026-05-21  
**Status:** Accepted  
**Decided by:** Lakshman (architect), confirmed by team in daily standup 2026-05-20  
**Documented by:** Alberto Hernandez

---

## Context

The team attempted an initial deployment of IBM ContextForge on Google Cloud Run as a faster path to a working environment. This deployment was performed by Kashyap. The resulting deployment was not functional — the ContextForge AI Gateway was not reachable from outside the container.

Two root causes were identified by Lakshman during the review of the Cloud Run deployment:

1. **Container port exposure not enabled.** ContextForge requires a specific configuration setting to be set to `true` for its AI Gateway to bind to and expose its container port. This setting was not applied in the Cloud Run deployment. Without it, the gateway process runs but does not listen on the expected port from the container's perspective, making it unreachable through Cloud Run's proxy.

2. **Required Google Cloud API not activated.** A specific GCP API (the exact API is to be confirmed when the IBM ContextForge documentation is fully reviewed — Q1, Q3) must be enabled in the GCP project before the Cloud Run deployment can function correctly. This step was skipped, preventing the registry component from initialising.

Kashyap's account during the standup: *"I added multiple tools, I created some virtual servers, which was not possible in yesterday's demo... I just wanted to push this into the grid cloud that we have."*

Lakshman's diagnosis: *"When I reviewed what Kashyap deployed onto the Google Cloud Run, it just installed within the Cloud Run, right? But not as a container port and exposing. Exposing — there is a setting that has to be enabled. We ran through the details of what settings were missed."*

The team then evaluated two paths forward:

- **Path A:** Resolve the two Cloud Run issues and continue with Cloud Run.
- **Path B:** Move to GKE as the deployment target, which provides standard Kubernetes networking without Cloud Run's port exposure constraints.

---

## Decision

**Use GKE (Google Kubernetes Engine) as the deployment target for ContextForge.**

Cloud Run is explicitly excluded as a deployment target for Phase 1. GKE is the only valid deployment target.

---

## Rationale

| Factor | Cloud Run | GKE |
|---|---|---|
| Port exposure | Requires a non-default flag that was missed | Standard Kubernetes Service and Ingress |
| Database connectivity | Requires Cloud SQL Auth Proxy sidecar or connector | Direct TCP via private IP |
| Redis connectivity | Requires VPC connector | Direct TCP via private IP |
| Persistent configuration | Stateless — configuration must be external | ConfigMap + Secret natively managed |
| Production path | Not a standard pattern for stateful gateways | Kubernetes is the team's production target |
| GCP API requirements | Additional API activation step (was missed) | Standard GKE APIs only |

Lakshman's explicit direction: *"Better we set that up on the Kubernetes. So what is the advantage of following this architecture? ...I just asked him to set up in the local and then better we set that up on the Kubernetes."*

---

## Consequences

1. The deployment topology requires Kubernetes manifests: Namespace, Deployment, Service, Ingress, ConfigMap, and Secrets. These are in `k8s/`.

2. PostgreSQL is provisioned as Cloud SQL (managed), not as an in-cluster PersistentVolume. See ADR-002.

3. Redis is provisioned as Cloud Memorystore (managed), not as an in-cluster pod. See ADR-002.

4. The container port exposure configuration flag **must be explicitly set to `true`** in every deployment context (local Docker Compose and GKE). This is enforced by:
   - `k8s/configmap.yaml`: `CF_EXPOSE_CONTAINER_PORT: "true"`
   - `docker-compose.yml`: `CF_EXPOSE_CONTAINER_PORT: "${CF_EXPOSE_CONTAINER_PORT:-true}"`
   - `config/contextforge.example.yaml`: `expose_container_port` key documented with this ADR reference

5. The exact YAML key name within the ContextForge configuration file is assumed to be `expose_container_port` under the `gateway:` section. This assumption is documented as Q3 in `doc/Specify.md` and must be verified against IBM ContextForge documentation when Q1 (image URI) is resolved and the stack can be started. If the key name differs, this ADR, `config/contextforge.example.yaml`, and the relevant ConfigMap must be updated.

---

## Unresolved Items

| Item | Resolution |
|---|---|
| Exact ContextForge YAML key for port exposure | Pending IBM doc review (Q3). Assumed: `gateway.expose_container_port` |
| Exact GCP API that must be enabled | Pending IBM doc review (Q1). Assumed: Cloud Run Admin API is irrelevant in GKE path |
| Confirmed health endpoint paths | Pending image availability. Assumed: `/health` on both ports 8080 and 8081 |

---

## Evidence

- Meeting transcript: `gemesis/BH-Daily-20052026.txt`, timestamps 00:01:41 — 00:04:32
- Plan ticket: `doc/Plan.md`, EPIC-MF-E03, MF-E03-T01
- Specification reference: `doc/Specify.md` Section 15, Q3; Section 6, definition of "Container Port Exposure"
