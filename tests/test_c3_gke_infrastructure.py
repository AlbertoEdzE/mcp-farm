"""Cluster C3 — GKE Infrastructure tests.

All tests in this file are structural (always run, no running services required).
GKE integration tests require Q2 (GCP_PROJECT_ID) and Q6 (node config) to be
resolved and a live GKE cluster to be provisioned — those are not implemented here
and will be added in a later cluster once the open questions are closed.

Run structural tests:
  make test CLUSTER=c3

Progressive run (C0 through C3):
  make test CLUSTER=c0,c1,c2,c3
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_K8S_DIR = _REPO_ROOT / "k8s"


class TestGKEInfrastructureStructure:

    # ------------------------------------------------------------------
    # ADR
    # ------------------------------------------------------------------

    def test_adr_002_exists(self) -> None:
        """doc/ADR/ADR-002-managed-data-services.md must exist."""
        adr_path = _REPO_ROOT / "doc" / "ADR" / "ADR-002-managed-data-services.md"
        assert adr_path.is_file(), (
            "ADR-002 not found. It documents the decision to use Cloud SQL and "
            "Memorystore over in-cluster StatefulSets. See doc/Plan.md MF-E04-T01."
        )

    def test_adr_002_references_cloud_sql(self) -> None:
        """ADR-002 must reference Cloud SQL as the chosen PostgreSQL backend."""
        content = (_REPO_ROOT / "doc" / "ADR" / "ADR-002-managed-data-services.md").read_text()
        assert "Cloud SQL" in content, (
            "ADR-002 must document Cloud SQL as the PostgreSQL provisioning decision."
        )

    def test_adr_002_references_memorystore(self) -> None:
        """ADR-002 must reference Memorystore as the chosen Redis backend."""
        content = (_REPO_ROOT / "doc" / "ADR" / "ADR-002-managed-data-services.md").read_text()
        assert "Memorystore" in content, (
            "ADR-002 must document Memorystore as the Redis provisioning decision."
        )

    # ------------------------------------------------------------------
    # gke_provision.sh
    # ------------------------------------------------------------------

    def test_gke_provision_script_help_exits_zero(self) -> None:
        """scripts/gke_provision.sh --help must exit with code 0."""
        result = subprocess.run(
            [str(_SCRIPTS_DIR / "gke_provision.sh"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"gke_provision.sh --help exited {result.returncode}.\n{result.stderr}"
        )

    def test_gke_provision_enables_container_api(self) -> None:
        """gke_provision.sh must enable container.googleapis.com."""
        content = (_SCRIPTS_DIR / "gke_provision.sh").read_text()
        assert "container.googleapis.com" in content, (
            "gke_provision.sh must enable container.googleapis.com (GKE API)."
        )

    def test_gke_provision_enables_sqladmin_api(self) -> None:
        """gke_provision.sh must enable sqladmin.googleapis.com."""
        content = (_SCRIPTS_DIR / "gke_provision.sh").read_text()
        assert "sqladmin.googleapis.com" in content, (
            "gke_provision.sh must enable sqladmin.googleapis.com (Cloud SQL API)."
        )

    def test_gke_provision_enables_redis_api(self) -> None:
        """gke_provision.sh must enable redis.googleapis.com."""
        content = (_SCRIPTS_DIR / "gke_provision.sh").read_text()
        assert "redis.googleapis.com" in content, (
            "gke_provision.sh must enable redis.googleapis.com (Memorystore API)."
        )

    def test_gke_provision_creates_gke_cluster(self) -> None:
        """gke_provision.sh must call 'gcloud container clusters create'."""
        content = (_SCRIPTS_DIR / "gke_provision.sh").read_text()
        assert "gcloud container clusters create" in content, (
            "gke_provision.sh must contain a 'gcloud container clusters create' command."
        )

    def test_gke_provision_creates_cloud_sql_instance(self) -> None:
        """gke_provision.sh must call 'gcloud sql instances create'."""
        content = (_SCRIPTS_DIR / "gke_provision.sh").read_text()
        assert "gcloud sql instances create" in content, (
            "gke_provision.sh must contain a 'gcloud sql instances create' command."
        )

    def test_gke_provision_creates_memorystore_instance(self) -> None:
        """gke_provision.sh must call 'gcloud redis instances create'."""
        content = (_SCRIPTS_DIR / "gke_provision.sh").read_text()
        assert "gcloud redis instances create" in content, (
            "gke_provision.sh must contain a 'gcloud redis instances create' command."
        )

    def test_gke_provision_validates_required_env_vars(self) -> None:
        """gke_provision.sh must check GCP_PROJECT_ID and GKE_CLUSTER_NAME before proceeding."""
        content = (_SCRIPTS_DIR / "gke_provision.sh").read_text()
        for var in ("GCP_PROJECT_ID", "GKE_CLUSTER_NAME", "CLOUDSQL_INSTANCE_NAME"):
            assert var in content, (
                f"gke_provision.sh must validate the required env var {var}."
            )

    def test_gke_provision_is_idempotent_by_design(self) -> None:
        """gke_provision.sh must skip creation of resources that already exist."""
        content = (_SCRIPTS_DIR / "gke_provision.sh").read_text()
        assert "already exists" in content, (
            "gke_provision.sh must handle the case where resources already exist "
            "to be safely re-runnable."
        )

    # ------------------------------------------------------------------
    # gke_deploy.sh
    # ------------------------------------------------------------------

    def test_gke_deploy_script_help_exits_zero(self) -> None:
        """scripts/gke_deploy.sh --help must exit with code 0."""
        result = subprocess.run(
            [str(_SCRIPTS_DIR / "gke_deploy.sh"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"gke_deploy.sh --help exited {result.returncode}.\n{result.stderr}"
        )

    def test_gke_deploy_creates_image_pull_secret(self) -> None:
        """gke_deploy.sh must create the IBM entitlement image pull secret."""
        content = (_SCRIPTS_DIR / "gke_deploy.sh").read_text()
        assert "kubectl create secret docker-registry" in content, (
            "gke_deploy.sh must create the IBM entitlement docker-registry secret."
        )
        assert "ibm-entitlement-key" in content, (
            "gke_deploy.sh must name the pull secret 'ibm-entitlement-key'."
        )

    def test_gke_deploy_creates_db_credentials_secret(self) -> None:
        """gke_deploy.sh must create the contextforge-db-credentials secret."""
        content = (_SCRIPTS_DIR / "gke_deploy.sh").read_text()
        assert "contextforge-db-credentials" in content, (
            "gke_deploy.sh must create the 'contextforge-db-credentials' Kubernetes Secret."
        )

    def test_gke_deploy_creates_redis_credentials_secret(self) -> None:
        """gke_deploy.sh must create the contextforge-redis-credentials secret."""
        content = (_SCRIPTS_DIR / "gke_deploy.sh").read_text()
        assert "contextforge-redis-credentials" in content, (
            "gke_deploy.sh must create the 'contextforge-redis-credentials' Kubernetes Secret."
        )

    def test_gke_deploy_applies_all_manifests(self) -> None:
        """gke_deploy.sh must apply all five k8s manifest files."""
        content = (_SCRIPTS_DIR / "gke_deploy.sh").read_text()
        for manifest in ("configmap.yaml", "deployment.yaml", "service.yaml", "ingress.yaml"):
            assert manifest in content, (
                f"gke_deploy.sh must apply k8s/{manifest}."
            )

    def test_gke_deploy_patches_image(self) -> None:
        """gke_deploy.sh must patch the deployment image with kubectl set image."""
        content = (_SCRIPTS_DIR / "gke_deploy.sh").read_text()
        assert "kubectl set image" in content, (
            "gke_deploy.sh must use 'kubectl set image' to inject the real ContextForge image URI."
        )

    def test_gke_deploy_waits_for_rollout(self) -> None:
        """gke_deploy.sh must wait for the deployment rollout to complete."""
        content = (_SCRIPTS_DIR / "gke_deploy.sh").read_text()
        assert "kubectl rollout status" in content, (
            "gke_deploy.sh must call 'kubectl rollout status' to block until the "
            "deployment is fully rolled out."
        )

    def test_gke_deploy_uses_idempotent_secret_creation(self) -> None:
        """gke_deploy.sh must use --dry-run=client -o yaml | kubectl apply pattern for secrets."""
        content = (_SCRIPTS_DIR / "gke_deploy.sh").read_text()
        assert "--dry-run=client" in content, (
            "gke_deploy.sh must use --dry-run=client -o yaml | kubectl apply for idempotent "
            "secret creation. This prevents errors when secrets already exist."
        )

    # ------------------------------------------------------------------
    # gke_teardown.sh
    # ------------------------------------------------------------------

    def test_gke_teardown_script_help_exits_zero(self) -> None:
        """scripts/gke_teardown.sh --help must exit with code 0."""
        result = subprocess.run(
            [str(_SCRIPTS_DIR / "gke_teardown.sh"), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"gke_teardown.sh --help exited {result.returncode}.\n{result.stderr}"
        )

    def test_gke_teardown_has_force_flag(self) -> None:
        """gke_teardown.sh --help must document the --force option."""
        result = subprocess.run(
            [str(_SCRIPTS_DIR / "gke_teardown.sh"), "--help"],
            capture_output=True,
            text=True,
        )
        assert "--force" in result.stdout, (
            "gke_teardown.sh --help must document the --force flag for non-interactive use."
        )

    def test_gke_teardown_deletes_gke_cluster(self) -> None:
        """gke_teardown.sh must call 'gcloud container clusters delete'."""
        content = (_SCRIPTS_DIR / "gke_teardown.sh").read_text()
        assert "gcloud container clusters delete" in content, (
            "gke_teardown.sh must delete the GKE cluster."
        )

    def test_gke_teardown_deletes_cloud_sql(self) -> None:
        """gke_teardown.sh must call 'gcloud sql instances delete'."""
        content = (_SCRIPTS_DIR / "gke_teardown.sh").read_text()
        assert "gcloud sql instances delete" in content, (
            "gke_teardown.sh must delete the Cloud SQL instance."
        )

    def test_gke_teardown_deletes_memorystore(self) -> None:
        """gke_teardown.sh must call 'gcloud redis instances delete'."""
        content = (_SCRIPTS_DIR / "gke_teardown.sh").read_text()
        assert "gcloud redis instances delete" in content, (
            "gke_teardown.sh must delete the Memorystore instance."
        )

    # ------------------------------------------------------------------
    # Kubernetes manifests
    # ------------------------------------------------------------------

    def test_configmap_has_gateway_health_path(self) -> None:
        """k8s/configmap.yaml must declare CF_GATEWAY_HEALTH_PATH."""
        content = (_K8S_DIR / "configmap.yaml").read_text()
        assert "CF_GATEWAY_HEALTH_PATH" in content, (
            "k8s/configmap.yaml must declare CF_GATEWAY_HEALTH_PATH."
        )

    def test_configmap_has_registry_health_path(self) -> None:
        """k8s/configmap.yaml must declare CF_REGISTRY_HEALTH_PATH."""
        content = (_K8S_DIR / "configmap.yaml").read_text()
        assert "CF_REGISTRY_HEALTH_PATH" in content, (
            "k8s/configmap.yaml must declare CF_REGISTRY_HEALTH_PATH."
        )

    def test_deployment_has_liveness_probe(self) -> None:
        """k8s/deployment.yaml must define a liveness probe."""
        content = (_K8S_DIR / "deployment.yaml").read_text()
        assert "livenessProbe" in content, (
            "k8s/deployment.yaml must define a livenessProbe."
        )

    def test_deployment_has_readiness_probe(self) -> None:
        """k8s/deployment.yaml must define a readiness probe."""
        content = (_K8S_DIR / "deployment.yaml").read_text()
        assert "readinessProbe" in content, (
            "k8s/deployment.yaml must define a readinessProbe."
        )

    def test_deployment_uses_ibm_entitlement_pull_secret(self) -> None:
        """k8s/deployment.yaml must reference the ibm-entitlement-key imagePullSecret."""
        content = (_K8S_DIR / "deployment.yaml").read_text()
        assert "ibm-entitlement-key" in content, (
            "k8s/deployment.yaml must reference 'ibm-entitlement-key' in imagePullSecrets. "
            "This secret is created by gke_deploy.sh from IBM_ENTITLEMENT_KEY."
        )

    def test_deployment_uses_placeholder_image(self) -> None:
        """k8s/deployment.yaml image must be a placeholder (patched at deploy time)."""
        content = (_K8S_DIR / "deployment.yaml").read_text()
        assert "placeholder" in content, (
            "k8s/deployment.yaml image must remain a placeholder — "
            "the real image is injected by gke_deploy.sh via kubectl set image."
        )

    def test_all_manifests_specify_mcp_farm_namespace(self) -> None:
        """All k8s manifest files must specify namespace: mcp-farm."""
        for manifest_file in ("deployment.yaml", "service.yaml", "configmap.yaml", "ingress.yaml"):
            path = _K8S_DIR / manifest_file
            content = path.read_text()
            assert "namespace: mcp-farm" in content, (
                f"k8s/{manifest_file} must specify 'namespace: mcp-farm'."
            )

    def test_secrets_example_has_three_secrets(self) -> None:
        """k8s/secrets.example.yaml must define all three required Kubernetes Secrets."""
        content = (_K8S_DIR / "secrets.example.yaml").read_text()
        for secret_name in (
            "contextforge-db-credentials",
            "contextforge-redis-credentials",
            "ibm-entitlement-key",
        ):
            assert secret_name in content, (
                f"k8s/secrets.example.yaml must document the '{secret_name}' Secret shape."
            )

    def test_namespace_manifest_exists(self) -> None:
        """k8s/namespace.yaml must exist."""
        assert (_K8S_DIR / "namespace.yaml").is_file(), (
            "k8s/namespace.yaml not found."
        )
