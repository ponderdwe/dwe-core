---
name: dwe-adapter
description: "Reference for dwe adapter repos (dwe_trino, dwe_cube, dwe_superset, dwe_coder, dwe_litellm, dwe_airflow, etc.) — structure, how dwe-core hydrates them, how dwe-hub drives the UI, and how to write or modify an adapter."
---

# DWE Adapter Reference

## What an adapter is

An adapter is a self-contained Pulumi + Docker repo that provisions and runs one data tool (Trino, Cube, Superset, Airflow, …) on Azure or AWS. dwe-core manages the lifecycle (create, update, destroy). dwe-hub provides the web UI. Each adapter is a copier template — dwe-core stamps it out with project-specific values when a customer installs it.

---

## Two adapter flavors

### Complex adapter (dwe_trino)
Tools that need generated config files (`.properties`, htpasswd, etc.) use a config generator:
```
dwe_trino/
├── config_generator.py           # Writes real config files from envs_*.json + .env
├── envs_prod.json                # Config file templates (production)
├── envs_dev.json                 # Config file templates (dev)
├── envs_prod.json.jinja
└── pulumi/
    └── _startup.py               # Shared Ubuntu boot script fragments (imported by _azure/_aws)
```

### Simple adapter (dwe_superset, dwe_coder, dwe_litellm, dwe_airflow)
Tools that read env vars directly at runtime — no config file generation needed. The startup script is inlined directly in `_azure.py` / `_aws.py` as a Python f-string. No `_startup.py`, no `envs_*.json`, no `config_generator.py`.

---

## Anatomy of an adapter repo

```
{adapter}/
├── copier.yml                    # Metadata, UI config, secrets manifest
├── docker-compose.yml            # Production services (no local db/redis)
├── docker-compose.override.yml   # Local-dev overrides (adds postgres, redis, etc.)
├── .env.example                  # Secret key documentation
├── ci-templates/
│   ├── github.yaml               # GitHub Actions workflow (Jinja template, {@ @} delimiters)
│   └── gitlab.yaml               # GitLab CI/CD template
└── pulumi/
    ├── __main__.py               # Entry point: reads cloud_provider, delegates
    ├── _azure.py                 # Azure resources (VMSS, App Gateway, KV, DNS…)
    ├── _aws.py                   # AWS resources (ASG, ALB, Route53, IAM…)
    ├── dwe-hydration.yaml.jinja  # Template; dwe-core writes the real file at deploy time
    ├── Pulumi.yaml.jinja
    ├── Pulumi.prod.yaml.jinja
    ├── Pulumi.dev.yaml.jinja
    └── requirements.txt.jinja
```

---

## copier.yml — the central contract

### `_dwe_hub` block — UI metadata

```yaml
_dwe_hub:
  hub_name: trino                      # Internal key
  display_name: "Trino Query Engine"
  description: "…"
  icon: database
  cloud_providers: [azure, aws]
  services:                            # Listed in dwe-hub service panel
    - name: Trino
      description: "REST API on port 8080"
    - name: DNS
      kg:
        trigger_secret: DNS_NAME       # Only shown when this secret is present
        properties:
          hostname: DNS_NAME           # Maps property → secret key
  kg_pulumi_outputs:                   # Pulumi outputs pushed to KG after deploy
    url: url
    asg_name: asg_name
  ci_templates:
    github: ci-templates/github.yaml
    gitlab: ci-templates/gitlab.yaml
```

### Parameters — what dwe-hub renders as form fields

```yaml
instance_type:
  type: str
  default: r6i.large
  help: "EC2 instance type"
  x_dwe_editable: true    # ← dwe-hub shows this field as editable
  x_dwe_per_env: true     # ← each environment (prod/dev) has its own value

secret_id:
  type: str
  default: DWE_DEPLOY_SUPERSET
  x_dwe_editable: true
  x_dwe_per_env: false    # ← same value across all envs
```

Parameters with `when: false` are set by dwe-core, not shown to users (`git_repo_url`, `adapter_name`, `cloud_provider`, etc.).

### `required_secrets`

`required_secrets` is nested inside `_dwe_hub`, not a top-level key:

```yaml
_dwe_hub:
  hub_name: coder
  # ...
  required_secrets:
    - key: AZURE_CLIENT_ID
      description: "Service principal client ID"
      destination: ci                # → GitHub/GitLab repo secret
      cloud_provider: azure          # Only for this cloud

    - key: DB_HOST
      description: "PostgreSQL server hostname"
      destination: secrets_manager   # → Azure Key Vault / AWS Secrets Manager
      # no cloud_provider → applies to both clouds

    - key: DB_PASS
      description: "PostgreSQL master password"
      destination: secrets_manager
```

`destination: ci` → dwe-hub tells the user to add it as a CI secret.
`destination: secrets_manager` → goes into the Key Vault / Secrets Manager secret JSON blob.

**DB secrets pattern**: adapters accept `DB_HOST` + `DB_PASS` (+ optional `DB_USER`, `DB_PORT`) rather than a full connection string. The Pulumi code constructs the connection string and creates the database in the existing cluster.

---

## dwe-core's role

dwe-core is the backend that manages adapter instances. When it creates or updates a service it:

1. Runs `copier copy <adapter_repo> <output_dir>` with the user's parameter values
2. Writes `pulumi/dwe-hydration.yaml` from `dwe-hydration.yaml.jinja`:
   ```yaml
   adapter_name: dwe_superset
   project_name: acme-superset
   git_repo_url: https://github.com/acme/superset-deploy
   adapter_version: v1.0.0
   cloud_provider: azure
   environments: [prod, dev]
   ```
3. Renders CI templates using `{@ VAR @}` substitution and commits to the customer repo
4. Triggers `pulumi up` per environment

**Key file**: `dwe-hydration.yaml` is the runtime config that Pulumi reads at deploy time. It is excluded from copier output (`_exclude` in `copier.yml`) — dwe-core writes it to the customer repo after copier runs and commits it. It MUST be committed to the customer deploy repo so the VM can read it after `git clone`. **Do not add `pulumi/dwe-hydration.yaml` to the adapter template's `.gitignore`** — that gitignore gets committed to the deploy repo, causing dwe-hub's written file to be ignored and never committed, leaving `git_repo_url` empty in the startup script (manifests as `fatal: unable to access 'https:///'`).

**CI template variables**: dwe-core uses uppercase `{@ PROJECT_NAME @}`, `{@ CLOUD_PROVIDER @}`, `{@ ENV_NAME @}`, `{@ WORKSPACE_NAME @}`, `{@ AWS_REGION @}`, `{@ SECRET_NAME @}`, `{@ GIT_REPO_URL @}`. Copier variables (`{{ project_name }}`) are different — do NOT use `{@ project_name @}` (lowercase) in CI templates; use `{@ PROJECT_NAME @}`.

---

## dwe-hub's role

dwe-hub is the web UI. It:
- Reads `copier.yml` to build the configuration form
- Shows `x_dwe_editable` parameters as editable, groups `x_dwe_per_env` ones per-environment
- Calls dwe-core APIs to apply changes
- Displays the services listed in `_dwe_hub.services`
- Shows Pulumi outputs from `kg_pulumi_outputs` (URL, VMSS/ASG names, etc.)

---

## Pulumi structure

### `__main__.py` — cloud router (with dwe-hydration.yaml fallback)

```python
import yaml
import pulumi
from pathlib import Path

_hydration = Path(__file__).parent / "dwe-hydration.yaml"
if _hydration.exists():
    cloud_provider = yaml.safe_load(_hydration.read_text()).get("cloud_provider", "azure")
else:
    cloud_provider = pulumi.Config().get("cloud_provider") or "azure"

if cloud_provider == "azure":
    import _azure  # noqa: F401
else:
    import _aws  # noqa: F401
```

The fallback is essential: `dwe-hydration.yaml` does not exist until dwe-core writes it. CI runs on fresh checkouts before that file is present.

### Hydration block in `_azure.py` / `_aws.py`

```python
_hydration = Path(__file__).parent / "dwe-hydration.yaml"
_dwe = yaml.safe_load(_hydration.read_text()) if _hydration.exists() else {}
if _dwe:
    project_name    = _dwe["project_name"]
    git_repo_url    = _dwe["git_repo_url"]
    adapter_version = _dwe["adapter_version"]
else:
    _cfg            = pulumi.Config()
    project_name    = _cfg.get("project_name") or pulumi.get_project()
    git_repo_url    = _cfg.get("git_repo_url") or ""
    adapter_version = _cfg.get("adapter_version") or "v1.0.0"
```

`pulumi.get_project()` returns the project name from `Pulumi.yaml` (e.g. "coder-deploy") — used as ultimate fallback so resource names are always valid even without the hydration file.

`_dwe` must always be defined (even as `{}`) because it is also accessed later for `_dwe.get("kg_mappings")`.

### `_startup.py` — shared boot fragments (Trino only)

```python
install_packages_and_docker()   # apt + Docker + Compose
clone_repo(repo_url, branch)    # git clone via deploy token
write_env_from_secret_json()    # echo $SECRET_JSON | jq → .env
generate_config_and_start(n)    # config_generator.py + docker-compose up --scale trino-worker=N
```

Simple adapters (Superset, Coder, LiteLLM, Airflow) inline the startup script directly in `_azure.py` / `_aws.py` as a Python f-string — no `_startup.py` import needed.

### `_azure.py` — Azure-specific resources

Resources provisioned (typical):
- User-assigned Managed Identity + KV Secrets User role assignment
- PostgreSQL database in existing Flexible Server (`pg.Database()` — idempotent)
- App Gateway (HTTP→HTTPS redirect + backend pool, `request_timeout` tuned per app)
- Network Security Group
- VMSS (capacity=1, `replace_on_changes=["virtualMachineProfile"]`, `delete_before_replace=True`)
- Azure DNS A/CNAME record

Azure startup script sequence:
1. apt packages + Docker + Docker Compose
2. Azure CLI install (`curl -sL https://aka.ms/InstallAzureCLIDeb | bash`)
3. `az login --identity` + Key Vault secret fetch → `$SECRET_JSON`
4. `git clone` repo
5. Write `.env` from `$SECRET_JSON` via `jq`
6. Append computed values (connection strings, etc.) to `.env`
7. `docker-compose up -d`

### `_aws.py` — AWS-specific resources

Resources provisioned (typical):
- IAM Role + Instance Profile (with managed policies, e.g. `AmazonBedrockFullAccess` for LiteLLM)
- EC2 Launch Template
- ALB + HTTP→HTTPS listeners + Target Group
- Auto Scaling Group (min/max=1)
- Route53 CNAME record

AWS startup script sequence:
1. apt packages + Docker + Docker Compose
2. AWS CLI install (from `awscli.amazonaws.com`)
3. `aws secretsmanager get-secret-value` → `$SECRET_JSON`
4. `git clone` repo
5. Write `.env` from `$SECRET_JSON` via `jq`
6. `apt-get install -y postgresql-client` + `psql CREATE DATABASE` (idempotent)
7. Append connection strings to `.env`
8. `docker-compose up -d`

---

## Database creation pattern

Adapters receive `DB_HOST` + `DB_PASS` pointing at an **existing** PostgreSQL cluster and create their own database in it at deploy time.

**Azure** — Pulumi resource (in `_azure.py`, after `kv_access` role assignment):
```python
import pulumi_azure_native.dbforpostgresql.v20221201 as pg

db_host = secrets["DB_HOST"]
db_name = f"{adapter}_{env}" if env != "prod" else adapter  # e.g. "superset_dev" / "superset"

pg.Database(
    f"{project_name}-pg-db{suffix}",
    resource_group_name=resource_group,
    server_name=db_host.split(".")[0],   # "myserver" from "myserver.postgres.database.azure.com"
    database_name=db_name,
    opts=pulumi.ResourceOptions(depends_on=[kv_access]),
)
```

**AWS** — psql in user_data (idempotent):
```bash
apt-get install -y postgresql-client
PGPASSWORD={db_pass} psql -h {db_host} -U {db_user} -d postgres \
  -c "CREATE DATABASE {db_name};" 2>/dev/null || true
echo "SQLALCHEMY_DATABASE_URI=postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}" \
  >> /home/ubuntu/{app}/.env
```

DB name convention: always `{adapter}_{env}` (e.g. `coder_prod`, `coder_dev`, `nessie_prod`, `nessie_dev`).

---

## VM startup flow (simple adapters — Superset, Coder, LiteLLM, Airflow)

```
VM boots → startup script runs:
  1. apt packages + Docker + Compose
  2. Cloud CLI install (az / aws)
  3. Fetch secrets from Key Vault / Secrets Manager
  4. git clone repo
  5. Write .env from secret JSON via jq
  6. [AWS only] Install postgresql-client + psql CREATE DATABASE
  7. Append computed values (connection strings, API URLs) to .env
  8. docker-compose up -d
```

## VM startup flow (Trino — complex adapter)

```
VM boots → startup script runs:
  1. apt packages + Docker + Compose
  2. Cloud CLI install (az / aws)
  3. Fetch secrets from Key Vault / Secrets Manager
  4. git clone repo
  5. Write .env from secret JSON + injected infra values
  6. [Azure only] Start Nessie on --network host, then wait until healthy:
     `until curl -sf http://localhost:19120/api/v2/config; do sleep 5; done`
  7. Compute DOCKER_GW (ip addr show docker0) → CATALOG_URL=http://DOCKER_GW:19120
  8. config_generator.py envs_prod.json --env-file .env
  9. docker-compose up -d --scale trino-worker=N
```

---

## envs_prod.json — config template format (Trino only)

```json
{
  "environment": "prod",
  "files": [
    {
      "type": "properties",
      "path": "trino/coordinator-config.properties",
      "properties": {
        "discovery.uri": "http://trino:8080",
        "internal-communication.shared-secret": "${TRINO_SHARED_SECRET}"
      }
    },
    {
      "type": "db",
      "path": "trino/password.db",
      "username_var": "TRINO_USER",
      "password_var": "TRINO_PASSWORD"
    }
  ]
}
```

`config_generator.py` resolves `${VAR}` from `.env`. Supported types: `properties`, `env`, `db` (htpasswd), `custom`.

**Important**: `CATALOG_URL` must NOT include an API path. The envs file appends `/api/v1` or `/api/v2`. Double-path causes Nessie 404.

---

## CI workflow — two paths

```
push/PR to prod/dev branch
  ↓
detect-changes (dorny/paths-filter)
  ├─ infra changed (pulumi/**)?
  │   ├─ PR  → pulumi preview
  │   └─ push → pulumi up → reimage VMSS / ASG instance refresh
  └─ app changed (non-pulumi), infra NOT changed?
       └─ push → reimage VMSS / ASG instance refresh
```

`startup_code_version` is set to `${{ github.sha }}` on each `pulumi up` — this touches `virtualMachineProfile.osProfile.customData`, triggering VMSS replacement (`replace_on_changes=["virtualMachineProfile"]`).

**No explicit `pip install` needed** — Pulumi creates its own venv and installs `requirements.txt` automatically.

### CI Pulumi config init (Azure preview and apply steps)

```yaml
pulumi stack select ${{ env.WORKSPACE }} 2>/dev/null || pulumi stack init ${{ env.WORKSPACE }}
pulumi config set {@ PROJECT_NAME @}:environment ${{ env.WORKSPACE }} --stack ${{ env.WORKSPACE }}
pulumi config set {@ PROJECT_NAME @}:git_branch {@ ENV_NAME @} --stack ${{ env.WORKSPACE }}
pulumi config set {@ PROJECT_NAME @}:secret_id ${{ env.SM_SECRET }} --stack ${{ env.WORKSPACE }} --plaintext
pulumi config set {@ PROJECT_NAME @}:key_vault_name ${{ secrets.KEY_VAULT_NAME }} --stack ${{ env.WORKSPACE }}
pulumi config set {@ PROJECT_NAME @}:resource_group ${{ secrets.RESOURCE_GROUP }} --stack ${{ env.WORKSPACE }}
pulumi config set {@ PROJECT_NAME @}:subscription_id ${{ secrets.AZURE_SUBSCRIPTION_ID }} --stack ${{ env.WORKSPACE }}
pulumi config set {@ PROJECT_NAME @}:cloud_provider {@ CLOUD_PROVIDER @} --stack ${{ env.WORKSPACE }}
```

`cloud_provider` must be set in Pulumi config so `__main__.py` can fall back to it when `dwe-hydration.yaml` is absent. `project_name` is NOT set — `pulumi.get_project()` handles it automatically.

---

## Writing a new adapter

### Simple adapter (no config files needed)

1. Copy `dwe_superset` or `dwe_coder` as a starting point
2. Update `copier.yml`:
   - Change `_dwe_hub.hub_name`, `display_name`, `description`, `icon`
   - Update `services` and `kg_pulumi_outputs`
   - Update `required_secrets` — use `DB_HOST`/`DB_PASS` instead of full connection strings
   - Add parameters with `x_dwe_editable` / `x_dwe_per_env`
3. Update `docker-compose.yml` — production services only (no local db/redis)
4. Update `docker-compose.override.yml` — add local postgres/redis for dev
5. Update `pulumi/_azure.py` and `pulumi/_aws.py`:
   - Change `app_port` to match the tool's HTTP port
   - Change health check path
   - Update the `docker-compose up` command if named services are needed
   - Add DB creation: `pg.Database()` on Azure, `psql CREATE DATABASE` on AWS
   - Update the `.env` echo block with connection strings
6. Keep the `__main__.py` and hydration fallback pattern unchanged
7. Register in `dwe-core/dwe/adapters.json`

### Complex adapter (needs config files)

Use `dwe_trino` as the starting point. Keep `_startup.py`, `config_generator.py`, `envs_prod.json`.

---

## Common pitfalls

- **`dwe-hydration.yaml` missing in CI**: normal — file is written by dwe-core after copier runs. The `__main__.py` and provider files fall back to `pulumi.Config()` then `pulumi.get_project()`.
- **`fatal: unable to access 'https:///'` on VM boot**: `git_repo_url` is empty in the startup script. Root cause: `pulumi/dwe-hydration.yaml` is in the adapter template's `.gitignore`, so dwe-hub writes the file but it never gets committed to the deploy repo, and the VM clones a repo without it. Fix: remove `pulumi/dwe-hydration.yaml` from the adapter's `.gitignore`. Re-hydrate from dwe-hub to commit the file.
- **`project_name` empty → resource names start with `-`**: happens when CI sets `project_name` to empty string (e.g., `{@ project_name @}` lowercase renders empty). Do NOT set `project_name` in CI config — `pulumi.get_project()` returns the correct value from `Pulumi.yaml`.
- **`_dwe` NameError**: `_dwe` must always be defined even as `{}` — it is referenced later for `_dwe.get("kg_mappings")`. Use the `_dwe = ... if exists else {}` one-liner before the `if _dwe:` block.
- **`{@ project_name @}` vs `{@ PROJECT_NAME @}`**: dwe-core CI template variables are **uppercase** (`PROJECT_NAME`, `CLOUD_PROVIDER`, `ENV_NAME`, etc.). Lowercase copier variables (`project_name`) render as empty in CI templates.
- **VMSS stuck in-place update**: add `replace_on_changes=["virtualMachineProfile"]` + `delete_before_replace=True` to VMSS opts.
- **Workers not registering (Trino)**: ensure `discovery.uri` is reachable — on single VM use `http://trino:8080` (Docker service name).
- **Double API path in Nessie URI**: `CATALOG_URL` should be the base URL only; envs file appends the path.
- **Run Command extension blocking reimage**: delete via `az rest --method delete --url ".../extensions/RunCommandHandlerLinux?api-version=2024-03-01"`.
- **Stale Pulumi lock**: delete the `.json` blob in the Pulumi state container (Azure Blob / S3).
- **App Gateway request timeout**: default is 20s — increase for slow-starting apps (e.g., LiteLLM needs 600s for Bedrock streaming).
