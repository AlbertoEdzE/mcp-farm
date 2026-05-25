#!/usr/bin/env python3
"""Generate the MCP Farm validation report.

Runs the full pytest suite, parses results, and writes
reports/validation_report.md — the Baptist Health deliverable.

Usage:
    python scripts/generate_report.py [--cluster c0,c1,...] [--target local|gke]

Make target:
    make report
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_REPORTS_DIR = _REPO_ROOT / "reports"
_JUNIT_XML = _REPORTS_DIR / "junit_results.xml"
_REPORT_MD = _REPORTS_DIR / "validation_report.md"

CLUSTER_LABELS: dict[str, str] = {
    "c0": "C0 — Repository Foundation",
    "c1": "C1 — Local Environment",
    "c2": "C2 — ContextForge Baseline",
    "c3": "C3 — GKE Infrastructure",
    "c4": "C4 — MCP Proxy (GitLab)",
    "c5": "C5 — Virtual Server",
    "c6": "C6 — Documentation",
}

# (criterion_number, description, evidence_source)
# evidence_source: cluster key or "operational" (requires live GKE)
ACCEPTANCE_CRITERIA: list[tuple[int, str, str]] = [
    (1,  "GKE cluster reachable via kubectl",                          "operational"),
    (2,  "All ContextForge pods in Running state",                     "operational"),
    (3,  "AI Gateway health endpoint returns HTTP 200",                 "c2"),
    (4,  "Config Registry health endpoint returns HTTP 200",           "c2"),
    (5,  "GET /v1/tools returns non-empty array with GitLab tools",    "operational"),
    (6,  "make test exits 0 from clean checkout",                      "overall"),
    (7,  "make gke-deploy is idempotent on second run",                "c3"),
    (8,  "Runbook contains all steps and expected outputs",            "c6"),
    (9,  "All open questions (Q1-Q6) resolved",                        "manual"),
    (10, "No credential or secret in any committed file",              "c0"),
]

OPEN_QUESTIONS: list[tuple[str, str]] = [
    ("Q1", "Resolved — ghcr.io/ibm/mcp-context-forge:latest (Apache 2.0, public image)"),
    ("Q2", "Resolved — x-ai-engineering (project number 1030710021223)"),
    ("Q3", "Assumed — gateway.expose_container_port: true (see ADR-001)"),
    ("Q4", "Pending — GITLAB_OAUTH_CLIENT_ID / GITLAB_OAUTH_CLIENT_SECRET (Bala)"),
    ("Q5", "Pending — Secret Manager vs Kubernetes Secrets decision (Chakri)"),
    ("Q6", "Pending — GKE_NODE_MACHINE_TYPE / GKE_NODE_COUNT (Lakshman)"),
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cluster",
        default="all",
        help="Comma-separated cluster list, e.g. c0,c1,c2 (default: all)",
    )
    parser.add_argument(
        "--target",
        default=os.environ.get("TEST_TARGET", "local"),
        choices=["local", "gke"],
        help="Deployment target (default: local)",
    )
    return parser.parse_args()


def _run_pytest(cluster: str) -> int:
    _REPORTS_DIR.mkdir(exist_ok=True)
    cmd = [
        sys.executable, "-m", "pytest",
        f"--junit-xml={_JUNIT_XML}",
        "--tb=short",
        "-v",
    ]
    if cluster != "all":
        clusters = [c.strip().lower() for c in cluster.split(",")]
        for c in clusters:
            cmd.append(f"tests/test_{c}_*.py")
    else:
        cmd.append("tests/")
    print(f"\n{'='*60}")
    print("MCP Farm — running test suite")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=_REPO_ROOT)
    return result.returncode


def _parse_junit() -> dict[str, list[dict]]:
    """Return {cluster_key: [{name, status, classname}]} from junit XML."""
    if not _JUNIT_XML.is_file():
        return {}
    tree = ET.parse(_JUNIT_XML)
    root = tree.getroot()
    # Handle both <testsuites><testsuite> and bare <testsuite>
    suites = root.findall(".//testsuite")
    if not suites:
        suites = [root]

    clusters: dict[str, list[dict]] = {k: [] for k in CLUSTER_LABELS}

    for suite in suites:
        for tc in suite.findall("testcase"):
            classname = tc.get("classname", "")
            name = tc.get("name", "")
            if tc.find("skipped") is not None:
                status = "SKIP"
            elif tc.find("failure") is not None or tc.find("error") is not None:
                status = "FAIL"
            else:
                status = "PASS"
            # Map to cluster by file name encoded in classname
            cluster_key = next(
                (k for k in CLUSTER_LABELS if f"test_{k}_" in classname.replace(".", "/")),
                None,
            )
            if cluster_key:
                clusters[cluster_key].append({"name": name, "classname": classname, "status": status})

    return {k: v for k, v in clusters.items() if v}


def _criterion_result(
    criterion_num: int,
    evidence_source: str,
    clusters: dict[str, list[dict]],
    pytest_exit_code: int,
    target: str,
) -> str:
    if evidence_source == "operational":
        return f"See Runbook — requires live {target.upper()} deployment"
    if evidence_source == "manual":
        return "See Open Questions table below"
    if evidence_source == "overall":
        return "PASS" if pytest_exit_code == 0 else "FAIL"
    tests = clusters.get(evidence_source, [])
    if not tests:
        return "NOT RUN"
    statuses = {t["status"] for t in tests}
    if "FAIL" in statuses:
        failed = [t["name"] for t in tests if t["status"] == "FAIL"]
        return f"FAIL — {len(failed)} test(s) failing"
    if all(s == "SKIP" for s in statuses):
        return "SKIP — requires running stack"
    passed = sum(1 for t in tests if t["status"] == "PASS")
    skipped = sum(1 for t in tests if t["status"] == "SKIP")
    if skipped:
        return f"PASS ({passed} structural) / SKIP ({skipped} integration — stack not running)"
    return f"PASS ({passed} tests)"


def _write_report(
    clusters: dict[str, list[dict]],
    pytest_exit_code: int,
    target: str,
    generated_at: str,
) -> None:
    total = sum(len(v) for v in clusters.values())
    passed = sum(t["status"] == "PASS" for v in clusters.values() for t in v)
    skipped = sum(t["status"] == "SKIP" for v in clusters.values() for t in v)
    failed = sum(t["status"] == "FAIL" for v in clusters.values() for t in v)

    lines: list[str] = [
        "# MCP Farm — Validation Report",
        "",
        f"**Project:** MCP Farm — Baptist Health AI Gateway  ",
        f"**Generated:** {generated_at}  ",
        f"**Target:** {target.upper()}  ",
        f"**GCP Project:** x-ai-engineering  ",
        f"**Image:** ghcr.io/ibm/mcp-context-forge:latest  ",
        "",
        "---",
        "",
        "## Test Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total  | {total} |",
        f"| Passed | {passed} |",
        f"| Skipped (stack not running) | {skipped} |",
        f"| Failed | {failed} |",
        f"| Suite exit code | {pytest_exit_code} |",
        "",
        "---",
        "",
        "## Results by Cluster",
        "",
    ]

    for key, label in CLUSTER_LABELS.items():
        tests = clusters.get(key, [])
        if not tests:
            continue
        n_pass = sum(1 for t in tests if t["status"] == "PASS")
        n_skip = sum(1 for t in tests if t["status"] == "SKIP")
        n_fail = sum(1 for t in tests if t["status"] == "FAIL")
        summary_parts = []
        if n_pass:
            summary_parts.append(f"{n_pass} passed")
        if n_skip:
            summary_parts.append(f"{n_skip} skipped")
        if n_fail:
            summary_parts.append(f"{n_fail} FAILED")
        lines.append(f"### {label}")
        lines.append("")
        lines.append(f"| Status | Count |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Passed  | {n_pass} |")
        lines.append(f"| Skipped | {n_skip} |")
        lines.append(f"| Failed  | {n_fail} |")
        lines.append("")
        if n_fail:
            lines.append("**Failing tests:**")
            lines.append("")
            for t in tests:
                if t["status"] == "FAIL":
                    lines.append(f"- `{t['name']}`")
            lines.append("")

    lines += [
        "---",
        "",
        "## Acceptance Criteria",
        "",
        "From `doc/Specify.md` Section 16.",
        "",
        "| # | Criterion | Result |",
        "|---|-----------|--------|",
    ]

    for num, description, source in ACCEPTANCE_CRITERIA:
        result = _criterion_result(num, source, clusters, pytest_exit_code, target)
        lines.append(f"| {num} | {description} | {result} |")

    lines += [
        "",
        "---",
        "",
        "## Open Questions",
        "",
        "| ID | Status |",
        "|----|--------|",
    ]
    for qid, status in OPEN_QUESTIONS:
        lines.append(f"| {qid} | {status} |")

    lines += [
        "",
        "---",
        "",
        "## Notes",
        "",
        "- Integration tests marked SKIP require the ContextForge stack to be running.",
        "  Run `make local-up` (local) or complete the GKE deployment path before re-running.",
        "- Acceptance criteria marked 'See Runbook' require live deployment verification.",
        "  Follow `doc/Runbook.md` Part 2 for the complete GKE deployment and verification path.",
        "- This report was generated by `scripts/generate_report.py`.",
        "  Reproduce with: `make report`",
        "",
    ]

    _REPORT_MD.write_text("\n".join(lines))
    print(f"\nReport written: {_REPORT_MD.relative_to(_REPO_ROOT)}")


def main() -> int:
    args = _parse_args()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    exit_code = _run_pytest(args.cluster)
    clusters = _parse_junit()
    _write_report(clusters, exit_code, args.target, generated_at)

    total = sum(len(v) for v in clusters.values())
    passed = sum(t["status"] == "PASS" for v in clusters.values() for t in v)
    skipped = sum(t["status"] == "SKIP" for v in clusters.values() for t in v)
    failed = sum(t["status"] == "FAIL" for v in clusters.values() for t in v)

    print(f"\nSummary: {total} total — {passed} passed, {skipped} skipped, {failed} failed")
    print(f"Deliverable: reports/validation_report.md\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
