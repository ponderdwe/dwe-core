# Proposal: dwe-hub Improvements

## Problem

Three architectural issues in dwe-hub identified in a structural review:

1. **Fragile auto-migrations**: `database.py` runs `run_migrations()` at app startup, checking `information_schema` to detect and apply schema changes. This silently fails for column renames, type changes, index removal, and default changes. A bad migration takes down the app on boot.

2. **Org secrets via env vars in production**: `secret_service.py` falls back to `{ORG_SLUG_UPPER}_DEPLOY` environment variables for org credentials. Env vars don't scale (adding an org requires redeploying the app), pollute the process environment, and create secret sprawl.

3. **No dependency check at import time**: When an org imports a dashboard from dwe-hub, there is no check of whether the required adapters are deployed in the org's environment. Schools import dashboards and only discover missing infrastructure after the fact.

## Solution

**Fix 1 — Alembic migrations**
Replace `run_migrations()` with Alembic. Migration history as versioned files under `alembic/versions/`. `entrypoint.sh` runs `alembic upgrade head` before app start. Migrations are a deliberate, auditable operation — not a startup side effect.

**Fix 2 — Org secrets: production must use AWS Secrets Manager only**
Remove the env var fallback in production contexts (`DWE_HUB_DEBUG != true`). In production, always resolve org credentials from AWS Secrets Manager. The env var path is kept for local development only.

**Fix 3 — Dependency check at dashboard import (specced, deferred)**
When an org requests a dashboard import, dwe-hub queries the org's deployed KG (via `dwe_falkordb`'s Deploy API) to determine what adapters the dashboard requires vs. what is deployed. Surface the gap clearly before importing. Implementation is deferred until `dwe_falkordb` is consistently deployed across orgs.

## Goals

- Schema migrations are safe, auditable, and reversible
- Org secrets in production always come from AWS Secrets Manager
- The dependency check flow is specced and ready for implementation when KG adoption is sufficient

## Non-goals

- Does not change the dwe-hub public API
- Does not change how dwe-hub connects to dwe-core
- Does not implement the Superset plugin
