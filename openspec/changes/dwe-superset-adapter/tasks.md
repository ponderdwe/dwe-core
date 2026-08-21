# Tasks: dwe-superset-adapter

## Phase 1: Adapter repo completion

- [ ] Add `copier.yml` to `dwe_superset` repo with Copier questions and `_dwe_hub` metadata
- [ ] Add `docker-compose.yml` with superset + postgres + redis
- [ ] Add `docker-compose.prod.yml`
- [ ] Add `.env.example`
- [ ] Add `justfile` with `just up`, `just init-db`, `just deploy-prod`
- [ ] Add `blueprint/superset_config.py.jinja` (Flask app secret, Redis cache config, etc.)
- [ ] Add `blueprint/instance-setup.sh` (EC2 user-data script)

## Phase 2: Superset configuration

- [ ] Configure Redis as cache backend and async results backend
- [ ] Set up Superset admin user creation on first boot (from env vars)
- [ ] Configure CSRF and session settings
- [ ] Test locally: `docker compose up` → Superset UI at localhost:8088

## Phase 3: Trino connection test

- [ ] While dwe_iceberg is also running locally, add Trino connection in Superset
- [ ] Create a test dataset from an Iceberg table
- [ ] Create a test chart → verify end-to-end query to Iceberg

## Phase 4: Pulumi IaC

- [ ] Add `pulumi/__main__.py` with EC2 + ALB + ACM + Route53 + Secrets Manager
- [ ] Add `pulumi/Pulumi.yaml.jinja`
- [ ] Add `pulumi/requirements.txt`
- [ ] Include static KG hydration block

## Phase 5: CI templates

- [ ] Add `ci-templates/github.yaml`
- [ ] Add `ci-templates/gitlab.yaml`

## Phase 6: dwe-core registration

- [ ] Add `dwe_superset` entry to `dwe/adapters.json`
- [ ] Test: `dwe list-adapters` shows dwe_superset
- [ ] Test: `dwe create-service dwe_superset --adapters-path /local/dwe_superset --project-name test-school`

## Phase 7: Hub plugin integration test

- [ ] Run dwe-hub locally (`docker compose up` in dwe-hub)
- [ ] Run dwe_superset locally
- [ ] Install dwe_hub_superset_plugin in local Superset
- [ ] Publish a test dashboard from Superset to local Hub
- [ ] Verify dashboard appears in Hub gallery
- [ ] Import dashboard back into a fresh Superset → verify charts render
