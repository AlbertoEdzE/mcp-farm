.PHONY: help install local-up local-down gke-provision gke-deploy gke-teardown \
        test lint typecheck generate-data register-proxy clean

SHELL  := /bin/bash
CLUSTER ?= all

help: ## Print all available targets and their descriptions
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "%-20s %s\n", $$1, $$2}'

install: ## Install system prerequisites check and Python virtual environment
	@scripts/install.sh

local-up: ## Start local Docker Compose stack (ContextForge + PostgreSQL + Redis)
	@scripts/local_up.sh

local-down: ## Stop local Docker Compose stack and remove volumes
	@scripts/local_down.sh

gke-provision: ## Provision GKE cluster, Cloud SQL, and Memorystore on GCP
	@scripts/gke_provision.sh

gke-deploy: ## Deploy Kubernetes manifests to the GKE cluster
	@scripts/gke_deploy.sh

gke-teardown: ## Destroy all GKE and managed GCP resources (destructive)
	@scripts/gke_teardown.sh

test: ## Run test suite. Filter by cluster: make test CLUSTER=c0 or CLUSTER=c0,c1
	@scripts/run_tests.sh $(if $(filter all,$(CLUSTER)),, --cluster $(CLUSTER))

lint: ## Run ruff linter on all Python files
	@ruff check .

typecheck: ## Run mypy type checker on tests and scripts
	@mypy tests/ scripts/generate_synthetic_data.py

generate-data: ## Generate deterministic synthetic test data fixtures
	@python scripts/generate_synthetic_data.py

register-proxy: ## Register the GitLab MCP proxy with the running ContextForge Config Registry
	@.venv/bin/python scripts/register_proxy.py

clean: ## Remove generated artefacts (__pycache__, .pytest_cache, reports/)
	@find . -type d -name __pycache__ -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf reports/
	@echo "Clean complete."
