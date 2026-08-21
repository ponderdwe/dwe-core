### Requirement: dwe_iceberg is a complete DWE adapter
`dwe_iceberg` SHALL be a complete Copier-based DWE adapter with `copier.yml` (including `_dwe_hub`), `docker-compose.yml`, Pulumi IaC, and CI templates following the same pattern as `dwe_cube`.

#### Scenario: dwe_iceberg registered in adapters.json
- **WHEN** `dwe list-adapters` is called
- **THEN** `dwe_iceberg` appears in the catalog with metadata fetched from its copier.yml

### Requirement: dwe_iceberg ships Trino, Nessie, and MinIO/S3
The `docker-compose.yml` SHALL include Trino (port 8080), Nessie (port 19120), and MinIO (local dev only). Production uses S3 in place of MinIO.

#### Scenario: All services start on docker compose up
- **WHEN** `docker compose up` is run in the dwe_iceberg repo
- **THEN** Trino is reachable at localhost:8080, Nessie at localhost:19120, MinIO at localhost:9000

#### Scenario: Iceberg table created via Trino
- **WHEN** connected to Trino CLI and running `CREATE TABLE iceberg.test.students ...`
- **THEN** the table is created successfully and data can be inserted and queried

### Requirement: Nessie is used as the Iceberg catalog (not AWS Glue)
The adapter SHALL configure Trino to use Nessie as the Iceberg catalog. AWS Glue SHALL NOT be used, to ensure cloud-agnostic deployment.

#### Scenario: Trino catalog config points to Nessie
- **WHEN** reviewing `config/trino/catalog/iceberg.properties`
- **THEN** it configures `iceberg.catalog.type=nessie` with Nessie endpoint URL

### Requirement: dwe_iceberg has no depends_on
The adapter SHALL declare no `depends_on` entries — it is the foundational layer.

#### Scenario: No dependency pre-flight for dwe_iceberg
- **WHEN** `dwe create-service dwe_iceberg --kg-api-host ...` is called
- **THEN** no dependency check is performed (empty depends_on list)

### Requirement: Trino and Nessie registered as KG Services after pulumi up
After a successful `pulumi up`, the static Pulumi hydration block SHALL call `PATCH /adapters/dwe_iceberg/{env}` with Trino and Nessie endpoints as Service nodes.

#### Scenario: KG shows Trino service after deployment
- **WHEN** `pulumi up` succeeds and `KG_API_HOST` is present
- **THEN** `GET /adapters/dwe_iceberg/prod` returns a node with services: [trino, nessie]

### Requirement: dwe create-service dwe_iceberg works end-to-end
Running `dwe create-service dwe_iceberg` SHALL clone the target repo, hydrate it with the dwe_iceberg template, create branches, and push — following the same flow as dwe_cube.

#### Scenario: create-service produces correct branch structure
- **WHEN** `dwe create-service dwe_iceberg --git-repo ... --project-name test-school --environments dev,main`
- **THEN** `initial-commit`, `dev`, and `main` branches are pushed to the target repo
