# Tasks: dwe-airflow-adapter

## Phase 1: Adapter repo setup

- [ ] Create `github.com/ponderdwe/dwe_airflow` repo
- [ ] Add `copier.yml` with Copier questions and `_dwe_hub` metadata block (including `depends_on: dwe_iceberg`)
- [ ] Add `docker-compose.yml` with airflow-webserver + airflow-scheduler + postgres (+ redis)
- [ ] Add `docker-compose.prod.yml`
- [ ] Add `.env.example`
- [ ] Add `requirements.txt` for extra Airflow packages
- [ ] Add `justfile`

## Phase 2: Airflow configuration

- [ ] Configure Airflow to use LocalExecutor by default
- [ ] Configure CeleryExecutor path (via AIRFLOW_EXECUTOR env var, activates Redis in compose)
- [ ] Set up Fernet key, secret key handling
- [ ] Test locally: `docker compose up` → Airflow UI at localhost:8080

## Phase 3: Pulumi IaC

- [ ] Add `pulumi/__main__.py` with EC2 + ALB + Secrets Manager
- [ ] Add `pulumi/Pulumi.yaml.jinja`
- [ ] Add `pulumi/requirements.txt`
- [ ] Include static KG hydration block

## Phase 4: CI templates

- [ ] Add `ci-templates/github.yaml`
- [ ] Add `ci-templates/gitlab.yaml`

## Phase 5: dwe-core registration

- [ ] Add `dwe_airflow` entry to `dwe/adapters.json`
- [ ] Test: `dwe list-adapters` shows dwe_airflow
- [ ] Test: `dwe create-service dwe_airflow --adapters-path /local/dwe_airflow --project-name test-school`
- [ ] Test optional dep warning: run with --kg-api-host when dwe_iceberg not in graph

## Phase 6: Connector smoke test

- [ ] Install a test connector package in local Airflow environment
- [ ] Create a simple test DAG using the connector
- [ ] Verify DAG appears in Airflow UI and can be triggered manually
