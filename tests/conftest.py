from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from faker import Faker

_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_SEED = 42

# Load .env if present. Does not override variables already set in the environment.
load_dotenv(_REPO_ROOT / ".env")


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
    return os.environ.get("TEST_GATEWAY_BASE_URL", "http://localhost:8080")


@pytest.fixture(scope="session")
def registry_base_url() -> str:
    """Base URL of the ContextForge Config Registry, read from TEST_REGISTRY_BASE_URL."""
    return os.environ.get("TEST_REGISTRY_BASE_URL", "http://localhost:8081")


@pytest.fixture(scope="session")
def test_target() -> str:
    """Deployment target for integration tests. Values: 'local' or 'gke'."""
    return os.environ.get("TEST_TARGET", "local")
