## Why

`adapters.json` duplicated all adapter metadata that already lives in each adapter repo's `copier.yml` under `_dwe_hub`, creating a two-source-of-truth problem where descriptions, secrets, services, and display properties could silently drift between the registry and the adapter itself.

## What Changes

- `dwe/adapters.json` is reduced to `{ url, type }` per adapter — pointer only, no metadata
- Each adapter repo's `copier.yml` becomes the sole source of truth for its `_dwe_hub` metadata block
- `dwe_cube/copier.yml`: added `description`, `Application Load Balancer` and `DNS` services, and `EC2_SECURITY_GROUP_ID` / `LB_SECURITY_GROUP_ID` / `ALB_INTERNAL` required secrets
- `dwe_dbt_kg/copier.yml`: added `description`, `POSTGRES_PASSWORD` required secret, and `POSTGRES_USER` / `POSTGRES_DB` / `EBS_FALKORDB_STORAGE_PERSIST` optional secrets
- `registry.py:get_adapter_catalog()` required no changes — it already fetched and merged `_dwe_hub` from copier.yml; adapters.json values were simply winning over it before

## Capabilities

### New Capabilities

- `adapter-metadata-from-copier`: Adapter metadata (display info, services, secrets) is discovered at runtime from each adapter repo's `copier.yml` `_dwe_hub` section, not from `adapters.json`

### Modified Capabilities

*(none — no spec-level behavior changes, only where data lives)*

## Impact

- **`dwe-core/dwe/adapters.json`**: stripped to `{url, type}` per adapter
- **`dwe_cube/copier.yml`**: `_dwe_hub` section now carries full metadata including missing secrets and services
- **`dwe_dbt_kg/copier.yml`**: `_dwe_hub` section now carries full metadata including missing secrets
- **`dwe-hub`**: no changes needed — consumes adapter data exclusively via `dwe.registry.get_adapter_catalog()`
- **`dwe-core/dwe/registry.py`**: no changes needed
