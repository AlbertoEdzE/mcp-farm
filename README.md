# MCP Farm

Enterprise MCP gateway for the Baptist Health AI platform, built on IBM ContextForge deployed to Google Kubernetes Engine.

MCP Farm provides a single governed access point through which AI agents discover, authenticate against, and invoke tools registered in the gateway. External vendor MCPs (GitLab, Snowflake) are registered as proxies; tool access for each AI agent role is scoped via virtual servers.

---

## Prerequisites

**Required tools**

| Tool | Minimum version | Purpose |
|---|---|---|
| Python | 3.11 | Test suite, operational scripts |
| Docker | 24.x | Local stack via Docker Compose |
| make | 3.8 | Task runner |
| gcloud | 460.x | GKE provisioning |
| kubectl | 1.29 | Kubernetes operations |

**Open questions — must be resolved before GKE deployment**

| ID | Question | Owner | Status |
|---|---|---|---|
| Q1 | IBM ContextForge image URI and entitlement key | Kashyap | Open |
| Q2 | GCP sandbox project ID | Chakri | Open |
| Q4 | GitLab OAuth registration type (static or dynamic) | Bala | Open |
| Q5 | GCP Secret Manager availability in sandbox | Chakri | Open |
| Q6 | GKE node machine type and count | Lakshman | Open |

Local infrastructure tests (postgres + redis) run without resolving any open questions. ContextForge stack tests require Q1.

---

## Quick Start — Local Environment

```bash
# 1. Clone and install
git clone https://github.com/AlbertoEdzE/mcp-farm.git
cd mcp-farm
cp .env.example .env          # populate CLOUDSQL_USER, CLOUDSQL_PASSWORD

# 2. Install Python dependencies
make install

# 3. Generate synthetic test data
make generate-data

# 4. Run structural tests (no stack required)
make test CLUSTER=c0,c1,c2,c3,c4,c5,c6

# 5. Start infrastructure (postgres + redis) — Q1 not required
make local-up -- --infra-only
make test CLUSTER=c1

# 6. When Q1 is resolved: start the full stack
make local-up
make register-proxy
make create-virtual-server
make test
```

---

## Make Targets

| Target | Description |
|---|---|
| `make install` | Install prerequisites and create Python virtual environment |
| `make local-up` | Start Docker Compose stack (accepts `-- --infra-only`) |
| `make local-down` | Stop Docker Compose stack and remove volumes |
| `make generate-data` | Generate deterministic synthetic test fixtures (seed 42) |
| `make register-proxy` | Register the GitLab MCP proxy with ContextForge Config Registry |
| `make create-virtual-server` | Create the test virtual server in ContextForge Config Registry |
| `make gke-provision` | Provision GKE cluster, Cloud SQL, and Memorystore |
| `make gke-deploy` | Deploy ContextForge Kubernetes manifests to GKE |
| `make gke-teardown` | Destroy all GKE and managed GCP resources (destructive) |
| `make test` | Run full test suite (filter: `make test CLUSTER=c0,c1`) |
| `make lint` | Run ruff linter |
| `make typecheck` | Run mypy type checker |
| `make clean` | Remove generated artefacts |

---

## Running Tests

Tests are organised by cluster. Each cluster's tests build on prior ones — run progressively.

```bash
# Structural only (always safe to run, no stack needed)
make test CLUSTER=c0
make test CLUSTER=c0,c1,c2,c3,c4,c5,c6

# With infrastructure (postgres + redis running)
make local-up -- --infra-only
make test CLUSTER=c1

# Full stack (Q1 resolved, make local-up running)
make test

# GKE target
TEST_TARGET=gke make test CLUSTER=c2,c3
```

Test count per cluster (structural tests only, skipped tests excluded):

| Cluster | Tests |
|---|---|
| C0 | 18 |
| C1 | 13 structural + 6 integration |
| C2 | 8 structural + 4 integration |
| C3 | 34 structural |
| C4 | 14 structural + 4 integration |
| C5 | 17 structural + 4 integration |
| C6 | structural |

---

## Cluster Map

| Cluster | EPIC | Description | Status |
|---|---|---|---|
| C0 | E01 | Repository foundation — directory structure, env templates, Makefile | Done |
| C1 | E02 | Local environment — Docker Compose, scripts, synthetic data fixtures | Done |
| C2 | E03 | ContextForge baseline — ADR-001, port exposure config, health paths | Done |
| C3 | E04 | GKE infrastructure — provision/deploy/teardown scripts, ADR-002 | Done |
| C4 | E05 | MCP proxy registration — GitLab proxy, OAuth strategy, ADR-003 | Done |
| C5 | E06 | Virtual server — tool scoping, access boundary, ADR-004 | Done |
| C6 | E07 | Documentation and runbook | Done |

---

## Architecture

```
Baptist Health AI agents
         |
         v
  ContextForge AI Gateway (port 8080)
         |
  ContextForge Config Registry (port 8081)
    |              |
    v              v
Virtual        MCP Proxies
Servers        (GitLab, Snowflake)
    |
    v
 GKE (mcp-farm namespace)
    |
    +---> Cloud SQL (PostgreSQL 15)
    +---> Memorystore (Redis 7)
```

**Local development mirrors GKE:**

```
docker-compose.yml
  contextforge  ->  k8s/deployment.yaml
  postgres      ->  Cloud SQL
  redis         ->  Memorystore
```

---

## Architecture Decision Records

| ADR | Decision |
|---|---|
| ADR-001 | GKE over Cloud Run — documents the Cloud Run failure root causes |
| ADR-002 | Cloud SQL and Memorystore over in-cluster StatefulSets |
| ADR-003 | Static OAuth 2.0 client registration for GitLab MCP proxy |
| ADR-004 | Virtual server as the agent access control boundary |

---

## Repository Structure

```
mcp-farm/
  config/                    # Configuration templates (committed, never populated files)
    contextforge.example.yaml
    gke.example.yaml
  doc/
    ADR/                     # Architecture Decision Records
    Plan.md                  # JIRA-style epics and tickets (source of truth)
    Runbook.md               # Deployment and operational runbook
    Specify.md               # SDD specification document
  k8s/                       # Kubernetes manifests
  scripts/                   # Operational shell and Python scripts
  tests/
    fixtures/                # Deterministic synthetic data (seed 42)
    conftest.py
    test_c0_foundation.py    # ... through test_c6_documentation.py
  .env.example               # Environment variable template
  docker-compose.yml
  Makefile
  requirements.txt
  requirements-dev.txt
```

---

## Team

| Name | Role |
|---|---|
| Alberto Hernandez | Engineer — implementation |
| Lakshman | Architect |
| Kashyap | Infrastructure / ContextForge setup |
| Chakri | GCP sandbox provisioning |
| Bala | GitLab OAuth 2.0 |
