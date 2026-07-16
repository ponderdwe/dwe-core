## 1. dwe_cube adapter repo

- [x] 1.1 Add `description` field to `_dwe_hub` in `copier.yml`
- [x] 1.2 Add `Application Load Balancer` and `DNS` entries to `_dwe_hub.services` in `copier.yml`
- [x] 1.3 Add `EC2_SECURITY_GROUP_ID`, `LB_SECURITY_GROUP_ID`, `ALB_INTERNAL` to `_dwe_hub.required_secrets` in `copier.yml`

## 2. dwe_dbt_kg adapter repo

- [x] 2.1 Add `description` field to `_dwe_hub` in `copier.yml`
- [x] 2.2 Add `POSTGRES_PASSWORD` to `_dwe_hub.required_secrets` in `copier.yml`
- [x] 2.3 Add `POSTGRES_USER`, `POSTGRES_DB`, `EBS_FALKORDB_STORAGE_PERSIST` to `_dwe_hub.optional_secrets` in `copier.yml`

## 3. dwe-core registry

- [x] 3.1 Slim `dwe/adapters.json` to `{ url, type }` per adapter — remove all metadata fields
