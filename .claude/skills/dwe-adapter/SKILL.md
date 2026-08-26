---
name: dwe-adapter
description: "Reference for dwe adapter repos (dwe_trino, dwe_cube, etc.) — structure, how dwe-core hydrates them, how dwe-hub drives the UI, and how to write or modify an adapter."
---

# DWE Adapter Reference

## What an adapter is

An adapter is a self-contained Pulumi + Docker repo that provisions and runs one data tool (Trino, Cube, Superset, Airflow, …) on Azure or AWS. dwe-core manages the lifecycle (create, update, destroy). dwe-hub provides the web UI. Each adapter is a copier template — dwe-core stamps it out with project-specific values when a customer installs it.

---

## Anatomy of an adapter repo

```
{adapter}/
├── copier.yml                    # Metadata, UI config, secrets manifest
├── docker-compose.yml            # Production services
├── docker-compose.override.yml   # Local-dev overrides
├── envs_prod.json                # Config file templates (production)
├── envs_dev.json                 # Config file templates (dev)
├── envs_prod.json.jinja          # Jinja source for envs_prod.json
├── config_generator.py           # Writes real config files from envs_*.json + .env
├── .env.example                  # Secret key documentation
├── ci-templates/
│   ├── github.yaml               # GitHub Actions workflow (Jinja template)
│   └── gitlab.yaml               # GitLab CI/CD template
└── pulumi/
    ├── __main__.py               # Entry point: reads cloud_provider, delegates
    ├── _azure.py                 # Azure resources (VMSS, App Gateway, KV, DNS…)
    ├── _aws.py                   # AWS resources (ASG, ALB, Route53, IAM…)
    ├── _startup.py               # Shared Ubuntu boot script fragments
    ├── dwe-hydration.yaml.jinja  # Written by dwe-core at deploy time
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
    - name: Application Gateway
      kg:
        trigger_secret: APP_GW_SUBNET_ID  # Only shown when this secret is present
        properties:
          endpoint: DNS_RECORD_NAME        # Maps property → secret key
  kg_pulumi_outputs:                   # Pulumi outputs pushed to KG after deploy
    url: url
    appgw_name: appgw_name
    coordinator_vmss_name: coordinator_vmss_name
  ci_templates:
    github: ci-templates/github.yaml
```

### Parameters — what dwe-hub renders as form fields

```yaml
instance_type:
  type: str
  default: Standard_D4s_v3
  help: "VM size"
  x_dwe_editable: true    # ← dwe-hub shows this field as editable
  x_dwe_per_env: true     # ← each environment (prod/dev) has its own value

worker_count:
  type: int
  default: 1
  x_dwe_editable: true
  x_dwe_per_env: true

secret_id:
  type: str
  default: DWE_DEPLOY_TRINO
  x_dwe_editable: true
  x_dwe_per_env: false    # ← same value across all envs
```

Parameters with `when: false` are set by dwe-core, not shown to users (`git_repo_url`, `adapter_name`, `cloud_provider`, etc.).

### `required_secrets`

```yaml
required_secrets:
  - key: AZURE_CLIENT_ID
    description: "Service principal client ID"
    destination: ci                # → GitHub/GitLab repo secret
    cloud_provider: azure          # Only for this cloud

  - key: VNET_ID
    description: "Azure VNet resource ID"
    destination: secrets_manager   # → Azure Key Vault / AWS Secrets Manager
```

`destination: ci` → dwe-hub tells the user to add it as a CI secret.
`destination: secrets_manager` → goes into the Key Vault / Secrets Manager secret JSON blob.

---

## dwe-core's role

dwe-core is the backend that manages adapter instances. When it creates or updates a service it:

1. Runs `copier copy <adapter_repo> <output_dir>` with the user's parameter values
2. Writes `pulumi/dwe-hydration.yaml` from `dwe-hydration.yaml.jinja`:
   ```yaml
   adapter_name: dwe_trino
   project_name: acme-trino
   git_repo_url: https://github.com/acme/trino-deploy
   adapter_version: v1.2.0
   cloud_provider: azure
   environments: [prod, dev]
   ```
3. Renders CI templates and commits to the customer repo
4. Triggers `pulumi up` per environment

**Key file**: `dwe-hydration.yaml` is the runtime config that Pulumi reads at deploy time. It is NOT committed to the adapter template repo (excluded in `_exclude`).

---

## dwe-hub's role

dwe-hub is the web UI. It:
- Reads `copier.yml` to build the configuration form
- Shows `x_dwe_editable` parameters as editable, groups `x_dwe_per_env` ones per-environment
- Calls dwe-core APIs to apply changes
- Displays the services listed in `_dwe_hub.services`
- Shows Pulumi outputs from `kg_pulumi_outputs` (URL, VMSS names, etc.)

---

## Pulumi structure

### `__main__.py` — cloud router

```python
_dwe = yaml.safe_load((Path(__file__).parent / "dwe-hydration.yaml").read_text())
cloud_provider = _dwe.get("cloud_provider", "azure")
if cloud_provider == "azure":
    import _azure
else:
    import _aws
```

### `_startup.py` — shared Ubuntu boot fragments

```python
install_packages_and_docker()   # apt + Docker + Compose
clone_repo(repo_url, branch)    # git clone via deploy token
write_env_from_secret_json()    # echo $SECRET_JSON | jq → .env
generate_config_and_start(n)    # config_generator.py + docker-compose up --scale trino-worker=N
```

Both `_azure.py` and `_aws.py` import these and compose them with cloud-specific sections.

### `_azure.py` — Azure-specific

Cloud-specific sections:
1. **Azure CLI install** — `curl -sL https://aka.ms/InstallAzureCLIDeb | bash`
2. **Key Vault secret fetch** — `az login --identity && az keyvault secret show …`
3. **Nessie startup** — `docker run --network host projectnessie/nessie` (Azure only, self-hosted)
4. **Infra value injection** — appends `NESSIE_DB_URL`, `AZURE_STORAGE_KEY`, `CATALOG_URL`, etc. to `.env`

Resources provisioned:
- User-assigned Managed Identity + KV Secrets User role
- Storage Account (ADLS Gen2, Iceberg warehouse)
- PostgreSQL database (Nessie catalog backend)
- App Gateway (HTTP→HTTPS redirect + backend pool)
- Network Security Group
- Coordinator VMSS (capacity=1, `replace_on_changes=["virtualMachineProfile"]`, `delete_before_replace=True`)
- Azure DNS A record

### `_aws.py` — AWS-specific

Cloud-specific sections:
1. **AWS CLI install** — downloads from `awscli.amazonaws.com`
2. **Secrets Manager fetch** — `aws secretsmanager get-secret-value …`
   - On AWS, CATALOG_URL and ICEBERG_WAREHOUSE_DIR are pre-stored in Secrets Manager, not computed at boot

Resources provisioned: IAM role, Launch Template, ALB + listeners, ASG, Route53 CNAME.

---

## VM startup flow (single VM = coordinator + worker)

Both coordinator and Trino workers run on the **same VM** in Docker containers on the Docker bridge. This eliminates inter-VM connectivity complexity.

```
VM boots → startup script runs:
  1. apt packages + Docker + Compose
  2. Cloud CLI install (az / aws)
  3. Fetch secrets from Key Vault / Secrets Manager
  4. git clone repo
  5. Write .env from secret JSON + injected infra values
  6. [Azure only] Start Nessie on --network host
  7. Compute DOCKER_GW (ip addr show docker0) → CATALOG_URL=http://DOCKER_GW:19120
  8. config_generator.py envs_prod.json --env-file .env
  9. docker-compose up -d --scale trino-worker=N
```

`discovery.uri=http://trino:8080` — Docker service name resolves on the bridge. Worker containers reach coordinator this way.

---

## envs_prod.json — config template format

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
      "type": "properties",
      "path": "trino/trino_connections/iceberg.properties",
      "properties": {
        "iceberg.nessie-catalog.uri": "${CATALOG_URL}/api/v1",
        "azure.access-key": "${AZURE_STORAGE_KEY}"
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

**Important**: `CATALOG_URL` must NOT include an API path (set it to `http://HOST:PORT`). The envs file appends `/api/v1` or `/api/v2`. Double-path (e.g. `/api/v2/api/v1`) causes Nessie 404.

---

## CI workflow — two paths

```
push/PR to prod branch
  ↓
detect-changes (dorny/paths-filter)
  ├─ infra changed (pulumi/**)?
  │   ├─ PR  → pulumi preview
  │   └─ push → pulumi up → reimage VMSS
  └─ app changed (non-pulumi), infra NOT changed?
       └─ push → reimage VMSS (git pull on fresh boot)
```

`startup_code_version` is set to `${{ github.sha }}` on each `pulumi up` — this touches `virtualMachineProfile.osProfile.customData`, triggering VMSS replacement (`replace_on_changes=["virtualMachineProfile"]`).

**No explicit `pip install` needed** — Pulumi creates its own venv and installs `requirements.txt` automatically.

---

## Writing a new adapter

1. Copy an existing adapter repo as a starting point
2. Update `copier.yml`:
   - Change `_dwe_hub.hub_name`, `display_name`, `description`
   - Update `services` to match the tool's endpoints
   - Update `required_secrets` for the tool's credentials
   - Add/remove parameters with `x_dwe_editable` / `x_dwe_per_env`
3. Update `docker-compose.yml` with the tool's services
4. Update `envs_prod.json` with the tool's config file templates
5. Update `pulumi/_azure.py` and `pulumi/_aws.py`:
   - Nessie startup is Trino-specific — remove if not needed
   - Add/remove infrastructure resources as needed
   - Keep `_startup.py` shared sections unchanged
6. Update `ci-templates/github.yaml` if VMSS query needs different tags
7. Register in dwe-core's adapter registry

---

## Common pitfalls

- **VMSS stuck in-place update**: add `replace_on_changes=["virtualMachineProfile"]` + `delete_before_replace=True` to VMSS opts
- **Workers not registering**: ensure `discovery.uri` is reachable — on single VM use `http://trino:8080` (Docker service name)
- **Double API path in Nessie URI**: `CATALOG_URL` should be the base URL only; envs file appends the path
- **Run Command extension blocking reimage**: delete via `az rest --method delete --url ".../extensions/RunCommandHandlerLinux?api-version=2024-03-01"`
- **Stale Pulumi lock**: delete the `.json` blob in the Pulumi state container
