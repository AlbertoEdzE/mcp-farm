# Demo Handbook — ContextForge Admin UI on GKE

Audience: Alberto (presenter) showing Chakri that the MCP gateway is running on GKE.
Goal: Open the ContextForge Admin UI in a browser, log in, and walk through the dashboard.

---

## Before You Start (5 minutes before the demo)

Confirm you have:
- A Google account with access to GCP project `x-ai-engineering`
- The mcp-farm repository cloned in Cloud Shell (`~/mcp-farm`)
- The Admin password: `BaptistHealth2026Alberto!`

---

## Step-by-Step: From Zero to Dashboard

### Step 1 — Open GCP Console

1. Open a new **InPrivate / Incognito** browser window.
2. Go to `console.cloud.google.com`
3. Sign in with your GCP account.
4. In the project selector (top bar), select **x-ai-engineering**.

---

### Step 2 — Open Cloud Shell

1. Click the **Cloud Shell** icon in the top-right toolbar of GCP Console
   (looks like `>_`).
2. Wait for the Cloud Shell terminal to load at the bottom of the page.
3. Navigate to the repo:
   ```bash
   cd ~/mcp-farm
   git pull origin main
   ```

---

### Step 3 — Run the Demo Startup Script

This single command checks the pod, clears any stale connection, and starts the
port-forward. Run it every time before the demo:

```bash
make demo-start
```

Expected output (last lines):
```
Health check passed (HTTP 200 on /health).

===========================================
 Admin UI is ready
===========================================

  1. Click 'Web Preview' in the Cloud Shell toolbar (top-right icon)
  2. Select 'Preview on port 8080'
  3. Append /admin to the URL in the browser address bar
  4. Log in with:
       Email   : admin@example.com
       Password: BaptistHealth2026Alberto!
```

If it prints an error, see the Troubleshooting section at the bottom.

---

### Step 4 — Open the Admin UI in the Browser

1. In Cloud Shell, click the **Web Preview** icon (top-right of the Cloud Shell panel).
2. Select **"Preview on port 8080"**.
3. A new tab opens with a URL like:
   `https://8080-cs-726073937637-default.cs-us-east1-vpcf.cloudshell.dev/`
4. Add `/admin` to the end of the URL and press Enter:
   `https://8080-cs-726073937637-default.cs-us-east1-vpcf.cloudshell.dev/admin`

---

### Step 5 — Log In

| Field    | Value                        |
|----------|------------------------------|
| Email    | `admin@example.com`          |
| Password | `BaptistHealth2026Alberto!`  |

Click **Sign In**. The Gateway Administration dashboard loads.

---

## What to Show Chakri

### Overview Dashboard

- **Uptime** (top right) — confirms the service has been running continuously on GKE.
- **MCP Runtime: Python MCP Core** — confirms ContextForge is running the correct runtime.
- **Active Entities** — number of registered gateways, proxies, and virtual servers.
- **Success Rate / Avg Latency** — live metrics.

### MCP Servers (left sidebar)

Shows the registered MCP backend servers. The demo MCP server (`mcp-demo-svc`) is
already registered and running at `mcp-demo-svc.mcp-farm.svc.cluster.local:9000`.

### Virtual Servers (left sidebar)

Shows the virtual server created by `make create-virtual-server`. Each virtual server
scopes tool access for a specific agent role (e.g., a read-only GitLab agent vs. a
full-access admin agent).

### MCP Registry (left sidebar)

Shows all registered proxies. After `make register-proxy` is run with Q4 credentials
(GITLAB_OAUTH_CLIENT_ID / GITLAB_OAUTH_CLIENT_SECRET confirmed with Bala), the GitLab
MCP proxy will appear here.

---

## Stopping the Demo

When done, stop the port-forward to free the port:

```bash
pkill -f "kubectl port-forward.*8080:80" || true
```

Or close the Cloud Shell session entirely.

---

## Troubleshooting

### "kubectl is not configured or cluster is unreachable"

The kubectl context was lost (Cloud Shell reconnected or session expired). Restore it:

```bash
source .env
gcloud container clusters get-credentials "${GKE_CLUSTER_NAME}" \
    --region "${GCP_REGION}" --project x-ai-engineering
```

Then re-run `make demo-start`.

### "Pod did not become Ready within 90s"

Check what's wrong with the pod:

```bash
kubectl get pods -n mcp-farm
kubectl describe pod -n mcp-farm -l app=contextforge | tail -30
kubectl logs -n mcp-farm -l app=contextforge --tail=40
```

Common causes:
- **ImagePullBackOff** — ghcr.io rate limit; wait a few minutes and retry.
- **CrashLoopBackOff** — check logs for application error.
- **OOMKilled** — pod exceeded 1Gi memory; node may need more capacity.

### "Invalid email or password" in the browser

The password is exactly: `BaptistHealth2026Alberto!`
Note the `2026` between `Health` and `Alberto` — easy to miss.

### "CSRF origin validation failed"

The Cloud Shell session ID changed (rare). The configmap `ALLOWED_ORIGINS` is set to
the session-specific URL. Check the current Web Preview URL and compare to the value in:

```bash
kubectl get configmap contextforge-config -n mcp-farm \
    -o jsonpath='{.data.ALLOWED_ORIGINS}'
```

If they differ, update `k8s/configmap.yaml` with the new Cloud Shell origin, commit,
push, and re-run `make gke-deploy`.

### Port 8080 already in use

```bash
pkill -f "kubectl port-forward.*8080" || true
sleep 2
make demo-start
```

---

## Architecture Summary (for Chakri Q&A)

```
Browser (InPrivate tab)
    |
    | HTTPS
    v
Cloud Shell Web Preview Proxy
    |
    | HTTP (proxied)
    v
kubectl port-forward (localhost:8080)
    |
    | TCP in-cluster
    v
contextforge-svc (ClusterIP, port 80)
    |
    | targetPort 4444
    v
contextforge Pod (GKE node)
    |-- PostgreSQL (Cloud SQL private IP)
    |-- Redis (Memorystore private IP)
    |-- mcp-demo-svc (in-cluster MCP backend)
```

External Load Balancer is not used because GCP org policy on `x-ai-engineering`
restricts all external LB types. Cloud Shell Web Preview is the interim access method
until an org-level policy exemption is granted.
