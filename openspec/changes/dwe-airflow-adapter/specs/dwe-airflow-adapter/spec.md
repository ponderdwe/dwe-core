### Requirement: dwe_airflow is a complete DWE adapter
`dwe_airflow` SHALL be a complete Copier-based DWE adapter with `copier.yml` (including `_dwe_hub`), `docker-compose.yml`, Pulumi IaC, and CI templates.

#### Scenario: dwe_airflow registered in adapters.json
- **WHEN** `dwe list-adapters` is called
- **THEN** `dwe_airflow` appears in the catalog

### Requirement: dwe_airflow ships Airflow webserver, scheduler, and Postgres
The `docker-compose.yml` SHALL include airflow-webserver (port 8080), airflow-scheduler, and postgres.

#### Scenario: All services start on docker compose up
- **WHEN** `docker compose up` is run in the dwe_airflow repo
- **THEN** Airflow UI is reachable at localhost:8080 with admin/admin credentials

#### Scenario: DAG visible in Airflow UI
- **WHEN** a DAG file is placed in the `dags/` directory
- **THEN** the DAG appears in the Airflow UI within the scheduler's refresh interval

### Requirement: dwe_airflow declares optional depends_on dwe_iceberg
The adapter SHALL declare `depends_on: [{adapter: dwe_iceberg, required: false}]`.

#### Scenario: Optional dependency warns when dwe_iceberg missing
- **WHEN** `dwe create-service dwe_airflow --kg-api-host ...` and dwe_iceberg is not in the graph
- **THEN** dwe-core prints a warning and prompts for confirmation before proceeding

#### Scenario: create-service proceeds when user confirms without dwe_iceberg
- **WHEN** user confirms proceeding without dwe_iceberg
- **THEN** dwe_airflow is created successfully — the dep is optional

### Requirement: Executor configurable via secret
The `AIRFLOW_EXECUTOR` secret SHALL control which executor is used (LocalExecutor default, CeleryExecutor optional).

#### Scenario: LocalExecutor is default
- **WHEN** `AIRFLOW_EXECUTOR` is not set in secrets
- **THEN** Airflow starts with LocalExecutor

#### Scenario: CeleryExecutor enables Redis
- **WHEN** `AIRFLOW_EXECUTOR=CeleryExecutor` is set
- **THEN** the Docker Compose includes a Redis service and Airflow uses Celery

### Requirement: Airflow endpoint registered as KG Service after pulumi up
After successful `pulumi up`, the Airflow webserver ALB endpoint SHALL be registered as a Service node in the KG.

#### Scenario: KG shows Airflow service after deployment
- **WHEN** `pulumi up` succeeds and `KG_API_HOST` is present
- **THEN** `GET /adapters/dwe_airflow/{env}` returns a node with services: [airflow]
