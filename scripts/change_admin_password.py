#!/usr/bin/env python3
"""Change the ContextForge admin password via Bearer token auth.

Uses the REST API directly — not the UI form — so CSRF protection does not apply.
Safe to run through any reverse proxy (Cloud Shell Web Preview, port-forward, etc.).

Usage:
    python scripts/change_admin_password.py
    python scripts/change_admin_password.py --new-password MyNewPass123!
    python scripts/change_admin_password.py --gateway-url http://localhost:8080 --help
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_GATEWAY_URL = "http://localhost:8080"
_LOGIN_ENDPOINT = "/auth/login"
_CHANGE_PASSWORD_ENDPOINT = "/auth/email/change-password"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--gateway-url",
        default=os.environ.get("TEST_GATEWAY_BASE_URL", _DEFAULT_GATEWAY_URL),
        help=f"ContextForge base URL (default: {_DEFAULT_GATEWAY_URL})",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("CF_ADMIN_EMAIL", "admin@example.com"),
        help="Admin account email (default: admin@example.com)",
    )
    parser.add_argument(
        "--current-password",
        default=os.environ.get("CF_ADMIN_PASSWORD", "changeme"),
        help="Current admin password (default: changeme)",
    )
    parser.add_argument(
        "--new-password",
        default=os.environ.get("CF_ADMIN_NEW_PASSWORD", ""),
        help="New admin password (prompted if not provided)",
    )
    args = parser.parse_args()

    new_password = args.new_password
    if not new_password:
        import getpass
        print("Enter new password (min 8 chars, must include upper, lower, digit):")
        new_password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm new password: ")
        if new_password != confirm:
            print("ERROR: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    import httpx

    base = args.gateway_url.rstrip("/")

    print(f"Connecting to {base} ...")

    # Step 1: login
    try:
        resp = httpx.post(
            base + _LOGIN_ENDPOINT,
            json={"email": args.email, "password": args.current_password},
            timeout=10.0,
        )
    except httpx.ConnectError as exc:
        print(f"ERROR: Cannot connect to {base}: {exc}", file=sys.stderr)
        print("Ensure port-forward is active: kubectl port-forward svc/contextforge-svc 8080:80 -n mcp-farm", file=sys.stderr)
        sys.exit(1)

    if resp.status_code != 200:
        print(f"ERROR: Login failed (HTTP {resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)

    token = resp.json().get("access_token") or resp.json().get("token")
    if not token:
        print(f"ERROR: No token in login response: {resp.text}", file=sys.stderr)
        sys.exit(1)

    print(f"Logged in as {args.email}")

    # Step 2: change password
    try:
        resp = httpx.post(
            base + _CHANGE_PASSWORD_ENDPOINT,
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": args.current_password, "new_password": new_password},
            timeout=10.0,
        )
    except httpx.ConnectError as exc:
        print(f"ERROR: Cannot connect to {base}: {exc}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code in (200, 201, 204):
        print("Password changed successfully.")
        print(f"Log in at the Admin UI with: {args.email} / <your new password>")
    elif resp.status_code == 422:
        print(f"ERROR: Password rejected — check requirements: {resp.text}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"ERROR: HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
