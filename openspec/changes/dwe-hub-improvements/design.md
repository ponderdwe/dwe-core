# Design: dwe-hub Improvements

## Fix 1: Alembic migrations

### Current flow (remove)
```python
# database.py — runs on every app startup
def run_migrations(engine):
    # Checks information_schema, adds columns, creates indexes
    # Fragile: silently fails for renames, type changes, index removal
    with engine.connect() as conn:
        if not column_exists(conn, "assets", "source_uuid"):
            conn.execute("ALTER TABLE assets ADD COLUMN source_uuid VARCHAR")
```

### Target flow
```
alembic/
├── env.py              # Alembic environment config
├── script.py.mako      # Migration template
└── versions/
    ├── 001_initial_schema.py
    ├── 002_add_source_uuid.py
    └── ...

entrypoint.sh:
  alembic upgrade head   ← runs before app starts
  python -m flask run    ← then starts app
```

Migration authoring:
```bash
# Generate new migration after model change
alembic revision --autogenerate -m "add connector to deployment config"

# Apply
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

### database.py after
Remove `run_migrations()` entirely. `database.py` retains only: engine creation, `session_scope()`, `get_db_session()`.

---

## Fix 2: Org secrets — Secrets Manager only in production

### Current flow
```python
# secret_service.py
def get_org_secrets(org_slug: str) -> dict:
    env_key = f"{org_slug.upper().replace('-', '_')}_DEPLOY"
    
    # Check env var first (works locally, doesn't scale)
    if env_key in os.environ:
        return json.loads(os.environ[env_key])
    
    # Fall back to AWS Secrets Manager
    return _fetch_from_secrets_manager(org_slug)
```

### Target flow
```python
def get_org_secrets(org_slug: str) -> dict:
    if current_app.config["DEBUG"]:
        # Local dev only: allow env var fallback
        env_key = f"{org_slug.upper().replace('-', '_')}_DEPLOY"
        if env_key in os.environ:
            return json.loads(os.environ[env_key])
    
    # Production: always AWS Secrets Manager
    secret = _fetch_from_secrets_manager(org_slug)
    if secret is None:
        raise SecretNotFoundError(
            f"No secrets found for org '{org_slug}' in AWS Secrets Manager. "
            f"Expected secret key: '{org_slug}_DEPLOY'"
        )
    return secret
```

Local dev `.env` (kept):
```
SCHOOL_ACME_DEPLOY={"AWS_ACCESS_KEY_ID": "...", "GIT_TOKEN": "..."}
```

Production: remove all `*_DEPLOY` env vars from EC2 instance. Always resolve from Secrets Manager.

---

## Fix 3: Connector in DeploymentConfig adapter enum

### Current model
```python
class AdapterType(enum.Enum):
    SUPERSET = "SUPERSET"
    CUBE = "CUBE"
    DBT_KG = "DBT_KG"
```

### Target model
```python
class AdapterType(enum.Enum):
    SUPERSET = "SUPERSET"
    CUBE = "CUBE"
    DBT_KG = "DBT_KG"
    ICEBERG = "ICEBERG"
    AIRFLOW = "AIRFLOW"
    FALKORDB = "FALKORDB"
    CONNECTOR = "CONNECTOR"   # ← new: for tracking connector installations
```

Connector `DeploymentConfig` records: which connector is installed, in which org's environment. No `pulumi up` — just a record that the connector package was installed.

---

## Fix 4: Dashboard import dependency check (specced, deferred)

### Target flow (future implementation)

```
User: Import Dashboard "Attendance by School"
  │
  ▼
dwe-hub: GET /api/v1/assets/{uuid}/requirements
  │
  ▼
dwe-hub queries org's KG:
  GET {org.kg_api_host}/adapters?env={env}
  │
  ▼
Gap analysis:
  Dashboard requires: [dwe_superset, dwe_cube, dwe_iceberg]
  Org has deployed:   [dwe_superset, dwe_iceberg]
  Missing:            [dwe_cube]
  │
  ▼
Response to UI:
  {
    "can_import": true,   # superset is deployed
    "warnings": [
      {
        "adapter": "dwe_cube",
        "message": "Dashboard uses Semantic Layer queries. Deploy dwe_cube for full functionality.",
        "required": false
      }
    ]
  }
  │
  ▼
UI: Shows warning with [Deploy Cube →] and [Import Anyway →] options
```

### What this requires before implementation
- `dwe_falkordb` deployed in the org (to have a KG to query)
- `DeploymentConfig` stores `kg_api_host` and `kg_api_token` per org
- Dashboard assets have declared requirements (future asset spec)
