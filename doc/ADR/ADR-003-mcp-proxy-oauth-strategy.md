# ADR-003: Static OAuth 2.0 Client Registration for GitLab MCP Proxy

**Date:** 2026-05-21  
**Status:** Assumed — pending Q4 confirmation from Bala  
**Decided by:** Team assumption from 2026-05-20 standup, pending Bala validation  
**Documented by:** Alberto Hernandez

---

## Context

IBM ContextForge routes MCP tool calls to external vendor MCPs through its proxy layer. Each registered proxy requires an authentication configuration. The GitLab MCP server uses OAuth 2.0.

OAuth 2.0 client registration has two modes:

- **Dynamic client registration (RFC 7591):** The ContextForge proxy dynamically registers a client with the GitLab OAuth server at startup. The server issues a client ID and secret and returns them in a registration response. No pre-provisioned credentials are required.
- **Static client registration:** A GitLab OAuth application is created manually by a GitLab administrator. The resulting client ID and secret are stored as environment variables (or Kubernetes Secrets) and passed to ContextForge at configuration time.

During the 2026-05-20 daily standup, Bala confirmed existing experience with the GitLab OAuth 2.0 integration. The team deferred the exact registration model to Q4, but the meeting context — Bala referencing established credentials — suggests static registration is already in use or assumed.

---

## Decision

**Assume static OAuth 2.0 client registration for the GitLab MCP proxy in Phase 1.**

The proxy configuration in `config/contextforge.example.yaml` and `k8s/configmap.yaml` will carry `client_id` and `client_secret` as static values read from environment variables. Dynamic registration is not implemented in Phase 1.

---

## Rationale

| Factor | Dynamic registration | Static registration |
|---|---|---|
| Credential management | Automated, server-issued | Manual, operator-provisioned |
| GitLab self-hosted support | Not universally supported | Standard OAuth application feature |
| Operational simplicity | Requires RFC 7591 support on GitLab side | Works on any GitLab version |
| Phase 1 scope | Adds complexity without confirmed benefit | Consistent with existing team practice |
| Auditability | Runtime-generated clients harder to audit | Named OAuth app auditable in GitLab admin |

Static registration is lower risk for Phase 1 and is consistent with Assumption A4 in `doc/Specify.md`.

---

## Consequences

1. A GitLab OAuth application must be created manually in the target GitLab instance before `gke_deploy.sh` runs. The application must grant scopes: `read_api`, `read_repository`.

2. The resulting credentials are stored in `.env` as `GITLAB_OAUTH_CLIENT_ID` and `GITLAB_OAUTH_CLIENT_SECRET`. These are injected into ContextForge at runtime via environment variables.

3. The proxy registration fixture (`tests/fixtures/mcp_proxy_registration.json`) uses synthetic OAuth values for testing. Real values are never committed.

4. If Q4 resolution reveals that the GitLab instance requires dynamic registration, this ADR must be updated, the proxy config key `auth.type` verified, and `GITLAB_OAUTH_CLIENT_ID` / `GITLAB_OAUTH_CLIENT_SECRET` may be replaced with a dynamic registration endpoint.

---

## Unresolved Items

| Item | Resolution |
|---|---|
| Q4: Does the GitLab instance support or require dynamic client registration? | Pending Bala's confirmation |
| Exact ContextForge proxy config key for OAuth client secret | Pending IBM doc review (Q1) |
| Token endpoint path for the target GitLab instance | Pending Q4 — assumed: `<GITLAB_MCP_URL>/oauth/token` |

---

## Evidence

- Meeting transcript: `gemesis/BH-Daily-20052026.txt`
- Specification assumption A4: `doc/Specify.md` Section 15
- Open question Q4: `doc/Specify.md` Section 15
