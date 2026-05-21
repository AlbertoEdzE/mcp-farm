# ADR-004: Virtual Server as the Agent Access Control Boundary

**Date:** 2026-05-21  
**Status:** Accepted  
**Decided by:** Lakshman (architect)  
**Documented by:** Alberto Hernandez

---

## Context

ContextForge exposes two types of HTTP surfaces:

1. **MCP Proxies** — registered connections to external vendor MCPs (e.g., GitLab). A proxy entry stores the remote URL, transport protocol, and OAuth 2.0 credentials. A proxy is a plumbing resource; it is not directly accessible to AI agents.

2. **Virtual Servers** — named, governed MCP endpoints that aggregate a specific set of tools drawn from one or more registered proxies. A virtual server is what an AI agent connects to.

The question this ADR resolves: at what layer does access control and tool scoping happen for AI agents consuming tools from MCP Farm?

---

## Decision

**The Virtual Server is the access control boundary. Each AI agent role is assigned exactly one virtual server. No AI agent connects directly to a proxy.**

Tool visibility, tool naming, and tool schemas are all defined at the virtual server level. An agent can only call tools that appear in its assigned virtual server — tools from registered proxies that are not included in the virtual server definition are invisible to that agent.

---

## Rationale

| Factor | Proxy-level access | Virtual Server access |
|---|---|---|
| Tool scoping | All tools from all proxies visible | Explicit inclusion list per agent |
| Credential separation | Agents hold proxy OAuth secrets | Agents interact with virtual server only |
| Audit trail | Per-proxy, coarse | Per-virtual-server, per-tool invocation |
| Multi-proxy composition | Not supported | Single virtual server can aggregate from N proxies |
| Baptist Health requirement | Violates least-privilege | Satisfies least-privilege for AI agents |

Baptist Health's governance requirement is that AI agents are constrained to a declared set of tools. The virtual server model enforces this at the ContextForge layer rather than at the application layer, making it auditable and centrally managed.

---

## Consequences

1. Every AI agent that consumes tools from MCP Farm must be assigned a named virtual server. The virtual server name is passed to the agent as `VIRTUAL_SERVER_NAME`.

2. The virtual server definition (`config/contextforge.example.yaml` section `virtual_servers`) is the source of truth for what tools a given agent role can invoke.

3. Each tool in a virtual server definition references a tool exposed by an already-registered MCP proxy. The proxy must be registered before the virtual server is created.

4. Virtual servers are created via `scripts/create_virtual_server.py` and registered with the ContextForge Config Registry API (assumed: `POST /v1/virtual-servers`).

5. The tool invocation fixture (`tests/fixtures/tool_invocation_request.json`) targets the virtual server by name, not the proxy directly. This is intentional and verifies the access control boundary.

6. If a new tool is needed, the workflow is: register the tool in the proxy → add the tool to the virtual server definition → re-register the virtual server. There is no shortcut that bypasses the virtual server.

---

## Unresolved Items

| Item | Resolution |
|---|---|
| Exact ContextForge API path for virtual server creation | Pending Q1 — assumed: `POST /v1/virtual-servers` |
| Schema key for proxy reference within virtual server tools | Pending Q1 — assumed: `proxy: <proxy-name>` under each tool entry |
| Whether virtual servers support per-tool auth overrides | Pending IBM doc review |

---

## Evidence

- Specification: `doc/Specify.md` Section 5 (stakeholders), Section 6 (definitions — Virtual Server)
- Meeting transcript: `gemesis/BH-Daily-20052026.txt` — Kashyap's virtual server demo attempt
- ADR-003: `doc/ADR/ADR-003-mcp-proxy-oauth-strategy.md` — proxy registration precedes virtual server creation
- Plan ticket: `doc/Plan.md`, EPIC-MF-E06
