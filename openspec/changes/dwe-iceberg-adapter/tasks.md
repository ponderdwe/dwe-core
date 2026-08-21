# Tasks: dwe-iceberg-adapter

## Phase 1: Adapter repo setup

- [ ] Create `github.com/ponderdwe/dwe_iceberg` repo (if not exists)
- [ ] Add `copier.yml` with Copier questions and `_dwe_hub` metadata block
- [ ] Add `docker-compose.yml` with Trino + Nessie + MinIO
- [ ] Add `docker-compose.prod.yml` with Trino + Nessie (no MinIO)
- [ ] Add `.env.example` with all required env vars
- [ ] Add `justfile` with `just up` and `just deploy-prod`

## Phase 2: Trino + Nessie configuration

- [ ] Add `config/trino/catalog/iceberg.properties.jinja` (Nessie catalog config)
- [ ] Add `config/trino/config.properties` (Trino JVM + node config)
- [ ] Add `config/nessie/application.properties` (Nessie with MinIO/S3 backend)
- [ ] Test locally: `docker compose up` → Trino CLI → create Iceberg table

## Phase 3: Pulumi IaC

- [ ] Add `pulumi/__main__.py` with EC2 + S3 + ALB + Secrets Manager provisioning
- [ ] Add `pulumi/Pulumi.yaml.jinja`
- [ ] Add `pulumi/requirements.txt`
- [ ] Include static KG hydration block (reads dwe-hydration.yaml, calls PATCH /adapters)

## Phase 4: CI templates

- [ ] Add `ci-templates/github.yaml` (path-based: infra → pulumi up, app → SSM redeploy)
- [ ] Add `ci-templates/gitlab.yaml`

## Phase 5: dwe-core registration

- [ ] Add `dwe_iceberg` entry to `dwe/adapters.json`
- [ ] Test: `dwe list-adapters` shows dwe_iceberg
- [ ] Test: `dwe create-service dwe_iceberg --adapters-path /local/dwe_iceberg --git-repo ... --project-name test-school`
- [ ] Test with KG: register dwe_iceberg in local FalkorDB, verify in graph

## Phase 6: Local end-to-end validation

- [ ] `docker compose up` → Trino at :8080, Nessie at :19120
- [ ] Create schema, table, insert rows via Trino CLI
- [ ] Connect to same Trino from local dwe_superset (via Superset DB connection)
