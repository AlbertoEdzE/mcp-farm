# Gemini Investigation Prompt — ContextForge Pod Rollout & Admin UI Access

## Context: Who You Are and What You Have Access To

You are Gemini, running in Google Cloud Shell with full `kubectl` access to the
`mcp-farm` namespace on the GKE cluster for GCP project `x-ai-engineering`. You
can also run Python 3 and `curl` directly in the shell.

This file was written by Claude Code (the local AI assistant) and pushed to the
`mcp-farm` repository so you can read it here in Cloud Shell. Claude cannot reach
the cluster directly, so you are the investigative arm for this session.

---

## Project Summary

**What this is:** IBM ContextForge (`ghcr.io/ibm/mcp-context-forge:latest`) deployed
on GKE as the enterprise MCP gateway for the Baptist Health AI platform. It is a
single FastAPI app running on port 4444 inside the container.

**Namespace:** `mcp-farm`
**Deployment name:** `contextforge`
**Service name:** `contextforge-svc` (ClusterIP, port 80 → targetPort 4444)

**Kubernetes manifests live at:** `k8s/` in the repo root.
**Key config:** `k8s/configmap.yaml` — all ContextForge env vars are here.

---

## What Happened (Chronological)

1. `make gke-deploy` was run after updating `k8s/configmap.yaml` with:
   - `MCPGATEWAY_UI_ENABLED: "true"` — enables the Admin UI (defaults False)
   - `MCPGATEWAY_ADMIN_API_ENABLED: "true"` — enables Admin REST API (defaults False)
   - `SECURE_COOKIES: "false"` — required so cookies pass through the Cloud Shell HTTP proxy
   - `ALLOWED_ORIGINS: "https://8080-cs-726073937637-default.cs-us-east1-vpcf.cloudshell.dev"` — CSRF allowlist

2. Steps 1-7 of gke_deploy.sh completed successfully:
   - `configmap/contextforge-config configured` — new configmap applied
   - `deployment.apps/contextforge restarted` — rollout triggered

3. **Step [8/8] FAILED with timeout:**
   ```
   error: timed out waiting for the condition
   make: *** [Makefile:34: gke-deploy] Error 1
   ```
   The rollout did not complete within 300 seconds.

**Goal:** Get the ContextForge Admin UI working and accessible in a browser via
Cloud Shell Web Preview on port 8080 at path `/admin`.

---

## What You Must Investigate

### Step 1 — Pod health check

Run these commands and note the output carefully:

```bash
# Overall pod status
kubectl get pods -n mcp-farm

# Detailed status of the contextforge pod (events section is critical)
kubectl describe pod -n mcp-farm -l app=contextforge

# Last 80 lines of container logs (the key diagnostic)
kubectl logs -n mcp-farm -l app=contextforge --tail=80

# Previous container logs if pod restarted (CrashLoopBackOff)
kubectl logs -n mcp-farm -l app=contextforge --tail=80 --previous 2>/dev/null || echo "no previous container"

# Cluster events sorted by time
kubectl get events -n mcp-farm --sort-by='.lastTimestamp' | tail -20
```

**What to look for:**
- `Status: Running` with `Ready: True` → pod is healthy, proceed to Step 3
- `CrashLoopBackOff` → application crash, logs will show the error
- `OOMKilled` → memory limit (1Gi) too low
- `ImagePullBackOff` → image can't be pulled (check ghcr.io credentials)
- `Pending` → node scheduling issue (run `kubectl get nodes`)
- Readiness probe failure → `/health` endpoint not responding on port 4444

### Step 2 — Verify configmap is correct

```bash
kubectl get configmap contextforge-config -n mcp-farm -o yaml
```

Confirm ALL of these keys are present with correct values:
- `MCPGATEWAY_UI_ENABLED: "true"`
- `MCPGATEWAY_ADMIN_API_ENABLED: "true"`
- `SECURE_COOKIES: "false"`
- `ALLOWED_ORIGINS: "https://8080-cs-726073937637-default.cs-us-east1-vpcf.cloudshell.dev"`
- `HOST: "0.0.0.0"`
- `PORT: "4444"`

If any are missing or wrong, the configmap in the repo is authoritative — re-apply:
```bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/contextforge -n mcp-farm
kubectl rollout status deployment/contextforge -n mcp-farm --timeout=300s
```

### Step 3 — If pod is Running, test the API directly

Open a port-forward in the background and test health and auth:

```bash
# Port-forward (run in background, kill after testing)
kubectl port-forward svc/contextforge-svc 8080:80 -n mcp-farm &
PF_PID=$!
sleep 5

# Health check
curl -s http://localhost:8080/health | python3 -m json.tool

# Login with default credentials (or current password if changed)
curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"BaptistHealth2026Alberto!"}' \
  | python3 -m json.tool

kill $PF_PID
```

**What to look for:**
- Health returns `{"status": "healthy"}` or similar → app is up
- Login returns `{"access_token": "..."}` → auth works
- Login returns 401 → password may still be default `changeme` (try that instead)
- Login returns 422 → request format issue

### Step 4 — Clear the `password_change_required` flag (CRITICAL)

When the admin logs in with the default password `changeme`, ContextForge sets a
`password_change_required` flag in the database. Even after changing the password
via API, this flag may remain set, causing an infinite redirect loop to the
change-password form after login.

**Check and clear it:**

```bash
kubectl port-forward svc/contextforge-svc 8080:80 -n mcp-farm &
PF_PID=$!
sleep 5

# Login to get a token (try BaptistHealth2026Alberto! first, then changeme)
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"BaptistHealth2026Alberto!"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

echo "Token: ${TOKEN:0:40}..."

# Check current user state
curl -s http://localhost:8080/auth/email/admin/users/admin%40example.com \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool

# Clear password_change_required flag
curl -s -X PUT http://localhost:8080/auth/email/admin/users/admin%40example.com \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password_change_required": false}' \
  | python3 -m json.tool

kill $PF_PID
```

**What to look for:**
- GET user returns `"password_change_required": true` → flag is set, needs clearing
- PUT returns 200/204 with updated user → flag cleared, login should work
- PUT returns 404 → endpoint path is wrong, check ContextForge API docs at `/docs`

### Step 5 — Discover correct API endpoint if Step 4 fails

If the user endpoint path is wrong, check the OpenAPI spec:

```bash
kubectl port-forward svc/contextforge-svc 8080:80 -n mcp-farm &
PF_PID=$!
sleep 3

# Dump all available routes
curl -s http://localhost:8080/openapi.json | python3 -c "
import sys, json
spec = json.load(sys.stdin)
for path in sorted(spec['paths'].keys()):
    methods = list(spec['paths'][path].keys())
    print(f'{path}  [{', '.join(m.upper() for m in methods)}]')
" | grep -i "user\|password\|admin"

kill $PF_PID
```

Record the exact endpoint path for user management and password_change_required.

### Step 6 — Verify Cloud Shell Web Preview access

Once the pod is Running and login works via curl, verify browser access:

1. Start port-forward: `kubectl port-forward svc/contextforge-svc 8080:80 -n mcp-farm &`
2. In Cloud Shell, click "Web Preview" → "Preview on port 8080"
3. Append `/admin` to the URL in the browser
4. Try logging in with `admin@example.com` / `BaptistHealth2026Alberto!`

**What to look for:**
- Login form submits and shows Admin UI dashboard → SUCCESS
- "CSRF origin validation failed" error → the ALLOWED_ORIGINS fix didn't take effect (re-check configmap)
- Redirect loop to change-password form → password_change_required still set (retry Step 4)
- "Insecure connection" cookie warning → try SECURE_COOKIES=false in configmap

---

## What to Report Back to Claude

Write a summary covering:

1. **Pod status** — Running/CrashLoopBackOff/Pending, restart count, reason
2. **Root cause of rollout timeout** — what specific error or condition caused it
3. **Application logs excerpt** — any ERROR or CRITICAL lines
4. **Configmap state** — correct or missing/wrong values
5. **Health endpoint response** — exact JSON
6. **Login response** — success or error, exact HTTP status
7. **password_change_required flag** — current value, result of clearing it
8. **Browser access** — did login succeed in the Web Preview? Any error?
9. **Correct API endpoint for user management** — if Step 4 endpoint was wrong

Paste the summary back to Alberto in Cloud Shell, or write it to
`doc/transcripts/gemini_pod_report.md` so Claude can read it next session.

---

## Important Background

- **No external Load Balancer is possible** — GCP org policy blocks all external LB types
  on `x-ai-engineering`. Cloud Shell Web Preview + port-forward is the only access method.
- **ContextForge source** lives in a separate local repo `k-mcp-farm`. Claude has already
  confirmed the CSRF logic: `ALLOWED_ORIGINS` env var is parsed as a comma-separated list
  and compared against the request Origin header. Setting it to the Cloud Shell URL should
  fix the "CSRF origin validation failed" error.
- **imagePullPolicy: IfNotPresent** — if the node already has the image cached, it won't
  re-pull. This is intentional to avoid ghcr.io rate limits.
- **The password `BaptistHealth2026Alberto!`** was successfully set via the API in the
  previous session using `scripts/change_admin_password.py`. If it fails, fall back to
  `changeme` (the default).
