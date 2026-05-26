"""Cluster C2 — ContextForge Baseline Validation tests.

Test classes:
  TestContextForgeBaselineStructure   — structural tests (always run, no stack required)
  TestContextForgeBaselineIntegration — health endpoint validation (require_full_stack)

Run structural tests only (no stack needed):
  make test CLUSTER=c2

Run integration tests (full stack required, Q1 must be resolved first):
  make local-up && make test CLUSTER=c2

Progressive run (C0 + C1 + C2):
  make test CLUSTER=c0,c1,c2
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Structural tests — always run, no running services required
# ---------------------------------------------------------------------------


class TestContextForgeBaselineStructure:
    def test_adr_001_exists(self) -> None:
        """doc/ADR/ADR-001-gke-over-cloud-run.md must exist."""
        adr_path = _REPO_ROOT / "doc" / "ADR" / "ADR-001-gke-over-cloud-run.md"
        assert adr_path.is_file(), (
            "ADR-001 not found. It documents the Cloud Run failure root causes and "
            "the decision to use GKE. See doc/Plan.md MF-E03-T01."
        )

    def test_adr_001_documents_expose_flag(self) -> None:
        """ADR-001 must reference the expose_container_port configuration flag."""
        adr_path = _REPO_ROOT / "doc" / "ADR" / "ADR-001-gke-over-cloud-run.md"
        content = adr_path.read_text()
        assert "expose_container_port" in content, (
            "ADR-001 must document the expose_container_port flag — "
            "this is a root cause of the Cloud Run deployment failure."
        )

    def test_configmap_sets_correct_port_and_host(self) -> None:
        """k8s/configmap.yaml must set PORT=4444 and HOST=0.0.0.0.

        Q1 resolved 2026-05-25: ContextForge binds to HOST:PORT. HOST must be 0.0.0.0
        (not the default 127.0.0.1) so Kubernetes liveness/readiness probes can reach it.
        """
        configmap_path = _REPO_ROOT / "k8s" / "configmap.yaml"
        assert configmap_path.is_file(), "k8s/configmap.yaml not found."
        content = configmap_path.read_text()
        assert 'PORT: "4444"' in content, (
            'k8s/configmap.yaml must contain PORT: "4444". '
            "ContextForge listens on port 4444 by default."
        )
        assert 'HOST: "0.0.0.0"' in content, (
            'k8s/configmap.yaml must contain HOST: "0.0.0.0". '
            "Default of 127.0.0.1 makes Kubernetes probes fail — loopback is unreachable from the kubelet."
        )

    def test_docker_compose_sets_port_and_host(self) -> None:
        """docker-compose.yml contextforge service must pass PORT and HOST via env vars."""
        compose_path = _REPO_ROOT / "docker-compose.yml"
        assert compose_path.is_file(), "docker-compose.yml not found."
        data = yaml.safe_load(compose_path.read_text())
        cf_env = data.get("services", {}).get("contextforge", {}).get("environment", {})
        assert "PORT" in cf_env, (
            "docker-compose.yml contextforge service must declare PORT in its environment block."
        )
        assert "HOST" in cf_env, (
            "docker-compose.yml contextforge service must declare HOST in its environment block."
        )

    def test_health_paths_present_in_env_example(self) -> None:
        """.env.example must declare CF_GATEWAY_HEALTH_PATH and CF_REGISTRY_HEALTH_PATH."""
        content = (_REPO_ROOT / ".env.example").read_text()
        for var in ("CF_GATEWAY_HEALTH_PATH", "CF_REGISTRY_HEALTH_PATH"):
            assert var in content, (
                f"{var} not found in .env.example. "
                "Health endpoint paths must be configurable via environment variables."
            )

    def test_health_paths_in_contextforge_config_template(self) -> None:
        """config/contextforge.example.yaml must include health_path under gateway and registry."""
        config_path = _REPO_ROOT / "config" / "contextforge.example.yaml"
        assert config_path.is_file(), "config/contextforge.example.yaml not found."
        content = config_path.read_text()
        assert "health_path" in content, (
            "config/contextforge.example.yaml must include health_path keys under "
            "the gateway and registry sections."
        )
        assert "CF_GATEWAY_HEALTH_PATH" in content, (
            "gateway.health_path must reference CF_GATEWAY_HEALTH_PATH env var."
        )
        assert "CF_REGISTRY_HEALTH_PATH" in content, (
            "registry.health_path must reference CF_REGISTRY_HEALTH_PATH env var."
        )

    def test_q3_documented_as_assumed_in_specify(self) -> None:
        """doc/Specify.md Q3 row must be marked Assumed (not Open) after ADR-001 was written."""
        content = (_REPO_ROOT / "doc" / "Specify.md").read_text()
        q3_line = next(
            (line for line in content.splitlines() if line.strip().startswith("| Q3 |")),
            None,
        )
        assert q3_line is not None, (
            "Q3 row not found in doc/Specify.md Section 15."
        )
        assert "Assumed" in q3_line, (
            "Q3 in doc/Specify.md must be marked 'Assumed' now that ADR-001 documents "
            "the assumed configuration key (gateway.expose_container_port: true). "
            f"Current Q3 row: {q3_line.strip()!r}"
        )

    def test_adr_directory_exists(self) -> None:
        """doc/ADR/ directory must exist."""
        assert (_REPO_ROOT / "doc" / "ADR").is_dir(), (
            "doc/ADR/ directory not found."
        )


# ---------------------------------------------------------------------------
# Integration tests — require the full ContextForge stack
# These tests are skipped until Q1 (CF_IMAGE_URI) is resolved and the
# stack is started with: make local-up
# ---------------------------------------------------------------------------


class TestContextForgeBaselineIntegration:
    @pytest.fixture(autouse=True)
    def _need_full_stack(self, require_full_stack: None) -> None:
        pass

    def test_gateway_health_endpoint_returns_200(
        self, gateway_base_url: str
    ) -> None:
        """GET {gateway_base_url}{CF_GATEWAY_HEALTH_PATH} must return HTTP 200."""
        import httpx

        health_path = os.environ.get("CF_GATEWAY_HEALTH_PATH", "/health")
        url = gateway_base_url.rstrip("/") + health_path
        response = httpx.get(url, timeout=5.0)
        assert response.status_code == 200, (
            f"Gateway health endpoint {url!r} returned HTTP {response.status_code}. "
            "Expected 200. If the path is wrong, update CF_GATEWAY_HEALTH_PATH in .env "
            "and update the Unresolved Items table in ADR-001."
        )

    def test_registry_health_endpoint_returns_200(
        self, registry_base_url: str
    ) -> None:
        """GET {registry_base_url}{CF_REGISTRY_HEALTH_PATH} must return HTTP 200."""
        import httpx

        health_path = os.environ.get("CF_REGISTRY_HEALTH_PATH", "/health")
        url = registry_base_url.rstrip("/") + health_path
        response = httpx.get(url, timeout=5.0)
        assert response.status_code == 200, (
            f"Registry health endpoint {url!r} returned HTTP {response.status_code}. "
            "Expected 200. If the path is wrong, update CF_REGISTRY_HEALTH_PATH in .env "
            "and update the Unresolved Items table in ADR-001."
        )

    def test_contextforge_health_endpoint_responds(
        self, gateway_base_url: str
    ) -> None:
        """ContextForge /health endpoint must return HTTP 200.

        Q1 resolved 2026-05-25: ContextForge is a single FastAPI app on port 4444.
        Gateway (/gateways) and server registry (/servers) are both served on the same port.
        """
        import httpx
        from urllib.parse import urlparse

        health_path = os.environ.get("CF_GATEWAY_HEALTH_PATH", "/health")
        url = gateway_base_url.rstrip("/") + health_path
        port = urlparse(gateway_base_url).port or 4444

        response = httpx.get(url, timeout=5.0)
        assert response.status_code == 200, (
            f"ContextForge health endpoint {url!r} returned HTTP {response.status_code}. "
            f"Expected 200 on port {port}."
        )

    def test_gateway_health_implies_expose_flag_active(
        self, gateway_base_url: str
    ) -> None:
        """A 200 response from the gateway health endpoint confirms the expose_container_port flag is active.

        If this test passes, the Cloud Run failure root cause (missing expose flag) is resolved
        in the local Docker Compose environment. See ADR-001.
        """
        import httpx

        health_path = os.environ.get("CF_GATEWAY_HEALTH_PATH", "/health")
        url = gateway_base_url.rstrip("/") + health_path
        try:
            response = httpx.get(url, timeout=5.0)
        except httpx.ConnectError as exc:
            pytest.fail(
                f"Gateway port is not reachable: {exc}. "
                "This likely means CF_EXPOSE_CONTAINER_PORT is not set to true in the "
                "running container. Check docker-compose.yml and .env."
            )
        assert response.status_code == 200, (
            f"Gateway returned HTTP {response.status_code}. "
            "Expected 200 — a non-200 may indicate the gateway started but is misconfigured."
        )
