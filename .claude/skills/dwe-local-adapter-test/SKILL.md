---
name: dwe-local-adapter-test
description: "Locally hydrate a DWE adapter and run Pulumi without touching AWS SM or Key Vault. All secrets (CI + infrastructure) come from a single .env file the user fills in."
---

# DWE Local Adapter Test

Hydrates an adapter locally and runs Pulumi the same way CI does. All secrets live in a single `.env` the user fills in — no AWS Secrets Manager, no Azure Key Vault call needed at hydration time. Everything stays in `local_development/` (gitignored).

## What to do when invoked

### Step 1 — Collect non-sensitive params

Run these to discover available adapters and what copier will ask:

```bash
dwe list-adapters
dwe adapter-questions <adapter>
dwe show-secrets-template <adapter>
```

Ask the user only for the non-sensitive params:

| Param | Example | Notes |
|---|---|---|
| `adapter` | `dwe_trino`, `dwe_coder`, `dwe_superset` | |
| `adapter_path` | `../dwe_coder` | path to the adapter repo |
| `secret_name` | `DWE-DEPLOY-CODER` | name in Key Vault / SM referenced by Pulumi |
| `cloud_provider` | `azure` or `aws` | |
| `environment` | `prod` or `dev` | |
| `git_repo_url` | `https://github.com/org/coder-deploy` | repo the VM clones at boot; use `""` if not relevant |
| `pulumi_action` | `preview` (default) or `up` | |

**Do not ask for `project_name`** — derive it from the adapter's `hub_name` in `copier.yml`:
```bash
grep "hub_name" <adapter_path>/copier.yml
# hub_name: coder  →  project_name = coder-deploy
```
Convention: `{hub_name}-deploy`.

**Do not ask for copier defaults** (`aws_region`, `instance_type`, `volume_size`) unless the user mentions them — just pass `--defaults` and the user's overrides.

### Step 2 — Generate .env template

The `.env` needs **CI/infrastructure secrets only** — credentials that Pulumi itself needs to authenticate and run. Runtime adapter secrets (DB passwords, networking IDs, Coder URLs, etc.) are read by Pulumi from Key Vault / Secrets Manager at deploy time, not from `.env`.

Create the directory and write the template:

```bash
mkdir -p local_development/<adapter>
```

**Azure `.env` template** (use `dwe show-secrets-template <adapter>` for the full list; note it shows all clouds — keep only Azure keys):

```bash
# ── Azure / Pulumi CI secrets ─────────────────────────────────────────────────
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=
AZURE_SUBSCRIPTION_ID=
AZURE_STORAGE_ACCOUNT=
PULUMI_AZURE_STATE=azblob://deploy-state/<adapter>-state
KEY_VAULT_NAME=
RESOURCE_GROUP=

# ── Git deploy token (VM clones this repo at boot) ────────────────────────────
git_deploy_token=
git_deploy_username=x-token-auth
```

**AWS `.env` template:**

```bash
# ── AWS / Pulumi CI secrets ───────────────────────────────────────────────────
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
PULUMI_S3_STATE=s3://my-pulumi-state-bucket

# ── Git deploy token (VM clones this repo at boot) ────────────────────────────
git_deploy_token=
git_deploy_username=x-token-auth
```

> `dwe show-secrets-template` returns ALL keys for all clouds — when the user is on Azure, skip the AWS-specific keys (VPC_ID, ALB_SUBNET_IDS, ROUTE53_ZONE_ID, ACM_CERTIFICATE_ARN, etc.) and vice versa.

Tell the user: **"Fill in `local_development/<adapter>/.env` and confirm when done."** Wait before continuing.

### Step 3 — Hydrate with copier

Stamp out the adapter code. Note: in copier 9.x the flag is `--UNSAFE` (uppercase):

```bash
copier copy <adapter_path> local_development/<adapter> --defaults --overwrite --UNSAFE \
  --data project_name=<project_name>
```

Pass any non-default copier params the user specified as additional `--data` flags:

```bash
  --data instance_type=Standard_D4s_v3 \
  --data volume_size=150 \
  --data secret_id=<secret_name>
```

> Run `dwe adapter-questions <adapter>` first to know which keys are available.

### Step 4 — Write dwe-hydration.yaml

The hydration yaml tells the Pulumi code which adapter, project, and cloud to use. `git_repo_url` can be `""` if not needed — the Azure Pulumi code falls back gracefully:

```bash
cat > local_development/<adapter>/pulumi/dwe-hydration.yaml << EOF
adapter_name: <adapter>
project_name: <project_name>
git_repo_url: <git_repo_url or "">
adapter_version: local
cloud_provider: <cloud_provider>
environments: [<environment>]
EOF
```

### Step 5 — Generate run-local.sh

Write `local_development/<adapter>/run-local.sh`. Key lessons learned:
- Create a `venv/` virtualenv and set `VIRTUAL_ENV` + `PATH` before running Pulumi — otherwise `pulumi-language-python-exec` uses the system Python and can't find the `pulumi` module even though `Pulumi.yaml` has `virtualenv: venv`.
- `PULUMI_CONFIG_PASSPHRASE=""` is required or Pulumi will prompt interactively.
- `--yes` must only be passed for `up`, not `preview` — use `${ACTION:+--yes}`.

**Azure version:**
```bash
cat > local_development/<adapter>/run-local.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

# Source .env — exports all secrets as env vars, same as GitHub secrets in CI
set -a && source "$(dirname "$0")/.env" && set +a

ACTION=${1:-preview}
WORKSPACE=<environment>
SM_SECRET=<secret_name>
PROJECT=<project_name>

cd "$(dirname "$0")/pulumi"
if [ ! -d venv ]; then python3 -m venv venv; fi
venv/bin/pip install -r requirements.txt -q

# Must set VIRTUAL_ENV + PATH so Pulumi's Python exec wrapper finds the right interpreter
export VIRTUAL_ENV="$(pwd)/venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"

# Login to Pulumi state backend (mirrors CI: cloud-url secret)
pulumi login "$PULUMI_AZURE_STATE"

# Authenticate Azure provider (mirrors CI: azure/login step)
az login --service-principal \
  -u "$AZURE_CLIENT_ID" \
  -p "$AZURE_CLIENT_SECRET" \
  --tenant "$AZURE_TENANT_ID" \
  --output none

# Set Pulumi stack config (exact commands from CI init-stack step)
pulumi stack select "$WORKSPACE" 2>/dev/null || pulumi stack init "$WORKSPACE"
pulumi config set "${PROJECT}:environment"     "$WORKSPACE"             --stack "$WORKSPACE"
pulumi config set "${PROJECT}:git_branch"      "<environment>"          --stack "$WORKSPACE"
pulumi config set "${PROJECT}:secret_id"       "$SM_SECRET"             --stack "$WORKSPACE" --plaintext
pulumi config set "${PROJECT}:key_vault_name"  "$KEY_VAULT_NAME"        --stack "$WORKSPACE"
pulumi config set "${PROJECT}:resource_group"  "$RESOURCE_GROUP"        --stack "$WORKSPACE"
pulumi config set "${PROJECT}:subscription_id" "$AZURE_SUBSCRIPTION_ID" --stack "$WORKSPACE"
pulumi config set "${PROJECT}:cloud_provider"  "azure"                  --stack "$WORKSPACE"

# Run Pulumi with same env vars CI injects into the pulumi/actions step
ARM_CLIENT_ID="$AZURE_CLIENT_ID" \
ARM_CLIENT_SECRET="$AZURE_CLIENT_SECRET" \
ARM_TENANT_ID="$AZURE_TENANT_ID" \
ARM_SUBSCRIPTION_ID="$AZURE_SUBSCRIPTION_ID" \
AZURE_STORAGE_ACCOUNT="$AZURE_STORAGE_ACCOUNT" \
PULUMI_BACKEND_URL="$PULUMI_AZURE_STATE" \
PULUMI_CONFIG_PASSPHRASE="" \
pulumi "$ACTION" --stack "$WORKSPACE" ${ACTION:+--yes}
SCRIPT
chmod +x local_development/<adapter>/run-local.sh
```

**AWS version:**
```bash
cat > local_development/<adapter>/run-local.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

set -a && source "$(dirname "$0")/.env" && set +a

ACTION=${1:-preview}
WORKSPACE=<environment>
PROJECT=<project_name>

cd "$(dirname "$0")/pulumi"
if [ ! -d venv ]; then python3 -m venv venv; fi
venv/bin/pip install -r requirements.txt -q

export VIRTUAL_ENV="$(pwd)/venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"

pulumi login "$PULUMI_S3_STATE"

pulumi stack select "$WORKSPACE" 2>/dev/null || pulumi stack init "$WORKSPACE"
pulumi config set "${PROJECT}:cloud_provider" "aws" --stack "$WORKSPACE"

AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
AWS_DEFAULT_REGION="$AWS_DEFAULT_REGION" \
PULUMI_BACKEND_URL="$PULUMI_S3_STATE" \
PULUMI_CONFIG_PASSPHRASE="" \
pulumi "$ACTION" --stack "$WORKSPACE" ${ACTION:+--yes}
SCRIPT
chmod +x local_development/<adapter>/run-local.sh
```

### Step 6 — Run

```bash
# Preview (safe, no changes)
bash local_development/<adapter>/run-local.sh preview

# Apply
bash local_development/<adapter>/run-local.sh up
```

> Use `bash` explicitly to avoid "no such file" errors from relative path resolution in some shells.

## Common issues

- **`ModuleNotFoundError: No module named 'pulumi'`**: Pulumi's Python exec wrapper ignores `virtualenv: venv` from `Pulumi.yaml` unless `VIRTUAL_ENV` and `PATH` are exported. The `run-local.sh` script handles this — if hitting this error manually, run: `export VIRTUAL_ENV=$(pwd)/pulumi/venv && export PATH="$VIRTUAL_ENV/bin:$PATH"` before `pulumi up`.
- **`--unsafe: Unknown switch`**: copier 9.x renamed the flag to `--UNSAFE` (uppercase). Always use `--UNSAFE`.
- **`copier: command not found`**: `pip install copier`
- **`dwe` not installed**: `pip install -e .` from dwe-core root
- **Auth error**: check the service principal in `.env` has Contributor on the resource group / AWS IAM permissions
- **`pulumi: command not found`**: `brew install pulumi` or follow pulumi.com/docs/install
- **Pulumi can't find runtime secrets**: `secret_id` in Pulumi config must match an actual secret in Key Vault / SM — Pulumi fetches it at deploy time. Only CI credentials go in `.env`.
- **`--yes` on preview**: `${ACTION:+--yes}` only appends `--yes` when action is `up` — preview never auto-approves.
