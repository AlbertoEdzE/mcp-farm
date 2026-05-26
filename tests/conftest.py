from __future__ import annotations

import json
import os
import socket
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv
from faker import Faker

_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_SEED = 42

# Load .env if present. Does not override variables already set in the environment.
load_dotenv(_REPO_ROOT / ".env")


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def fake() -> Faker:
    """Deterministic Faker instance seeded from TEST_SYNTHETIC_DATA_SEED (default 42)."""
    seed = int(os.environ.get("TEST_SYNTHETIC_DATA_SEED", _DEFAULT_SEED))
    instance = Faker()
    instance.seed_instance(seed)
    return instance


@pytest.fixture(scope="session")
def env() -> dict[str, str]:
    """All current environment variables as an immutable dict."""
    return dict(os.environ)


@pytest.fixture(scope="session")
def gateway_base_url() -> str:
    """Base URL of the ContextForge AI Gateway, read from TEST_GATEWAY_BASE_URL."""
    return os.environ.get("TEST_GATEWAY_BASE_URL", "http://localhost:4444")


@pytest.fixture(scope="session")
def registry_base_url() -> str:
    """Base URL of the ContextForge Config Registry, read from TEST_REGISTRY_BASE_URL."""
    return os.environ.get("TEST_REGISTRY_BASE_URL", "http://localhost:4444")


@pytest.fixture(scope="session")
def test_target() -> str:
    """Deployment target for integration tests. Values: 'local' or 'gke'."""
    return os.environ.get("TEST_TARGET", "local")


# ---------------------------------------------------------------------------
# TCP availability helpers (utility — used by C2+ for direct port checks)
# ---------------------------------------------------------------------------


def _tcp_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


@pytest.fixture(scope="session")
def gateway_reachable() -> bool:
    """True if the local ContextForge AI Gateway TCP port is accepting connections."""
    port = int(os.environ.get("LOCAL_CF_GATEWAY_PORT", "4444"))
    return _tcp_reachable("localhost", port)


@pytest.fixture(scope="session")
def registry_reachable() -> bool:
    """True if the local ContextForge Config Registry TCP port is accepting connections."""
    port = int(os.environ.get("LOCAL_CF_REGISTRY_PORT", "4444"))
    return _tcp_reachable("localhost", port)


@pytest.fixture(scope="session")
def contextforge_image_resolved() -> bool:
    """True if CF_IMAGE_URI has been resolved from the Q1 placeholder."""
    uri = os.environ.get("CF_IMAGE_URI", "<resolve-Q1>")
    return bool(uri) and not uri.startswith("<")


# ---------------------------------------------------------------------------
# Docker Compose state fixture
# Parses `docker compose ps --format json` for the project stack.
# Returns an empty dict if docker compose is not running or docker is unavailable.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def docker_compose_services() -> dict[str, str]:
    """Map of service name to health status from the project docker compose stack.

    Returns {} if docker is not available or no services are running.
    Health values are lowercase strings e.g. 'healthy', 'starting', 'unhealthy'.
    """
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}

    if result.returncode != 0 or not result.stdout.strip():
        return {}

    services: dict[str, str] = {}
    for line in result.stdout.strip().splitlines():
        try:
            obj = json.loads(line)
            name = obj.get("Service") or obj.get("Name", "")
            health = (obj.get("Health") or obj.get("Status", "")).lower()
            if name:
                services[name] = health
        except json.JSONDecodeError:
            continue
    return services


# ---------------------------------------------------------------------------
# Stack availability skip fixtures
# Tests that use these fixtures are skipped (not failed) when the stack is down.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def require_infra_stack(docker_compose_services: dict[str, str]) -> None:
    """Skip the test if postgres and redis are not running via docker compose.

    Checks the project docker compose stack specifically — not system-level services.
    Start the infra stack: make local-up -- --infra-only
    """
    for svc in ("postgres", "redis"):
        if svc not in docker_compose_services:
            pytest.skip(
                f"Docker Compose service '{svc}' is not running. "
                "Start infra stack: make local-up -- --infra-only"
            )
        if "healthy" not in docker_compose_services[svc]:
            pytest.skip(
                f"Docker Compose service '{svc}' is not healthy. "
                f"Status: '{docker_compose_services[svc]}'. "
                "Run: make local-up -- --infra-only"
            )


@pytest.fixture(scope="session")
def require_full_stack(
    docker_compose_services: dict[str, str],
    contextforge_image_resolved: bool,
) -> None:
    """Skip the test if the full stack (contextforge + postgres + redis) is not running.

    Requires Q1 (CF_IMAGE_URI) to be resolved and the full stack started: make local-up
    """
    if not contextforge_image_resolved:
        pytest.skip(
            "CF_IMAGE_URI not resolved (Q1 is open). "
            "Resolve Q1 in .env then run: make local-up"
        )
    for svc in ("postgres", "redis", "contextforge"):
        if svc not in docker_compose_services:
            pytest.skip(
                f"Docker Compose service '{svc}' is not running. "
                "Start full stack: make local-up"
            )
        if "healthy" not in docker_compose_services[svc]:
            pytest.skip(
                f"Docker Compose service '{svc}' is not healthy. "
                f"Status: '{docker_compose_services[svc]}'. "
                "Run: make local-up"
            )
