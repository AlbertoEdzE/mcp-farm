# Plan: MCP Farm

**Document class:** SDD Phase 2 — Plan  
**SDD Framework:** SPTI (Specify, Plan, Task, Implement)  
**Derived from:** `doc/Specify.md` (authoritative specification)  
**Author:** Alberto Hernandez  
**Project:** mcp-farm  
**Client:** Baptist Health  
**Date:** 2026-05-21  
**Status:** Active  
**Revision:** 1.0

---

## How to Read This Document

This document is the source of truth for all implementation work on the MCP Farm project. It is structured to be consumed by any developer or AI coding agent who needs to understand, continue, or audit work on this project — even with no prior context beyond this file and `doc/Specify.md`.

**Reading order for a new agent or developer:**
1. Read `doc/Specify.md` in full for definitions, philosophy, constraints, and architecture.
2. Read Section 1 of this document (Global Requirements) to understand what must be built and with what tools.
3. Read Section 2 (Expected Final Product) to understand the target state.
4. Navigate to the Epic of the current phase and read all tickets within it in order.
5. Before starting any ticket, verify its Preconditions are met. Before closing it, verify all Acceptance Criteria and update status.

**Status values used in this document:**  
`To Do` | `In Progress` | `Blocked` | `Done`

**Priority values:** `Critical` | `High` | `Medium` | `Low`  
**Complexity values:** `XS` (under 1h) | `S` (1-2h) | `M` (2-4h) | `L` (4-8h) | `XL` (over 8h)

---

## Section 1 — Global Requirements

### 1.1 Purpose Statement

The MCP Farm project delivers a governed, enterprise-grade MCP (Model Context Protocol) gateway for the Baptist Health AI Platform. The gateway acts as a single, authenticated access point through which AI agents discover and invoke tools, regardless of whether those tools are hosted externally (vendor MCPs) or defined internally (virtual servers). The gateway is built on IBM ContextForge, deployed on Google Cloud GKE, and backed by managed Cloud SQL and Memorystore services.

### 1.2 Technology Stack

All version numbers below are minimum required versions unless marked as exact. Where a version is marked as exact, deviation requires an Architecture Decision Record entry.

#### Infrastructure

| Component | Technology | Version | Role |
|---|---|---|---|
| Container orchestration | Google Kubernetes Engine (GKE) | 1.29+ | Production deployment platform |
| Container runtime | Docker | 24.0+ | Local development |
| Compose tool | Docker Compose | v2.20+ | Local stack orchestration |
| IaC / provisioning | Google Cloud SDK (`gcloud`) | 460.0+ | GCP resource provisioning |
| Kubernetes client | `kubectl` | 1.29+ | Cluster management |
| GCP managed database | Cloud SQL — PostgreSQL 15 (exact) | 15 | ContextForge config registry persistence |
| GCP managed cache | Cloud Memorystore — Redis 7 (exact) | 7 | ContextForge session and config cache |

#### Application

| Component | Technology | Version | Role |
|---|---|---|---|
| MCP gateway | IBM ContextForge | latest stable (resolve Q1) | Core gateway; AI Gateway + Config Registry |
| Configuration format | YAML | — | ContextForge configuration |
| Secret management | Kubernetes Secrets or GCP Secret Manager | — | Resolve per Q5 |

#### Development and Testing

| Component | Technology | Version | Role |
|---|---|---|---|
| Runtime | Python | 3.11+ | Scripts, tests, data generation |
| Test framework | `pytest` | 8.0+ | All test types |
| Data validation | `pydantic` | 2.0+ | API contract tests |
| Synthetic data | `faker` | 24.0+ | Deterministic test data generation |
| HTTP client | `httpx` | 0.27+ | API calls in tests and scripts |
| Environment management | `python-dotenv` | 1.0+ | Loading `.env` in scripts and tests |
| Linter | `ruff` | 0.4+ | Code quality enforcement |
| Type checker | `mypy` | 1.8+ | Type correctness |
| MCP protocol testing | MCP Inspector | latest | Manual protocol validation |
| stdio-to-HTTP bridge | `mcp-remote` (npm) | latest | Local MCP Inspector testing only |

#### Repository and Tooling

| Component | Technology | Version | Role |
|---|---|---|---|
| Version control | Git | 2.40+ | Source control |
| Build automation | `make` (GNU Make) | 4.0+ | Unified command interface |
| Shell scripts | `bash` | 5.0+ | Automation scripts |

### 1.3 Specific Goals

The following goals are derived directly from the three non-negotiable outcomes in `doc/Specify.md` Section 3. Each goal is stated as a verifiable condition.

**Goal G1 — Infrastructure provisioned and operational.**  
A GKE cluster named `mcp-farm-sandbox` exists in the designated GCP sandbox project. The cluster contains a namespace `mcp-farm` with a running ContextForge deployment. Cloud SQL instance `mcp-farm-pg` (PostgreSQL 15) and Memorystore instance `mcp-farm-redis` (Redis 7) exist, are accessible from the cluster network, and are connected to ContextForge.

**Goal G2 — ContextForge AI Gateway reachable.**  
The ContextForge AI Gateway container port (8080) is correctly exposed via a Kubernetes Service and Ingress. An HTTP GET request to the gateway health endpoint from within the cluster returns HTTP 200. The container port exposure configuration flag is confirmed set to `true` in all deployment manifests and local Docker Compose configuration.

**Goal G3 — ContextForge Config Registry reachable.**  
The ContextForge Config Registry (port 8081) is reachable from within the cluster. An HTTP GET request to the registry health endpoint returns HTTP 200.

**Goal G4 — GitLab MCP proxy registered and functional.**  
The GitLab MCP server is registered in ContextForge as a proxy. An HTTP GET request to the ContextForge tools listing endpoint returns a JSON array that includes tools originating from the GitLab MCP. The OAuth 2.0 authentication flow between ContextForge and GitLab is documented and reproducible.

**Goal G5 — Virtual server registered and invocable.**  
At least one virtual server is registered in ContextForge with a minimum of two tool definitions. An agent-equivalent HTTP request to invoke one of those tools returns the expected response. This is validated by an automated test.

**Goal G6 — Full deployment reproducible from clean checkout.**  
A team member starting from a fresh `git clone`, with only the documented prerequisites installed and the `.env` file populated from `.env.example`, can execute `scripts/install.sh` and `scripts/local_up.sh` to obtain a running local environment, or `scripts/gke_deploy.sh` to deploy to GKE, without requiring any undocumented knowledge.

**Goal G7 — All behaviour verified by automated tests.**  
The full test suite (`make test`) passes with exit code 0 against a properly configured environment. The test suite covers structural validation (C0), local environment health (C1), ContextForge baseline (C2), GKE infrastructure (C3), proxy registration (C4), and virtual server invocation (C5). Progressive integration: tests from all prior clusters are re-executed at the end of each new cluster.

### 1.4 Non-Goals (Explicit Exclusions)

The following will not be delivered in Phase 1, regardless of scope creep pressure. Any request to include these must be escalated as a new Jira story.

- Production-grade high availability, autoscaling, or multi-zone deployment.
- Snowflake MCP proxy registration (assigned to Bala).
- CI/CD pipeline automation for MCP onboarding.
- Observability dashboards, alerting, or SLO definitions.
- Agent business logic of any kind.
- Cloud Run as a deployment target.

---

## Section 2 — Expected Final Product

At the conclusion of Phase 1, the following is the complete, observable state of the system.

### 2.1 Repository State

The `mcp-farm` Git repository on the `main` branch contains the following committed artefacts, all in the canonical directory structure defined in `doc/Specify.md` Section 13:

```
mcp-farm/
  config/
    contextforge.example.yaml     # Template with all config keys documented, no real values
    gke.example.yaml              # GKE parameter template
  doc/
    Specify.md                    # Specification (Phase 1)
    Plan.md                       # This document (Phase 2)
    Runbook.md                    # Deployment runbook with exact commands and expected outputs
    ADR/
      ADR-001-gke-over-cloud-run.md
      ADR-002-managed-services-over-pvs.md
  gemesis/
    BH-Daily-20052026.txt         # Source meeting transcript
    ticket                        # Source ticket description
  k8s/
    namespace.yaml
    deployment.yaml
    service.yaml
    ingress.yaml
    configmap.yaml
    secrets.example.yaml
  scripts/
    install.sh
    local_up.sh
    local_down.sh
    gke_provision.sh
    gke_deploy.sh
    gke_teardown.sh
    run_tests.sh
    generate_synthetic_data.py
  tests/
    conftest.py
    test_c0_foundation.py
    test_c1_local_environment.py
    test_c2_contextforge_baseline.py
    test_c3_gke_infrastructure.py
    test_c4_mcp_proxy_registration.py
    test_c5_virtual_server.py
  docker-compose.yml
  .env.example
  Makefile
  requirements.txt
  requirements-dev.txt
  README.md
```

No file in the repository contains a secret, credential, or environment-specific value. The `.gitignore` enforces this.

### 2.2 Runtime State (GKE)

```
GKE Cluster: mcp-farm-sandbox (GCP sandbox project, configured region)
  Namespace: mcp-farm
    Pods: contextforge-<hash>   Status: Running
    Service: contextforge-svc   Type: ClusterIP  Ports: 8080, 8081
    Ingress: contextforge-ingress  External IP: <assigned>
    ConfigMap: contextforge-config
    Secret: contextforge-db-credentials
    Secret: contextforge-redis-credentials
    Secret: ibm-entitlement-key  (image pull secret)

GCP Managed Services:
  Cloud SQL: mcp-farm-pg  Engine: PostgreSQL 15  Tier: db-f1-micro (or approved)
  Memorystore: mcp-farm-redis  Version: Redis 7  Tier: BASIC  Size: 1GB

ContextForge Registry State:
  MCP Proxy: gitlab-mcp  Transport: SSE or Streamable HTTP  Auth: OAuth 2.0
  Virtual Server: test-virtual-server  Tools: [tool-alpha, tool-beta]
```

### 2.3 Behavioural State

- `GET <gateway>/health` returns `{"status": "ok"}` or equivalent with HTTP 200.
- `GET <registry>/health` returns `{"status": "ok"}` or equivalent with HTTP 200.
- `GET <gateway>/v1/tools` (or equivalent) returns a JSON array containing GitLab MCP tools and test virtual server tools.
- Invoking `tool-alpha` from the test virtual server via the gateway returns a well-formed JSON response.
- `make test` completes with exit code 0 and produces `reports/test-results.xml`.

---

## Section 3 — Epic and Ticket Hierarchy

### Ticket ID Format

```
MF-<EPIC_NUMBER>-<TICKET_NUMBER>
```

Epic identifiers: E01 through E07.  
Example: `MF-E01-T01` is the first ticket of the first epic.

### Dependency notation

`DEPENDS_ON: MF-EXX-TYY` means ticket `MF-EXX-TYY` must reach status `Done` before this ticket can begin.  
`BLOCKS: MF-EXX-TYY` means this ticket must reach `Done` before `MF-EXX-TYY` can begin.

---

## EPIC-MF-E01: Repository Foundation

**Cluster:** C0  
**Phase:** 1  
**Status:** To Do  
**Priority:** Critical  
**Description:** Establish the complete, canonical repository structure from which all subsequent work builds. This epic has no code logic — it establishes the skeleton, contracts, and toolchain. Nothing in C1 through C6 can proceed without C0 being complete and committed.  
**Business value:** Without a stable, agreed foundation, every subsequent cluster risks structural inconsistency that compounds into integration failures. This epic eliminates that class of failure before it can occur.  
**Postcondition of epic:** A developer starting from a clean checkout of the repository after this epic is committed can run `make help` to see all available targets, `make lint` to confirm the linter is configured, and `make test CLUSTER=c0` to confirm the structural validation test passes.

---

### MF-E01-T01: Establish canonical directory structure

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** XS  
**Cluster:** C0

**Description:**  
Create all directories and placeholder files defined in `doc/Specify.md` Section 13. Empty directories receive a `.gitkeep` file. Files with `.example` suffix receive their placeholder structure (keys present, values empty or descriptive strings that are clearly not real values).

**Preconditions:**  
- `doc/Specify.md` exists and is committed.
- `doc/Plan.md` (this document) exists.
- The repository root is `/mcp-farm`.

**Technical Requirements:**  
- All directory names are lowercase with hyphens, no underscores.
- All file names follow the conventions in `doc/Specify.md` Section 13 exactly.
- No file in this ticket contains any real credential, hostname, or project identifier.

**Postconditions:**  
- Running `find . -not -path './.git/*'` from the repository root produces output that matches the tree in `doc/Specify.md` Section 13 (excluding files created by later tickets).
- All directories exist. No directory listed in the specification is missing.

**Acceptance Criteria:**  
1. All directories listed in `doc/Specify.md` Section 13 exist.
2. All `.example` files exist and contain clearly labelled placeholder keys.
3. No `.example` file contains a real value for any sensitive parameter.
4. `git status` shows all new files as untracked (not ignored).

**Test file:** `tests/test_c0_foundation.py` — test `test_directory_structure_complete`  
**Dependencies:** None  
**Blocks:** All other tickets in E01

**Definition of Done:**  
- [ ] All directories and placeholder files created.
- [ ] `test_directory_structure_complete` passes.
- [ ] No secrets in any file.

---

### MF-E01-T02: Create .env.example

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** S  
**Cluster:** C0

**Description:**  
Create `.env.example` at the repository root. This file documents every environment variable consumed by any script, test, or configuration file in the project. It is the single authoritative reference for required configuration. Any variable not listed here is not a valid variable in this project.

**Preconditions:**  
- MF-E01-T01 is Done.

**Technical Requirements:**  
The following variable groups must be present with descriptive placeholder values:

```
# GCP configuration
GCP_PROJECT_ID=<your-gcp-project-id>
GCP_REGION=<gcp-region-e.g.-us-central1>
GCP_ZONE=<gcp-zone-e.g.-us-central1-a>

# GKE cluster
GKE_CLUSTER_NAME=mcp-farm-sandbox
GKE_NAMESPACE=mcp-farm
GKE_NODE_MACHINE_TYPE=<resolve-Q6>
GKE_NODE_COUNT=<resolve-Q6>

# IBM ContextForge
CF_IMAGE_URI=<resolve-Q1>
CF_IMAGE_TAG=<resolve-Q1>
CF_GATEWAY_PORT=8080
CF_REGISTRY_PORT=8081
CF_EXPOSE_CONTAINER_PORT=true

# Cloud SQL
CLOUDSQL_INSTANCE_NAME=mcp-farm-pg
CLOUDSQL_DATABASE_NAME=contextforge
CLOUDSQL_USER=<db-username>
CLOUDSQL_PASSWORD=<db-password>
CLOUDSQL_CONNECTION_STRING=<host:port/dbname>

# Memorystore
MEMORYSTORE_INSTANCE_NAME=mcp-farm-redis
REDIS_HOST=<redis-host>
REDIS_PORT=6379

# Local Docker overrides
LOCAL_POSTGRES_PORT=5432
LOCAL_REDIS_PORT=6379
LOCAL_CF_GATEWAY_PORT=8080
LOCAL_CF_REGISTRY_PORT=8081

# IBM entitlement
IBM_ENTITLEMENT_KEY=<resolve-Q1>

# GitLab MCP (OAuth 2.0)
GITLAB_MCP_URL=<gitlab-mcp-endpoint>
GITLAB_OAUTH_CLIENT_ID=<resolve-Q4>
GITLAB_OAUTH_CLIENT_SECRET=<resolve-Q4>

# Test configuration
TEST_SYNTHETIC_DATA_SEED=42
TEST_TARGET=local
TEST_GATEWAY_BASE_URL=http://localhost:8080
TEST_REGISTRY_BASE_URL=http://localhost:8081
```

**Postconditions:**  
- `.env.example` exists at the repository root.
- Every variable consumed anywhere in the project is listed in this file.
- Copying `.env.example` to `.env` and filling in real values produces a complete, working environment.
- `.env` is in `.gitignore` (verify, do not modify `.gitignore` if already present).

**Acceptance Criteria:**  
1. `.env.example` exists.
2. All variable groups listed in Technical Requirements are present.
3. No variable has a real value (all values are placeholder strings matching the pattern `<description>`).
4. `.env` is confirmed present in `.gitignore`.

**Test file:** `tests/test_c0_foundation.py` — test `test_env_example_complete`  
**Dependencies:** MF-E01-T01  
**Blocks:** MF-E01-T03, MF-E02-T01

**Definition of Done:**  
- [ ] `.env.example` created with all variable groups.
- [ ] `test_env_example_complete` passes.
- [ ] `.env` confirmed in `.gitignore`.

---

### MF-E01-T03: Create requirements.txt and requirements-dev.txt

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** S  
**Cluster:** C0

**Description:**  
Create the two Python dependency files that define the runtime and development environments. Versions are pinned to exact versions to guarantee reproducibility. `requirements.txt` contains runtime dependencies (scripts, data generation). `requirements-dev.txt` contains everything in `requirements.txt` plus testing and linting tools.

**Preconditions:**  
- MF-E01-T01 is Done.
- Python 3.11+ is available on the development machine.

**Technical Requirements:**

`requirements.txt` must include at minimum:
```
httpx>=0.27.0
pydantic>=2.0.0
python-dotenv>=1.0.0
faker>=24.0.0
pyyaml>=6.0.1
```

`requirements-dev.txt` must include:
```
-r requirements.txt
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-httpx>=0.30.0
mypy>=1.8.0
ruff>=0.4.0
```

All versions must be pinned with `>=` minimum bounds. After resolving the actual environment, versions are pinned to exact versions using `pip freeze > requirements-lock.txt` (lock file committed for reproducibility).

**Postconditions:**  
- `pip install -r requirements-dev.txt` completes without error in a fresh virtual environment.
- All libraries listed are importable.

**Acceptance Criteria:**  
1. `requirements.txt` exists with all listed packages.
2. `requirements-dev.txt` exists and includes `-r requirements.txt`.
3. `pip install -r requirements-dev.txt` succeeds in a clean virtual environment.
4. `python -c "import httpx, pydantic, faker, dotenv, yaml, pytest"` exits with code 0.

**Test file:** `tests/test_c0_foundation.py` — test `test_requirements_installable`  
**Dependencies:** MF-E01-T01  
**Blocks:** MF-E01-T04, MF-E01-T05

**Definition of Done:**  
- [ ] Both files created with correct contents.
- [ ] Install test passes in clean virtual environment.
- [ ] `test_requirements_installable` passes.

---

### MF-E01-T04: Create Makefile

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** M  
**Cluster:** C0

**Description:**  
Create a `Makefile` at the repository root that provides a unified command interface for all project operations. The Makefile is the primary interface — scripts in `scripts/` are the implementation. No developer or agent should need to remember raw script paths.

**Preconditions:**  
- MF-E01-T03 is Done.

**Technical Requirements:**

The Makefile must define the following targets:

| Target | Command | Description |
|---|---|---|
| `help` | (default) | Print all targets with descriptions |
| `install` | `scripts/install.sh` | Install all dependencies |
| `local-up` | `scripts/local_up.sh` | Start local Docker Compose stack |
| `local-down` | `scripts/local_down.sh` | Stop local Docker Compose stack |
| `gke-provision` | `scripts/gke_provision.sh` | Provision GKE + managed services |
| `gke-deploy` | `scripts/gke_deploy.sh` | Deploy K8s manifests to GKE |
| `gke-teardown` | `scripts/gke_teardown.sh` | Destroy GKE resources |
| `test` | `scripts/run_tests.sh` | Run full test suite |
| `test CLUSTER=<id>` | `scripts/run_tests.sh --cluster <id>` | Run tests for one cluster |
| `lint` | `ruff check .` | Run linter |
| `typecheck` | `mypy tests/ scripts/` | Run type checker |
| `generate-data` | `python scripts/generate_synthetic_data.py` | Generate synthetic test data |
| `clean` | Remove `__pycache__`, `.pytest_cache`, `reports/` | Clean generated artefacts |

All targets that invoke scripts pass through environment variables from the calling shell. No target hardcodes any value.

`make help` must print all targets. This is implemented using `##` comment convention.

**Postconditions:**  
- `make help` prints all targets.
- `make lint` runs without error on a clean repository.
- `make clean` removes generated artefacts without error.

**Acceptance Criteria:**  
1. `make help` exits with code 0 and prints all 13 targets.
2. All targets listed in Technical Requirements exist in the Makefile.
3. No hardcoded value in the Makefile body (variable references only).
4. `make clean` is idempotent: running it twice produces no error.

**Test file:** `tests/test_c0_foundation.py` — test `test_makefile_targets_present`  
**Dependencies:** MF-E01-T03  
**Blocks:** MF-E01-T06

**Definition of Done:**  
- [ ] Makefile created with all targets.
- [ ] `make help` works.
- [ ] `make lint` passes.
- [ ] `test_makefile_targets_present` passes.

---

### MF-E01-T05: Create conftest.py and test_c0_foundation.py

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** M  
**Cluster:** C0

**Description:**  
Create the base pytest configuration and the first test file. `conftest.py` defines project-wide fixtures — particularly the synthetic data factory and environment loader. `test_c0_foundation.py` validates the structural integrity of the repository itself (directory structure, file presence, `.env.example` completeness, Makefile targets).

**Preconditions:**  
- MF-E01-T01 through MF-E01-T04 are Done.
- `requirements-dev.txt` is installed.

**Technical Requirements:**

`tests/conftest.py` must define:
- A `fake` fixture (session-scoped) that returns a `Faker` instance with seed `TEST_SYNTHETIC_DATA_SEED` (read from environment, default `42`).
- A `env` fixture (session-scoped) that loads `.env` if it exists and returns a dict of all environment variables.
- A `gateway_base_url` fixture that reads `TEST_GATEWAY_BASE_URL` from environment.
- A `registry_base_url` fixture that reads `TEST_REGISTRY_BASE_URL` from environment.
- A `test_target` fixture that reads `TEST_TARGET` from environment (`local` or `gke`).

`tests/test_c0_foundation.py` must define:
- `test_directory_structure_complete`: asserts all directories from `doc/Specify.md` Section 13 exist.
- `test_env_example_complete`: asserts all variable groups are present in `.env.example`.
- `test_requirements_installable`: asserts all packages in `requirements.txt` are importable.
- `test_makefile_targets_present`: asserts all required targets exist in the Makefile by parsing it.
- `test_no_secrets_in_committed_files`: asserts no file in the repository matches patterns for real secrets (e.g., GCP project IDs that are not placeholder strings, tokens of typical entropy).

**Postconditions:**  
- `make test CLUSTER=c0` passes with exit code 0.
- `reports/test-results.xml` is produced.

**Acceptance Criteria:**  
1. `conftest.py` exists with all five fixtures defined.
2. `test_c0_foundation.py` exists with all five test functions defined.
3. `make test CLUSTER=c0` exits with code 0.
4. `reports/test-results.xml` is produced and contains results for all five tests.
5. All five tests pass.

**Test file:** `tests/test_c0_foundation.py` (self-referential: this test validates its own cluster)  
**Dependencies:** MF-E01-T01 through MF-E01-T04  
**Blocks:** All tests in subsequent epics

**Definition of Done:**  
- [ ] `conftest.py` created with all fixtures.
- [ ] `test_c0_foundation.py` created with all tests.
- [ ] `make test CLUSTER=c0` passes.
- [ ] XML report produced.

---

### MF-E01-T06: Create install.sh

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** S  
**Cluster:** C0

**Description:**  
Create `scripts/install.sh`, the entry-point script for setting up the development environment on a clean machine. This script installs system-level prerequisites (checking for them, not silently installing without notification), creates a Python virtual environment, and installs all Python dependencies.

**Preconditions:**  
- MF-E01-T03 is Done.
- MF-E01-T04 is Done.

**Technical Requirements:**  
- The script must be idempotent: running it a second time produces no error and no duplicate state.
- The script must accept `--help` and print usage.
- The script must check for required system tools (`docker`, `docker compose`, `kubectl`, `gcloud`, `python3`, `make`) and print a clear error for each one that is missing — it does not silently install system tools.
- The script creates or re-creates a Python virtual environment at `.venv/` in the repository root.
- The script installs `requirements-dev.txt` into the virtual environment.
- The script prints a summary of what was done and what the developer must do next (populate `.env` from `.env.example`).
- All output is plain text. No emoji.

**Postconditions:**  
- `.venv/` exists at the repository root.
- All packages in `requirements-dev.txt` are installed in `.venv/`.
- Running `source .venv/bin/activate && python -c "import pytest"` exits with code 0.

**Acceptance Criteria:**  
1. `scripts/install.sh --help` exits with code 0 and prints usage.
2. `scripts/install.sh` completes without error on a machine with all system prerequisites installed.
3. Running `scripts/install.sh` a second time exits with code 0 (idempotent).
4. After running, `pytest --version` inside `.venv` exits with code 0.

**Test file:** `tests/test_c0_foundation.py` — test `test_install_script_executable`  
**Dependencies:** MF-E01-T03, MF-E01-T04  
**Blocks:** MF-E02-T01

**Definition of Done:**  
- [ ] `install.sh` created and executable (`chmod +x`).
- [ ] Idempotency verified manually.
- [ ] `--help` output verified.
- [ ] `test_install_script_executable` passes.

---

### Cluster C0 Commit Prompt

When all tickets MF-E01-T01 through MF-E01-T06 are Done and `make test CLUSTER=c0` passes:

```
COMMIT READY: Cluster C0 — Repository Foundation

Suggested commit message:
  feat(c0): establish canonical repository structure and toolchain

  Initialises directory layout, .env.example, requirements, Makefile,
  install script, conftest, and structural validation test suite.
  All C0 acceptance criteria pass (make test CLUSTER=c0).

Files to stage:
  config/contextforge.example.yaml
  config/gke.example.yaml
  doc/Plan.md
  k8s/namespace.yaml
  k8s/deployment.yaml
  k8s/service.yaml
  k8s/ingress.yaml
  k8s/configmap.yaml
  k8s/secrets.example.yaml
  scripts/install.sh
  scripts/local_up.sh        (placeholder, populated in C1)
  scripts/local_down.sh      (placeholder, populated in C1)
  scripts/gke_provision.sh   (placeholder, populated in C3)
  scripts/gke_deploy.sh      (placeholder, populated in C3)
  scripts/gke_teardown.sh    (placeholder, populated in C3)
  scripts/run_tests.sh
  scripts/generate_synthetic_data.py  (placeholder, populated in C1)
  tests/conftest.py
  tests/test_c0_foundation.py
  .env.example
  Makefile
  requirements.txt
  requirements-dev.txt

Command:
  git add <files above> && git commit -m "feat(c0): establish canonical repository structure and toolchain"
```

---

## EPIC-MF-E02: Local Environment

**Cluster:** C1  
**Phase:** 1  
**Status:** To Do  
**Priority:** Critical  
**Description:** Build and validate the local Docker Compose stack that mirrors the GKE architecture. ContextForge, PostgreSQL, and Redis run as containers locally. All configuration is read from environment variables. Health checks pass. This cluster is the first point at which the system is live.  
**Business value:** Validates the ContextForge configuration locally before any GCP resources are provisioned, avoiding cloud cost and iteration time. Establishes the local-to-GKE parity that makes the GKE deployment low-risk.  
**Postcondition of epic:** `make local-up` starts the stack. `make test CLUSTER=c1` passes. `make local-down` stops it cleanly. All prior cluster tests still pass.

---

### MF-E02-T01: Create docker-compose.yml

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** M  
**Cluster:** C1

**Description:**  
Create `docker-compose.yml` at the repository root. This file defines the local three-service stack: ContextForge, PostgreSQL 15, and Redis 7. All ports and credentials are read from environment variables — no hardcoded values.

**Preconditions:**  
- MF-E01 epic is Done (all tickets).
- `.env` file exists (populated from `.env.example` by the developer).
- Q1 (ContextForge image URI) is resolved.
- Q3 (container port exposure flag) is resolved.

**Technical Requirements:**  
- Service `postgres`: image `postgres:15`, data volume `postgres_data` (named volume), port from `LOCAL_POSTGRES_PORT`, password from `CLOUDSQL_PASSWORD`, database from `CLOUDSQL_DATABASE_NAME`.
- Service `redis`: image `redis:7`, port from `LOCAL_REDIS_PORT`, no persistence required in local environment.
- Service `contextforge`: image from `CF_IMAGE_URI:CF_IMAGE_TAG`, ports from `LOCAL_CF_GATEWAY_PORT` (8080) and `LOCAL_CF_REGISTRY_PORT` (8081), container port exposure flag set to `true` (read from `CF_EXPOSE_CONTAINER_PORT`), `depends_on` postgres and redis with health check condition.
- ContextForge service must define health check: `GET http://localhost:8080/health` with interval 10s, timeout 5s, retries 5.
- PostgreSQL service must define health check: `pg_isready`.
- Redis service must define health check: `redis-cli ping`.
- No hardcoded value in `docker-compose.yml`. Every variable references the environment.

**Postconditions:**  
- `docker compose up -d` starts all three services.
- All three services pass their health checks within 60 seconds.
- `docker compose ps` shows all services as `healthy`.

**Acceptance Criteria:**  
1. `docker-compose.yml` exists.
2. All three services defined: `contextforge`, `postgres`, `redis`.
3. All ports and credentials read from environment variables.
4. Health checks defined for all three services.
5. `docker compose up -d` succeeds and all services reach `healthy` state within 60 seconds.
6. `docker compose down -v` removes all containers and named volumes cleanly.

**Test file:** `tests/test_c1_local_environment.py` — test `test_docker_compose_services_healthy`  
**Dependencies:** MF-E01-T06; Q1 and Q3 resolved  
**Blocks:** MF-E02-T02, MF-E02-T03

**Definition of Done:**  
- [ ] `docker-compose.yml` created.
- [ ] All services start and pass health checks.
- [ ] No hardcoded values.
- [ ] `test_docker_compose_services_healthy` passes.

---

### MF-E02-T02: Create contextforge.example.yaml config template

**Type:** Task  
**Status:** To Do  
**Priority:** High  
**Complexity:** M  
**Cluster:** C1

**Description:**  
Create `config/contextforge.example.yaml`. This file is the template for all ContextForge configuration. It documents every configuration key, its purpose, and its expected value type. It contains no real values. The actual `config/contextforge.yaml` (not committed) is derived from this file by the developer.

**Preconditions:**  
- Q1 and Q3 are resolved (image URI and port exposure flag key are known).
- MF-E02-T01 is In Progress (config keys are being discovered).

**Technical Requirements:**  
The file must contain at minimum the following sections:

```yaml
# ContextForge configuration template
# Copy to contextforge.yaml and fill in real values
# This file must not contain real values

gateway:
  port: <CF_GATEWAY_PORT>
  expose_container_port: <CF_EXPOSE_CONTAINER_PORT>  # Must be true — see ADR-001

registry:
  port: <CF_REGISTRY_PORT>

database:
  connection_string: <CLOUDSQL_CONNECTION_STRING>
  database_name: <CLOUDSQL_DATABASE_NAME>
  user: <CLOUDSQL_USER>
  password: <CLOUDSQL_PASSWORD>

cache:
  host: <REDIS_HOST>
  port: <REDIS_PORT>

proxy:
  # MCP proxy definitions added per MF-E05 (C4)

virtual_servers:
  # Virtual server definitions added per MF-E06 (C5)
```

**Postconditions:**  
- `config/contextforge.example.yaml` is committed.
- The file documents every ContextForge configuration key used in this project.

**Acceptance Criteria:**  
1. `config/contextforge.example.yaml` exists.
2. All sections listed in Technical Requirements are present.
3. No real value present in the file.
4. The `expose_container_port` key is present and its comment references ADR-001.

**Test file:** `tests/test_c1_local_environment.py` — test `test_contextforge_config_template_complete`  
**Dependencies:** MF-E02-T01  
**Blocks:** MF-E02-T03

**Definition of Done:**  
- [ ] File created.
- [ ] All sections documented.
- [ ] No real values.

---

### MF-E02-T03: Create local_up.sh and local_down.sh

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** S  
**Cluster:** C1

**Description:**  
Implement `scripts/local_up.sh` and `scripts/local_down.sh`. These scripts are the official start and stop procedures for the local environment. They wrap Docker Compose with pre-flight checks and clear output.

**Preconditions:**  
- MF-E02-T01 is Done.

**Technical Requirements:**

`local_up.sh`:
- Accepts `--help`.
- Verifies `.env` file exists; exits with error code 1 and instructions if not.
- Verifies Docker daemon is running.
- Verifies required environment variables are set (at minimum: `CF_IMAGE_URI`, `CLOUDSQL_PASSWORD`).
- Runs `docker compose up -d --wait`.
- Polls health checks and prints status until all services are healthy or timeout (120s) is reached.
- On success: prints gateway URL and registry URL.
- On timeout: prints docker logs for the failing service and exits with code 1.

`local_down.sh`:
- Accepts `--help`.
- Runs `docker compose down -v` (removes volumes for clean state).
- Confirms all containers are stopped.
- Both scripts are idempotent.

**Postconditions:**  
- `scripts/local_up.sh` starts the stack and confirms all services are healthy.
- `scripts/local_down.sh` stops the stack and removes volumes.
- Both scripts run without error if invoked when already in the expected state.

**Acceptance Criteria:**  
1. `local_up.sh --help` exits with code 0.
2. `local_up.sh` exits with code 0 when the stack starts successfully.
3. `local_up.sh` exits with code 1 if `.env` is missing.
4. `local_down.sh` exits with code 0 after stopping the stack.
5. Running `local_up.sh` twice exits with code 0 both times.
6. Running `local_down.sh` twice exits with code 0 both times.

**Test file:** `tests/test_c1_local_environment.py` — test `test_local_up_down_idempotent`  
**Dependencies:** MF-E02-T01  
**Blocks:** MF-E02-T04

**Definition of Done:**  
- [ ] Both scripts created and executable.
- [ ] Idempotency verified.
- [ ] `test_local_up_down_idempotent` passes.

---

### MF-E02-T04: Create generate_synthetic_data.py and write test_c1_local_environment.py

**Type:** Task  
**Status:** To Do  
**Priority:** High  
**Complexity:** M  
**Cluster:** C1

**Description:**  
Implement the synthetic data generator and the C1 integration test suite. The generator produces all data needed for tests in C1 through C5. The C1 tests confirm the local stack is operational.

**Preconditions:**  
- MF-E02-T03 is Done (local stack is startable).
- `requirements-dev.txt` is installed.

**Technical Requirements:**

`scripts/generate_synthetic_data.py`:
- Uses `faker` with seed from `TEST_SYNTHETIC_DATA_SEED` environment variable (default `42`).
- Produces the following data sets and writes them to `tests/fixtures/` (directory created by this script):
  - `mcp_proxy_registration.json`: a synthetic MCP proxy registration payload.
  - `virtual_server_definition.json`: a synthetic virtual server with two tool definitions.
  - `tool_invocation_request.json`: a synthetic tool invocation request body.
- Script is idempotent. Running twice overwrites with identical data (same seed).
- Script accepts `--help` and `--seed <integer>` arguments.

`tests/test_c1_local_environment.py` must define:
- `test_docker_compose_services_healthy`: calls `docker compose ps --format json`, asserts all three services show `healthy`.
- `test_gateway_port_reachable`: makes a TCP connection to `LOCAL_CF_GATEWAY_PORT`, asserts connection succeeds within 5 seconds.
- `test_registry_port_reachable`: same for `LOCAL_CF_REGISTRY_PORT`.
- `test_postgres_accepts_connections`: connects to PostgreSQL using `CLOUDSQL_CONNECTION_STRING`, asserts connection and `SELECT 1` succeeds.
- `test_redis_responds_to_ping`: connects to Redis, issues PING, asserts PONG response.
- `test_contextforge_config_template_complete`: parses `config/contextforge.example.yaml` and asserts all required keys are present.

**Postconditions:**  
- `tests/fixtures/` directory exists with three JSON files.
- `make test CLUSTER=c1` passes with the local stack running.

**Acceptance Criteria:**  
1. `generate_synthetic_data.py --help` exits with code 0.
2. Running `generate_synthetic_data.py` produces all three fixture files.
3. Running it twice produces byte-identical fixture files.
4. All six tests in `test_c1_local_environment.py` pass against a running local stack.
5. `make test CLUSTER=c1` exits with code 0.

**Test file:** `tests/test_c1_local_environment.py`  
**Dependencies:** MF-E02-T03  
**Blocks:** EPIC-MF-E03

**Definition of Done:**  
- [ ] Generator script created and verified idempotent.
- [ ] Fixtures directory and files created.
- [ ] All six C1 tests pass.
- [ ] `make test CLUSTER=c0,c1` (progressive) passes.

---

### Cluster C1 Commit Prompt

When all tickets MF-E02-T01 through MF-E02-T04 are Done and `make test CLUSTER=c0,c1` passes:

```
COMMIT READY: Cluster C1 — Local Environment

Suggested commit message:
  feat(c1): add Docker Compose local stack and C1 integration tests

  Implements docker-compose.yml (ContextForge + PostgreSQL 15 + Redis 7),
  local_up/down scripts, contextforge config template, synthetic data
  generator, and C1 test suite. Progressive test run c0+c1 passes.

Files to stage:
  docker-compose.yml
  config/contextforge.example.yaml
  scripts/local_up.sh
  scripts/local_down.sh
  scripts/generate_synthetic_data.py
  tests/fixtures/mcp_proxy_registration.json
  tests/fixtures/virtual_server_definition.json
  tests/fixtures/tool_invocation_request.json
  tests/test_c1_local_environment.py

Command:
  git add <files above> && git commit -m "feat(c1): add Docker Compose local stack and C1 integration tests"
```

---

## EPIC-MF-E03: ContextForge Baseline Validation

**Cluster:** C2  
**Phase:** 1  
**Status:** To Do  
**Priority:** Critical  
**Description:** With the local stack running, confirm that ContextForge itself is correctly configured — specifically that the AI Gateway and Config Registry are reachable via their HTTP APIs and that the container port exposure flag is set correctly. This is the first cluster that exercises ContextForge's own API.  
**Business value:** The root cause of the prior failed Cloud Run deployment was a missed configuration flag. This cluster exists to confirm that flag is set correctly and is verified by an automated test, so the same failure cannot propagate to GKE.  
**Postcondition of epic:** `make test CLUSTER=c2` passes. ContextForge health endpoints return 200. The container port exposure configuration is confirmed in the test report.

---

### MF-E03-T01: Resolve and document container port exposure configuration

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** S  
**Cluster:** C2

**Description:**  
Identify the exact ContextForge YAML configuration key that enables container port exposure (Q3). Verify it by setting it to `true` in the local `contextforge.yaml`, restarting the stack, and confirming the gateway is reachable. Document the key and its value in `config/contextforge.example.yaml` and in an ADR.

**Preconditions:**  
- MF-E02 epic is Done.
- IBM ContextForge documentation is accessible.

**Technical Requirements:**  
- The correct configuration key must be identified from IBM ContextForge documentation (not guessed).
- The value `true` must be the configuration that enables exposure.
- If the key name differs from the assumed pattern in `.env.example`, `.env.example` must be updated.
- An ADR (`doc/ADR/ADR-001-gke-over-cloud-run.md`) must document: the original Cloud Run failure, the root cause (this flag), the decision to use GKE, and the exact configuration that resolves the issue.

**Postconditions:**  
- `config/contextforge.example.yaml` contains the correct key with a comment explaining its necessity.
- `doc/ADR/ADR-001-gke-over-cloud-run.md` exists and documents the decision.
- Q3 is marked Resolved in `doc/Specify.md`.

**Acceptance Criteria:**  
1. The exact ContextForge configuration key for container port exposure is identified and documented.
2. Setting it to `true` in the local stack makes the gateway reachable on port 8080.
3. `config/contextforge.example.yaml` is updated with the correct key.
4. ADR-001 is written.
5. Q3 in `doc/Specify.md` is updated to Resolved.

**Test file:** `tests/test_c2_contextforge_baseline.py` — test `test_port_exposure_config_key_documented`  
**Dependencies:** MF-E02 epic Done  
**Blocks:** MF-E03-T02

**Definition of Done:**  
- [ ] Config key identified from IBM documentation.
- [ ] Local stack restarted with correct config and gateway reachable.
- [ ] ADR-001 written.
- [ ] Q3 resolved in Specify.md.

---

### MF-E03-T02: Validate AI Gateway health endpoint

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** S  
**Cluster:** C2

**Description:**  
Identify the correct health check endpoint for the ContextForge AI Gateway (port 8080) from IBM documentation. Confirm the endpoint path, expected HTTP status code, and expected response body. Write this into the test.

**Preconditions:**  
- MF-E03-T01 is Done.
- Local stack is running with correct container port exposure configuration.

**Technical Requirements:**  
- The health endpoint path is read from `config/contextforge.example.yaml` or `.env` — not hardcoded.
- The expected response body structure is defined as a `pydantic` model in the test module for contract validation.
- The test makes a real HTTP request using `httpx`.

**Postconditions:**  
- `GET <LOCAL_CF_GATEWAY_URL>/health` (or correct path) returns HTTP 200.
- Response body matches the documented contract.

**Acceptance Criteria:**  
1. The AI Gateway health endpoint path is documented in `config/contextforge.example.yaml`.
2. An HTTP GET to the endpoint returns HTTP 200.
3. The response body is validated against a `pydantic` contract model.
4. The test passes with the local stack running.

**Test file:** `tests/test_c2_contextforge_baseline.py` — test `test_gateway_health_endpoint_returns_200`  
**Dependencies:** MF-E03-T01  
**Blocks:** MF-E03-T03

**Definition of Done:**  
- [ ] Endpoint path documented.
- [ ] Pydantic contract model defined.
- [ ] `test_gateway_health_endpoint_returns_200` passes.

---

### MF-E03-T03: Validate Config Registry health endpoint and write test_c2

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** M  
**Cluster:** C2

**Description:**  
Mirror MF-E03-T02 for the Config Registry (port 8081). Then assemble the complete `test_c2_contextforge_baseline.py` test suite.

**Preconditions:**  
- MF-E03-T02 is Done.

**Technical Requirements:**

`tests/test_c2_contextforge_baseline.py` must define:
- `test_port_exposure_config_key_documented`: parses `config/contextforge.example.yaml`, asserts the container port exposure key is present and its value is the string `"true"` or equivalent.
- `test_gateway_health_endpoint_returns_200`: as defined in MF-E03-T02.
- `test_registry_health_endpoint_returns_200`: same for port 8081.
- `test_gateway_responds_to_mcp_protocol_version`: calls the MCP protocol version endpoint (if exposed by ContextForge) and validates the response.
- `test_config_registry_is_connected_to_database`: queries a registry status endpoint that confirms database connectivity (if available); otherwise documents why this test is deferred.

**Postconditions:**  
- `make test CLUSTER=c2` passes.
- Progressive run `make test CLUSTER=c0,c1,c2` passes.

**Acceptance Criteria:**  
1. All five tests in `test_c2_contextforge_baseline.py` are defined.
2. All five tests pass against the running local stack.
3. `make test CLUSTER=c0,c1,c2` exits with code 0.

**Test file:** `tests/test_c2_contextforge_baseline.py`  
**Dependencies:** MF-E03-T02  
**Blocks:** EPIC-MF-E04

**Definition of Done:**  
- [ ] All five tests pass.
- [ ] Progressive test run passes.

---

### Cluster C2 Commit Prompt

When all tickets MF-E03-T01 through MF-E03-T03 are Done and `make test CLUSTER=c0,c1,c2` passes:

```
COMMIT READY: Cluster C2 — ContextForge Baseline Validation

Suggested commit message:
  test(c2): validate ContextForge gateway and registry health locally

  Resolves container port exposure config (Q3), documents in ADR-001,
  confirms gateway (8080) and registry (8081) health endpoints return 200.
  Progressive test run c0+c1+c2 passes.

Files to stage:
  config/contextforge.example.yaml    (updated with correct keys)
  doc/Specify.md                      (Q3 resolved)
  doc/ADR/ADR-001-gke-over-cloud-run.md
  tests/test_c2_contextforge_baseline.py

Command:
  git add <files above> && git commit -m "test(c2): validate ContextForge gateway and registry health locally"
```

---

## EPIC-MF-E04: GKE Infrastructure

**Cluster:** C3  
**Phase:** 1  
**Status:** To Do  
**Priority:** Critical  
**Description:** Provision all GCP infrastructure and deploy the ContextForge stack to GKE. This is the largest cluster. It requires all open questions to be resolved before it begins. The local environment validated in C1 and C2 is replicated to GKE using the same configuration structure.  
**Business value:** Delivers the infrastructure outcome. Moves the system from local proof-of-concept to a shared, team-accessible environment in the GCP sandbox.  
**Postcondition of epic:** `kubectl get pods -n mcp-farm` shows all pods Running. Health endpoints return 200 from within the cluster. `make test CLUSTER=c3` passes.

---

### MF-E04-T01: Resolve all open questions Q1 through Q6

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** M  
**Cluster:** C3

**Description:**  
Before any GKE provisioning begins, all six open questions from `doc/Specify.md` Section 15 must be answered, documented, and their answers incorporated into the relevant configuration files and the Specify.md document.

**Preconditions:**  
- MF-E03 epic is Done.
- Access to IBM ContextForge documentation (Q1, Q3).
- Access to Chakri for Q2, Q5.
- Access to Lakshman for Q6.
- Access to Bala for Q4.

**Technical Requirements:**

For each question, the resolution must:
- Be recorded in `doc/Specify.md` Section 15 with the answer and the date resolved.
- Update `.env.example` with the correct variable names and example values.
- Update any affected config template files.

Q1 resolution: `CF_IMAGE_URI` and `CF_IMAGE_TAG` are set in `.env.example`.  
Q2 resolution: `GCP_PROJECT_ID` is set in `.env.example`.  
Q3 resolution: already done in C2 (MF-E03-T01).  
Q4 resolution: `GITLAB_OAUTH_CLIENT_ID` pattern is confirmed (static or dynamic).  
Q5 resolution: secret management approach is decided and documented in ADR-002.  
Q6 resolution: `GKE_NODE_MACHINE_TYPE` and `GKE_NODE_COUNT` are set in `.env.example`.

**Postconditions:**  
- All six questions in `doc/Specify.md` Section 15 show status Resolved.
- `.env.example` reflects all resolved values.

**Acceptance Criteria:**  
1. All six questions show Resolved in `doc/Specify.md`.
2. `.env.example` has no `<resolve-QN>` placeholders remaining.
3. `config/gke.example.yaml` is updated with resolved GKE parameters.

**Test file:** `tests/test_c3_gke_infrastructure.py` — test `test_all_open_questions_resolved`  
**Dependencies:** MF-E03 epic Done  
**Blocks:** MF-E04-T02

**Definition of Done:**  
- [ ] All six questions resolved.
- [ ] `.env.example` updated.
- [ ] `doc/Specify.md` updated.

---

### MF-E04-T02: Create Kubernetes manifests

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** L  
**Cluster:** C3

**Description:**  
Create all Kubernetes manifest files in `k8s/`. These manifests deploy ContextForge to the GKE cluster. They are the declarative source of truth for the GKE deployment state.

**Preconditions:**  
- MF-E04-T01 is Done (all questions resolved, GKE parameters known).

**Technical Requirements:**

`k8s/namespace.yaml`: Defines namespace `mcp-farm` with standard labels (`project: mcp-farm`, `managed-by: mcp-farm`).

`k8s/configmap.yaml`: Contains non-sensitive ContextForge configuration (ports, health check paths, gateway flags). Sensitive values are not in this file.

`k8s/secrets.example.yaml`: Template showing the shape of required Secrets (db credentials, Redis credentials, IBM entitlement key). Contains no real values. Comment on each entry explains the source.

`k8s/deployment.yaml`:
- `replicas: 1` for Phase 1.
- Image from `CF_IMAGE_URI:CF_IMAGE_TAG` (injected via Kustomize or envsubst at deploy time — not hardcoded).
- Environment variables sourced from ConfigMap and Secrets.
- Container port exposure flag set via environment variable from ConfigMap.
- Health probes: `livenessProbe` and `readinessProbe` on gateway health endpoint.
- `imagePullSecrets` referencing the IBM entitlement key secret.
- Resource requests and limits set (values from Q6 resolution).

`k8s/service.yaml`: ClusterIP service exposing ports 8080 and 8081.

`k8s/ingress.yaml`: GKE Ingress (or LoadBalancer Service, per Q6/Lakshman guidance) exposing the gateway externally.

All manifests use `namespace: mcp-farm`. No manifest contains a hardcoded image tag, credential, or project identifier.

**Postconditions:**  
- All six manifest files in `k8s/` are complete and validated with `kubectl apply --dry-run=client`.
- `k8s/secrets.example.yaml` is committed; actual Secrets are applied manually from `.env` and never committed.

**Acceptance Criteria:**  
1. All six manifest files exist.
2. `kubectl apply --dry-run=client -f k8s/` exits with code 0.
3. No hardcoded credential or project identifier in any manifest.
4. `k8s/secrets.example.yaml` contains the correct shape with no real values.
5. `imagePullSecrets` is configured for the IBM entitlement key.

**Test file:** `tests/test_c3_gke_infrastructure.py` — test `test_k8s_manifests_dry_run_valid`  
**Dependencies:** MF-E04-T01  
**Blocks:** MF-E04-T03

**Definition of Done:**  
- [ ] All six manifests created.
- [ ] `kubectl apply --dry-run=client` passes.
- [ ] No real secrets in committed files.

---

### MF-E04-T03: Create gke_provision.sh

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** L  
**Cluster:** C3

**Description:**  
Create `scripts/gke_provision.sh`. This script provisions all GCP-managed resources: the GKE cluster, Cloud SQL instance, and Memorystore instance. It is idempotent — running it against an already-provisioned environment exits with code 0 without duplicating resources.

**Preconditions:**  
- MF-E04-T01 is Done.
- `gcloud` is authenticated and pointing to the correct project.

**Technical Requirements:**  
- Accepts `--help`.
- Reads all parameters from environment variables (no hardcoded values).
- Creates GKE cluster if it does not exist; skips if it does.
- Creates Cloud SQL instance if it does not exist; skips if it does.
- Creates Cloud SQL database and user if they do not exist.
- Creates Memorystore instance if it does not exist; skips if it does.
- Enables required GCP APIs (`container.googleapis.com`, `sqladmin.googleapis.com`, `redis.googleapis.com`) — idempotent.
- Configures `kubectl` credentials for the cluster (`gcloud container clusters get-credentials`).
- On completion, prints a summary of all created resources and their connection details.
- On any failure, prints the exact failing command and exits with code 1.

**Postconditions:**  
- GKE cluster `mcp-farm-sandbox` exists and is reachable via `kubectl`.
- Cloud SQL instance `mcp-farm-pg` exists and PostgreSQL is accepting connections.
- Memorystore instance `mcp-farm-redis` exists and Redis is accepting connections.
- `kubectl get nodes` shows nodes in `Ready` state.

**Acceptance Criteria:**  
1. `gke_provision.sh --help` exits with code 0.
2. `gke_provision.sh` completes without error.
3. Running `gke_provision.sh` a second time exits with code 0 (idempotent).
4. `kubectl get nodes` shows all nodes as `Ready`.
5. Cloud SQL and Memorystore instances are visible in `gcloud sql instances list` and `gcloud redis instances list`.

**Test file:** `tests/test_c3_gke_infrastructure.py` — test `test_gcp_resources_provisioned`  
**Dependencies:** MF-E04-T02  
**Blocks:** MF-E04-T04

**Definition of Done:**  
- [ ] Script created and executable.
- [ ] Provisioning verified.
- [ ] Idempotency verified.
- [ ] `test_gcp_resources_provisioned` passes.

---

### MF-E04-T04: Create gke_deploy.sh and gke_teardown.sh

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** M  
**Cluster:** C3

**Description:**  
Create `scripts/gke_deploy.sh` (deploys Kubernetes manifests) and `scripts/gke_teardown.sh` (destroys all GKE and managed GCP resources). Both are idempotent.

**Preconditions:**  
- MF-E04-T03 is Done (cluster exists).
- Kubernetes Secrets have been applied manually from `.env` values.

**Technical Requirements:**

`gke_deploy.sh`:
- Accepts `--help`.
- Applies namespace manifest first, then ConfigMap, then Secrets (checks if they exist — does not re-apply credentials if already present, to avoid accidental rotation), then Deployment, Service, Ingress.
- Waits for the Deployment rollout to complete (`kubectl rollout status`).
- Prints the external IP or URL of the Ingress/LoadBalancer on success.
- Reads image tag from environment (`CF_IMAGE_TAG`).

`gke_teardown.sh`:
- Accepts `--help`.
- Prints a warning and requires confirmation (interactive `read` prompt or `--force` flag for non-interactive use).
- Deletes the GKE cluster.
- Deletes the Cloud SQL instance.
- Deletes the Memorystore instance.
- Is idempotent: resources that do not exist are silently skipped.

**Postconditions:**  
- After `gke_deploy.sh`: `kubectl get pods -n mcp-farm` shows ContextForge pods Running.
- After `gke_teardown.sh`: all GCP resources created by `gke_provision.sh` are gone.

**Acceptance Criteria:**  
1. `gke_deploy.sh` completes without error and pods reach `Running`.
2. `gke_deploy.sh` run twice exits with code 0 (idempotent).
3. `gke_teardown.sh --force` removes all resources without error.
4. After teardown, re-running `gke_provision.sh` and `gke_deploy.sh` restores the environment.

**Test file:** `tests/test_c3_gke_infrastructure.py` — test `test_gke_deployment_running`  
**Dependencies:** MF-E04-T03  
**Blocks:** MF-E04-T05

**Definition of Done:**  
- [ ] Both scripts created and executable.
- [ ] Deploy verified.
- [ ] Teardown verified.
- [ ] Idempotency verified for deploy.

---

### MF-E04-T05: Create gke.example.yaml and write test_c3_gke_infrastructure.py

**Type:** Task  
**Status:** To Do  
**Priority:** High  
**Complexity:** M  
**Cluster:** C3

**Description:**  
Create `config/gke.example.yaml` as the template for GKE deployment parameters. Assemble the complete `test_c3_gke_infrastructure.py` suite.

**Preconditions:**  
- MF-E04-T04 is Done.

**Technical Requirements:**

`config/gke.example.yaml`:
```yaml
cluster:
  name: <GKE_CLUSTER_NAME>
  project: <GCP_PROJECT_ID>
  region: <GCP_REGION>
  zone: <GCP_ZONE>
  node_machine_type: <GKE_NODE_MACHINE_TYPE>
  node_count: <GKE_NODE_COUNT>

namespace: <GKE_NAMESPACE>

cloud_sql:
  instance_name: <CLOUDSQL_INSTANCE_NAME>
  database_name: <CLOUDSQL_DATABASE_NAME>
  tier: <db-tier>

memorystore:
  instance_name: <MEMORYSTORE_INSTANCE_NAME>
  tier: BASIC
  size_gb: 1
```

`tests/test_c3_gke_infrastructure.py` must define:
- `test_all_open_questions_resolved`: parses `doc/Specify.md`, asserts no question shows status Open.
- `test_k8s_manifests_dry_run_valid`: runs `kubectl apply --dry-run=client -f k8s/`, asserts exit code 0.
- `test_gcp_resources_provisioned`: uses `gcloud` CLI (via `subprocess`) to list Cloud SQL and Memorystore instances, asserts both exist.
- `test_gke_pods_running`: runs `kubectl get pods -n <namespace> -o json`, asserts all pods show `Running` phase.
- `test_gateway_health_on_gke`: makes HTTP GET to the GKE-deployed gateway health endpoint, asserts HTTP 200 (requires `TEST_TARGET=gke` and `TEST_GATEWAY_BASE_URL` set to the GKE external address).

**Postconditions:**  
- `make test CLUSTER=c3` passes (requires `TEST_TARGET=gke`).
- Progressive run `make test CLUSTER=c0,c1,c2,c3` passes.

**Acceptance Criteria:**  
1. `config/gke.example.yaml` exists with all keys.
2. All five tests in `test_c3_gke_infrastructure.py` pass against the running GKE environment.
3. Progressive test run passes.

**Test file:** `tests/test_c3_gke_infrastructure.py`  
**Dependencies:** MF-E04-T04  
**Blocks:** EPIC-MF-E05

**Definition of Done:**  
- [ ] `gke.example.yaml` created.
- [ ] All five GKE tests pass.
- [ ] Progressive test run passes.

---

### Cluster C3 Commit Prompt

When all tickets MF-E04-T01 through MF-E04-T05 are Done and `make test CLUSTER=c0,c1,c2,c3` passes:

```
COMMIT READY: Cluster C3 — GKE Infrastructure

Suggested commit message:
  infra(c3): provision GKE cluster and deploy ContextForge to GCP sandbox

  Adds K8s manifests, gke_provision/deploy/teardown scripts, resolves all
  open questions (Q1-Q6). ContextForge running on GKE, health endpoints
  return 200. Progressive test run c0+c1+c2+c3 passes.

Files to stage:
  config/gke.example.yaml
  doc/Specify.md                    (all Q1-Q6 resolved)
  doc/ADR/ADR-002-managed-services-over-pvs.md
  k8s/namespace.yaml
  k8s/deployment.yaml
  k8s/service.yaml
  k8s/ingress.yaml
  k8s/configmap.yaml
  k8s/secrets.example.yaml
  scripts/gke_provision.sh
  scripts/gke_deploy.sh
  scripts/gke_teardown.sh
  tests/test_c3_gke_infrastructure.py
  .env.example                      (updated with resolved values)

Command:
  git add <files above> && git commit -m "infra(c3): provision GKE cluster and deploy ContextForge to GCP sandbox"
```

---

## EPIC-MF-E05: MCP Proxy Registration — GitLab

**Cluster:** C4  
**Phase:** 1  
**Status:** To Do  
**Priority:** High  
**Description:** Register the GitLab MCP server as a proxy in ContextForge. ContextForge handles OAuth 2.0 authentication to GitLab on behalf of the calling agent. The tools exposed by GitLab become discoverable through the ContextForge tools listing endpoint.  
**Business value:** Demonstrates the primary enterprise use case: an agent accessing a vendor-hosted, OAuth-protected MCP through a single governed gateway. This is the pattern that will be replicated for all future vendor MCP integrations.  
**Postcondition of epic:** `make test CLUSTER=c4` passes. GitLab MCP tools are visible in the ContextForge tools listing. The OAuth 2.0 flow is documented and reproducible.

---

### MF-E05-T01: Document GitLab OAuth 2.0 integration pattern

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** M  
**Cluster:** C4

**Description:**  
Before registering the proxy, document the OAuth 2.0 integration pattern between ContextForge and GitLab. Based on observations from the 2026-05-20 daily meeting, GitLab does not support OAuth 2.0 dynamic client registration (no `/.well-known/oauth-authorization-server` endpoint). This must be confirmed and the correct pattern (static client registration) documented.

**Preconditions:**  
- Q4 is resolved (MF-E04-T01).
- GitLab OAuth application credentials (`GITLAB_OAUTH_CLIENT_ID`, `GITLAB_OAUTH_CLIENT_SECRET`) are available.

**Technical Requirements:**  
- Confirm whether GitLab supports dynamic OAuth 2.0 discovery or requires static client registration.
- Document the exact OAuth 2.0 flow (authorisation code, client credentials, or token passthrough) that ContextForge uses for this proxy.
- Document the GitLab MCP URL and transport type (SSE or Streamable HTTP).
- Write this documentation as `doc/ADR/ADR-003-gitlab-mcp-oauth-pattern.md`.
- Update `.env.example` with any new variables identified.

**Postconditions:**  
- ADR-003 exists and documents the complete OAuth integration pattern.
- All required GitLab credentials are documented in `.env.example`.

**Acceptance Criteria:**  
1. ADR-003 exists.
2. The OAuth 2.0 pattern (static vs dynamic) is stated unambiguously with evidence.
3. `.env.example` is updated with all required GitLab variables.

**Test file:** `tests/test_c4_mcp_proxy_registration.py` — test `test_gitlab_oauth_config_documented`  
**Dependencies:** MF-E04 epic Done; Q4 resolved  
**Blocks:** MF-E05-T02

**Definition of Done:**  
- [ ] ADR-003 written.
- [ ] OAuth pattern confirmed.
- [ ] `.env.example` updated.

---

### MF-E05-T02: Register GitLab MCP proxy in ContextForge (local)

**Type:** Task  
**Status:** To Do  
**Priority:** Critical  
**Complexity:** M  
**Cluster:** C4

**Description:**  
Register the GitLab MCP server as a proxy in the local ContextForge instance. Use the ContextForge API or configuration file (whichever is the correct registration mechanism per IBM documentation) to add the proxy definition. Confirm the tools listing returns GitLab tools.

**Preconditions:**  
- MF-E05-T01 is Done.
- Local stack is running.
- GitLab OAuth credentials are in `.env`.

**Technical Requirements:**  
- The proxy registration payload is defined in `config/contextforge.example.yaml` under the `proxy:` section.
- No OAuth credential is hardcoded in any configuration file.
- Credentials are injected via environment variables at runtime.
- The registration is performed via the ContextForge API (using `httpx`) in a script or via configuration file mount — whichever is the supported mechanism.
- After registration, `GET <gateway>/v1/tools` (or correct endpoint) returns a JSON array containing at least one tool from the GitLab MCP.

**Postconditions:**  
- GitLab MCP tools are visible in the ContextForge tools listing locally.
- The proxy definition is in `config/contextforge.example.yaml` (template form, no real credentials).

**Acceptance Criteria:**  
1. `GET <gateway>/v1/tools` returns HTTP 200 with a JSON array.
2. The array contains at least one tool with `source: gitlab` (or equivalent field identifying the origin).
3. The proxy definition is in the config template.
4. No credential is in any committed file.

**Test file:** `tests/test_c4_mcp_proxy_registration.py` — test `test_gitlab_tools_visible_in_listing`  
**Dependencies:** MF-E05-T01  
**Blocks:** MF-E05-T03

**Definition of Done:**  
- [ ] Proxy registered locally.
- [ ] Tools listing returns GitLab tools.
- [ ] No credentials committed.

---

### MF-E05-T03: Register GitLab MCP proxy on GKE and write test_c4

**Type:** Task  
**Status:** To Do  
**Priority:** High  
**Complexity:** M  
**Cluster:** C4

**Description:**  
Replicate the GitLab proxy registration on the GKE-deployed ContextForge instance. Assemble the complete C4 test suite.

**Preconditions:**  
- MF-E05-T02 is Done.
- GKE stack is running (C3 complete).

**Technical Requirements:**

`tests/test_c4_mcp_proxy_registration.py` must define:
- `test_gitlab_oauth_config_documented`: parses ADR-003, asserts it exists and contains the OAuth pattern declaration.
- `test_gitlab_tools_visible_in_listing`: calls `GET <gateway>/v1/tools`, asserts GitLab tools present. Parameterised to run against local and GKE targets.
- `test_gitlab_proxy_responds_to_tool_call`: invokes one read-only GitLab tool through ContextForge (e.g., list projects), asserts a valid response. Uses synthetic data for any required parameters.
- `test_no_credentials_in_committed_files`: scans all committed files for patterns matching OAuth tokens or client secrets.
- `test_progressive_c0_through_c4`: runs `make test CLUSTER=c0,c1,c2,c3,c4` as a subprocess, asserts exit code 0.

**Postconditions:**  
- All five C4 tests pass against GKE.
- Progressive test run `make test CLUSTER=c0,c1,c2,c3,c4` passes.

**Acceptance Criteria:**  
1. All five tests defined and passing.
2. Tests are parameterised to run against both `local` and `gke` targets.
3. Progressive test run passes.

**Test file:** `tests/test_c4_mcp_proxy_registration.py`  
**Dependencies:** MF-E05-T02  
**Blocks:** EPIC-MF-E06

**Definition of Done:**  
- [ ] All five tests pass.
- [ ] GKE proxy registration confirmed.
- [ ] Progressive test run passes.

---

### Cluster C4 Commit Prompt

When all tickets MF-E05-T01 through MF-E05-T03 are Done and `make test CLUSTER=c0,c1,c2,c3,c4` passes:

```
COMMIT READY: Cluster C4 — GitLab MCP Proxy Registration

Suggested commit message:
  feat(c4): register GitLab MCP proxy in ContextForge with OAuth 2.0

  Adds GitLab proxy config template, ADR-003 (OAuth pattern), and C4
  test suite. GitLab tools visible in gateway listing on both local and
  GKE targets. Progressive test run c0+c1+c2+c3+c4 passes.

Files to stage:
  config/contextforge.example.yaml    (updated proxy section)
  doc/ADR/ADR-003-gitlab-mcp-oauth-pattern.md
  .env.example                        (updated with GitLab variables)
  tests/test_c4_mcp_proxy_registration.py

Command:
  git add <files above> && git commit -m "feat(c4): register GitLab MCP proxy in ContextForge with OAuth 2.0"
```

---

## EPIC-MF-E06: Virtual Server Registration

**Cluster:** C5  
**Phase:** 1  
**Status:** To Do  
**Priority:** High  
**Description:** Create and register a native ContextForge virtual server — a bundle of tool definitions that are exposed as a single MCP endpoint without requiring an external MCP server. Verify that tools can be invoked end-to-end through the gateway.  
**Business value:** Demonstrates ContextForge's ability to host its own tools, not just proxy external ones. This is the pattern used for internal tool exposure without requiring a separately deployed MCP server.  
**Postcondition of epic:** `make test CLUSTER=c5` passes. A virtual server with two tools is reachable via the gateway. Tool invocation returns a valid response.

---

### MF-E06-T01: Define virtual server schema and synthetic tool definitions

**Type:** Task  
**Status:** To Do  
**Priority:** High  
**Complexity:** M  
**Cluster:** C5

**Description:**  
Design the virtual server to be registered in ContextForge. The virtual server contains two tool definitions. Tool definitions are generated as synthetic data by `generate_synthetic_data.py` using `faker` with seed 42. The tool definitions must be valid per the MCP tool specification (name, description, input schema).

**Preconditions:**  
- MF-E04 epic is Done.
- MCP tool specification is understood (from IBM ContextForge documentation).

**Technical Requirements:**  
- Virtual server name: `test-virtual-server` (read from `VIRTUAL_SERVER_NAME` environment variable).
- Tool 1 name: `tool-alpha` — a tool that accepts a `query` parameter (string) and returns a synthetic text response.
- Tool 2 name: `tool-beta` — a tool that accepts an `entity_id` parameter (string, UUID format) and returns a synthetic JSON object.
- Both tools are defined with valid JSON Schema for their input parameters.
- All tool names, descriptions, and parameter definitions are generated by `generate_synthetic_data.py` — not hardcoded.
- The virtual server definition is written to `tests/fixtures/virtual_server_definition.json`.
- `config/contextforge.example.yaml` is updated with the virtual server template section.

**Postconditions:**  
- `tests/fixtures/virtual_server_definition.json` exists and is valid JSON.
- The virtual server definition conforms to the ContextForge virtual server schema.

**Acceptance Criteria:**  
1. `tests/fixtures/virtual_server_definition.json` contains two tool definitions.
2. Both tools have valid `name`, `description`, and `inputSchema` fields.
3. The fixture is regenerated identically by `make generate-data`.
4. `config/contextforge.example.yaml` shows the virtual server template.

**Test file:** `tests/test_c5_virtual_server.py` — test `test_virtual_server_definition_valid`  
**Dependencies:** MF-E04 epic Done  
**Blocks:** MF-E06-T02

**Definition of Done:**  
- [ ] Fixture file created.
- [ ] Schema validated.
- [ ] Config template updated.

---

### MF-E06-T02: Register virtual server and validate end-to-end invocation

**Type:** Task  
**Status:** To Do  
**Priority:** High  
**Complexity:** M  
**Cluster:** C5

**Description:**  
Register the virtual server in ContextForge (both local and GKE). Invoke `tool-alpha` through the gateway and verify the response is well-formed.

**Preconditions:**  
- MF-E06-T01 is Done.
- Local stack and GKE stack are running.

**Technical Requirements:**  
- Registration is performed via the ContextForge API using the fixture in `tests/fixtures/virtual_server_definition.json`.
- After registration, `GET <gateway>/v1/tools` includes `tool-alpha` and `tool-beta` in its response.
- Invocation request body is taken from `tests/fixtures/tool_invocation_request.json` (generated by `generate_synthetic_data.py`).
- The response to `tool-alpha` invocation is validated against a `pydantic` contract model defined in the test module.

**Postconditions:**  
- Virtual server registered on both local and GKE.
- `tool-alpha` invocation returns a valid, well-formed response.

**Acceptance Criteria:**  
1. `GET <gateway>/v1/tools` includes `tool-alpha` and `tool-beta`.
2. Invoking `tool-alpha` with the fixture request body returns HTTP 200.
3. The response body validates against the pydantic contract model.
4. Registration is idempotent: re-registering the same virtual server produces no error.

**Test file:** `tests/test_c5_virtual_server.py` — test `test_virtual_server_tool_invocation`  
**Dependencies:** MF-E06-T01  
**Blocks:** MF-E06-T03

**Definition of Done:**  
- [ ] Virtual server registered locally and on GKE.
- [ ] Tool invocation verified.
- [ ] Idempotency verified.

---

### MF-E06-T03: Write test_c5_virtual_server.py

**Type:** Task  
**Status:** To Do  
**Priority:** High  
**Complexity:** M  
**Cluster:** C5

**Description:**  
Assemble the complete C5 test suite as the final implementation cluster.

**Preconditions:**  
- MF-E06-T02 is Done.

**Technical Requirements:**

`tests/test_c5_virtual_server.py` must define:
- `test_virtual_server_definition_valid`: loads `tests/fixtures/virtual_server_definition.json`, validates it against the expected schema with pydantic.
- `test_virtual_server_tools_in_listing`: calls `GET <gateway>/v1/tools`, asserts `tool-alpha` and `tool-beta` are present.
- `test_tool_alpha_invocation_returns_200`: invokes `tool-alpha` via the gateway, asserts HTTP 200 and valid response contract.
- `test_tool_beta_invocation_returns_200`: same for `tool-beta`.
- `test_full_progressive_suite`: runs `make test CLUSTER=c0,c1,c2,c3,c4,c5` as a subprocess, asserts exit code 0.

**Postconditions:**  
- All five tests pass.
- The full progressive test suite `c0` through `c5` passes.
- `reports/test-results.xml` contains results for all tests across all clusters.

**Acceptance Criteria:**  
1. All five C5 tests pass.
2. Progressive test run `make test CLUSTER=c0,c1,c2,c3,c4,c5` exits with code 0.
3. `reports/test-results.xml` is produced with all cluster results.

**Test file:** `tests/test_c5_virtual_server.py`  
**Dependencies:** MF-E06-T02  
**Blocks:** EPIC-MF-E07

**Definition of Done:**  
- [ ] All five tests pass.
- [ ] Full progressive suite passes.
- [ ] XML report confirmed.

---

### Cluster C5 Commit Prompt

When all tickets MF-E06-T01 through MF-E06-T03 are Done and full progressive suite passes:

```
COMMIT READY: Cluster C5 — Virtual Server Registration

Suggested commit message:
  feat(c5): register virtual server with two tools and validate invocation

  Adds virtual server definition, registers tool-alpha and tool-beta in
  ContextForge on local and GKE. Full progressive test suite c0-c5 passes.

Files to stage:
  config/contextforge.example.yaml    (updated virtual_servers section)
  tests/fixtures/virtual_server_definition.json
  tests/fixtures/tool_invocation_request.json
  tests/test_c5_virtual_server.py
  scripts/generate_synthetic_data.py  (final version)

Command:
  git add <files above> && git commit -m "feat(c5): register virtual server with two tools and validate invocation"
```

---

## EPIC-MF-E07: Documentation and Runbook

**Cluster:** C6  
**Phase:** 1 (parallel with C3–C5)  
**Status:** To Do  
**Priority:** High  
**Description:** Produce the deployment runbook, architecture decision records, and final README that constitute the operational outcome of this ticket. This epic runs in parallel with C3–C5 — documentation is updated as each cluster is completed, not deferred to the end.  
**Business value:** Without documentation, the infrastructure outcome and functional outcome cannot be operationalised by the team. The runbook is a Phase 1 deliverable, not an afterthought.  
**Postcondition of epic:** Any team member can reproduce the full environment from the runbook alone.

---

### MF-E07-T01: Write deployment runbook

**Type:** Task  
**Status:** To Do  
**Priority:** High  
**Complexity:** L  
**Cluster:** C6

**Description:**  
Write `doc/Runbook.md`. This is the human-readable, step-by-step guide for deploying, operating, and troubleshooting the MCP Farm. It is complete enough that a team member with GCP access but no prior context on this project can reproduce the environment.

**Preconditions:**  
- C3 is Done (GKE infrastructure exists and is understood).

**Technical Requirements:**

The runbook must contain:

1. **Prerequisites section**: exact tools required, exact versions, and verification commands.
2. **First-time setup section**: clone, populate `.env`, run `scripts/install.sh`, verify setup.
3. **Local environment section**: start, verify, stop. Expected output for each command.
4. **GKE provisioning section**: exact `gcloud` and `kubectl` commands with expected output.
5. **GKE deployment section**: exact commands, expected pod state, health check URLs.
6. **MCP proxy registration section**: exact steps to register GitLab proxy, including OAuth setup.
7. **Virtual server registration section**: exact steps to register the test virtual server.
8. **Verification section**: exact test commands and expected output.
9. **Teardown section**: exact commands to destroy all resources.
10. **Known issues and resolutions section**: documents the Cloud Run port exposure failure (from 2026-05-20) and its resolution, and any issues encountered during C3–C5.

All commands in the runbook are presented verbatim (copy-pasteable). All expected outputs are shown. No step is omitted because it seems obvious.

**Postconditions:**  
- `doc/Runbook.md` exists.
- A second team member can reproduce the GKE environment by following the runbook with no additional guidance.

**Acceptance Criteria:**  
1. All ten sections are present.
2. Every `scripts/` command is covered.
3. The Cloud Run failure is documented in Known Issues.
4. A peer review by one team member confirms the runbook is reproducible.

**Test file:** `tests/test_c5_virtual_server.py` — `test_full_progressive_suite` is the proxy for runbook correctness (if the suite passes from a clean environment, the runbook works).  
**Dependencies:** C3 Done  
**Blocks:** MF-E07-T02

---

### MF-E07-T02: Write Architecture Decision Records

**Type:** Task  
**Status:** To Do  
**Priority:** Medium  
**Complexity:** M  
**Cluster:** C6

**Description:**  
Write the following ADRs. ADR-001 and ADR-003 may already exist from C2 and C4; this ticket finalises and completes them.

- `ADR-001-gke-over-cloud-run.md`: GKE chosen over Cloud Run. Root cause of Cloud Run failure. Decision criteria.
- `ADR-002-managed-services-over-pvs.md`: Cloud SQL and Memorystore chosen over in-cluster PostgreSQL and Redis with PVs. Decision criteria (per Lakshman's direction in 2026-05-20 meeting).
- `ADR-003-gitlab-mcp-oauth-pattern.md`: Static OAuth 2.0 client registration used for GitLab proxy. Evidence that dynamic discovery is not supported.

Each ADR follows the format:
```
# ADR-NNN: Title
Date: YYYY-MM-DD
Status: Accepted
Context: <why a decision was needed>
Decision: <what was decided>
Consequences: <what changes as a result>
Evidence: <references, commands, or observations that support the decision>
```

**Acceptance Criteria:**  
1. All three ADRs exist in `doc/ADR/`.
2. Each ADR follows the format above.
3. ADR-001 references the 2026-05-20 daily meeting and the specific configuration flag.
4. ADR-002 references Lakshman's direction.
5. ADR-003 references the MCP Inspector observations from the 2026-05-20 meeting.

**Dependencies:** MF-E07-T01  
**Blocks:** MF-E07-T03

---

### MF-E07-T03: Update README.md

**Type:** Task  
**Status:** To Do  
**Priority:** Medium  
**Complexity:** S  
**Cluster:** C6

**Description:**  
Replace the placeholder `README.md` with a complete project entry point. The README is the first document a new team member or agent reads. It must orient quickly and delegate to the detailed documents.

**Technical Requirements:**

The README must contain:
1. Project name and one-paragraph description.
2. Link to `doc/Specify.md` (specification).
3. Link to `doc/Plan.md` (this document).
4. Link to `doc/Runbook.md` (deployment).
5. Quick-start section: minimum commands to get local environment running (3-5 commands, referencing the runbook for detail).
6. Architecture diagram (same ASCII diagram as in `doc/Specify.md` Section 9).
7. Technology stack table.
8. Test execution section: `make test` and `make test CLUSTER=<id>`.
9. Current status: Epic-level completion table showing which clusters are Done.

**Acceptance Criteria:**  
1. All nine sections present.
2. All links to other documents are correct (relative paths, verified to exist).
3. Quick-start commands work from a configured environment.
4. No placeholder text remains.

**Dependencies:** MF-E07-T02  
**Blocks:** Cluster C6 commit

---

### Cluster C6 Commit Prompt

When all tickets MF-E07-T01 through MF-E07-T03 are Done:

```
COMMIT READY: Cluster C6 — Documentation and Runbook

Suggested commit message:
  docs(c6): add deployment runbook, ADRs, and final README

  Completes operational documentation: Runbook.md covering full
  lifecycle, ADR-001/002/003, and README entry point. Phase 1
  all acceptance criteria satisfied.

Files to stage:
  doc/Runbook.md
  doc/ADR/ADR-001-gke-over-cloud-run.md
  doc/ADR/ADR-002-managed-services-over-pvs.md
  doc/ADR/ADR-003-gitlab-mcp-oauth-pattern.md
  README.md

Command:
  git add <files above> && git commit -m "docs(c6): add deployment runbook, ADRs, and final README"
```

---

## Section 4 — Dependency Graph

The following shows the critical path and parallelism constraints across all epics.

```
E01 (C0) --> E02 (C1) --> E03 (C2) --> E04 (C3) --> E05 (C4) --> E06 (C5)
                                           |
                                           +--> E07 (C6, parallel) -------> closes with E06
```

No epic can begin until the preceding epic on the critical path is fully Done. E07 (C6) may proceed from C3 onward and finalises after C5.

Within each epic, tickets are ordered and must be completed sequentially unless explicitly noted as parallelisable.

---

## Section 5 — Open Questions Tracker

This table mirrors `doc/Specify.md` Section 15 and is the working copy updated during implementation.

| ID | Question | Responsible | Status | Resolution |
|---|---|---|---|---|
| Q1 | IBM ContextForge image URI and entitlement key | Alberto / Kashyap | Open | — |
| Q2 | GCP sandbox project ID | Chakri | Open | — |
| Q3 | ContextForge container port exposure config key | Alberto | Open | Resolved in C2 |
| Q4 | GitLab OAuth 2.0 type: static or dynamic | Bala | Open | Resolved in C4 |
| Q5 | GCP Secret Manager availability in sandbox | Chakri | Open | Resolved in C3 |
| Q6 | Approved GKE node machine type and count | Lakshman | Open | Resolved in C3 |

---

## Section 6 — Project-Level Acceptance Criteria Cross-Reference

Each project-level acceptance criterion from `doc/Specify.md` Section 16 is mapped to the ticket that satisfies it.

| AC# | Criterion | Satisfied by |
|---|---|---|
| AC-1 | GKE cluster reachable via kubectl | MF-E04-T03 |
| AC-2 | All ContextForge pods Running | MF-E04-T04 |
| AC-3 | AI Gateway health endpoint returns 200 | MF-E03-T02 |
| AC-4 | Config Registry health endpoint returns 200 | MF-E03-T03 |
| AC-5 | Tools listing returns GitLab MCP tools | MF-E05-T02 |
| AC-6 | `make test` passes with exit code 0 | MF-E06-T03 |
| AC-7 | `install.sh` + `gke_deploy.sh` reproducible | MF-E04-T04 |
| AC-8 | Deployment runbook complete | MF-E07-T01 |
| AC-9 | All open questions resolved | MF-E04-T01 |
| AC-10 | No secret in any committed file | MF-E01-T02, MF-E04-T02, MF-E05-T03 |
