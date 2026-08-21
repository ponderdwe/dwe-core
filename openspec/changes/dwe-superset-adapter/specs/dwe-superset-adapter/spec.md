### Requirement: dwe_superset is a complete DWE adapter
The `dwe_superset` repo SHALL be completed with `copier.yml` (including `_dwe_hub`), `docker-compose.yml`, `docker-compose.prod.yml`, Pulumi IaC, CI templates, and a justfile — on par with `dwe_cube`.

#### Scenario: dwe_superset registered in adapters.json
- **WHEN** `dwe list-adapters` is called
- **THEN** `dwe_superset` appears in the catalog with full metadata

### Requirement: dwe_superset ships Superset, Postgres, and Redis
The `docker-compose.yml` SHALL include Superset (port 8088), Postgres (Superset metadata), and Redis (caching and async results).

#### Scenario: All services start on docker compose up
- **WHEN** `docker compose up` is run in dwe_superset
- **THEN** Superset UI is reachable at localhost:8088

#### Scenario: Superset connects to local Trino
- **WHEN** a Trino database connection is added in Superset (URI: trino://localhost:8080/iceberg)
- **THEN** Superset can browse Iceberg tables and run SQL queries

### Requirement: dwe_superset declares optional depends_on dwe_cube and dwe_iceberg
The adapter SHALL declare both as optional dependencies.

#### Scenario: Optional deps produce warnings not errors
- **WHEN** `dwe create-service dwe_superset --kg-api-host ...` and neither dwe_cube nor dwe_iceberg are in the graph
- **THEN** dwe-core warns about both optional deps, prompts for confirmation, and proceeds if confirmed

### Requirement: Superset endpoint registered as KG Service after pulumi up
After successful `pulumi up`, the Superset ALB endpoint SHALL be registered as a Service node in the KG.

#### Scenario: KG shows Superset service after deployment
- **WHEN** `pulumi up` succeeds and `KG_API_HOST` is present
- **THEN** `GET /adapters/dwe_superset/{env}` returns a node with services: [superset]

### Requirement: dwe create-service dwe_superset works end-to-end
Running `dwe create-service dwe_superset` SHALL follow the same 8-step flow as `dwe_cube`.

#### Scenario: create-service produces correct branch structure
- **WHEN** `dwe create-service dwe_superset --git-repo ... --project-name test-school`
- **THEN** `initial-commit`, `development`, and `main` branches are pushed to the target repo with hydrated content

### Requirement: dwe-hub Superset plugin can publish to a deployed dwe_superset instance
A school running `dwe_superset` locally SHALL be able to publish dashboards via the `dwe_hub_superset_plugin` to a local dwe-hub instance for testing.

#### Scenario: Dashboard published from local Superset to local Hub
- **WHEN** local dwe_superset is running at localhost:8088 and local dwe-hub at localhost:5050
- **THEN** the Superset plugin can publish a test dashboard and it appears in the hub gallery
