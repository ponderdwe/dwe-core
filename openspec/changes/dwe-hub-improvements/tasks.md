# Tasks: dwe-hub-improvements

## Fix 1: Alembic migrations

- [ ] Add `alembic` to `dwe_hub/requirements.txt`
- [ ] Run `alembic init alembic` in dwe-hub root, configure `alembic/env.py` with dwe-hub's SQLAlchemy engine
- [ ] Generate initial migration from current models: `alembic revision --autogenerate -m "initial_schema"`
- [ ] Review and clean up auto-generated migration (ensure it captures all existing tables/columns)
- [ ] Remove `run_migrations()` from `database.py`
- [ ] Update `entrypoint.sh`: add `alembic upgrade head` before Flask start
- [ ] Test: fresh `docker compose up` → migrations run → app starts → all features work
- [ ] Test: second `docker compose up` → "already at head" → no changes

## Fix 2: Org secrets — production only from Secrets Manager

- [ ] Update `secret_service.py` `get_org_secrets()`:
  - Wrap env var path in `if current_app.config.get("DEBUG"):`
  - Production path: only Secrets Manager, raise `SecretNotFoundError` if not found
- [ ] Add `SecretNotFoundError` exception class with clear message (includes expected Secrets Manager key name)
- [ ] Update `.env.example` with comment: "Org secrets below are for LOCAL DEV ONLY"
- [ ] Test locally: env var still works with `DWE_HUB_DEBUG=true`
- [ ] Test: with `DWE_HUB_DEBUG=false` and no AWS creds → `SecretNotFoundError` raised, not silent failure

## Fix 3: Adapter enum expansion

- [ ] Add to `AdapterType` enum in `models.py`: `ICEBERG`, `AIRFLOW`, `FALKORDB`, `CONNECTOR`
- [ ] Generate Alembic migration for the enum change
- [ ] Test: `POST /api/v1/organizations/{slug}/deploy-configs` with `adapter: "ICEBERG"` → 200 OK

## Future (specced, not implemented):

- [ ] (Deferred) Implement `GET /api/v1/assets/{uuid}/requirements` endpoint
- [ ] (Deferred) Implement KG query in Hub for deployment status check
- [ ] (Deferred) Import UI: show adapter gap warning before confirming import
