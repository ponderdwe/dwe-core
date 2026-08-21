### Requirement: connectors.json is the static connector registry
`dwe/connectors.json` SHALL exist alongside `dwe/adapters.json` and contain the canonical list of known DWE connectors. Each entry SHALL include: type, package, source_system, direction, target_adapter, description.

#### Scenario: connectors.json is parseable
- **WHEN** `dwe/connectors.json` is read
- **THEN** it parses as valid JSON with the required fields per entry

### Requirement: load_connector_registry returns all connectors
`load_connector_registry()` SHALL read `dwe/connectors.json` and return a dict of all connectors. It SHALL NOT make network calls.

#### Scenario: load_connector_registry is fast and pure
- **WHEN** `load_connector_registry()` is called
- **THEN** it returns within 10ms with no network access

### Requirement: get_connectors_for_adapter returns matching connectors
`get_connectors_for_adapter("dwe_iceberg")` SHALL return all connectors whose `target_adapter` is `dwe_iceberg`.

#### Scenario: Connector filtered by target adapter
- **WHEN** `get_connectors_for_adapter("dwe_iceberg")` is called
- **THEN** it returns only connectors that target dwe_iceberg (not connectors for other adapters)

### Requirement: dwe list-connectors displays the connector catalog
The `list-connectors` CLI command SHALL display all connectors in a Rich table with columns: name, source_system, type, target adapter, direction.

#### Scenario: list-connectors shows all connectors
- **WHEN** `dwe list-connectors` is called
- **THEN** a formatted table shows all entries from connectors.json

### Requirement: Connector type is distinct from Adapter type in all interfaces
`list-connectors` and `list-adapters` SHALL be separate commands. A connector SHALL never appear in `list-adapters` output and vice versa.

#### Scenario: Connectors not mixed with adapters
- **WHEN** `dwe list-adapters` is called
- **THEN** no connector entries appear in the output

### Requirement: Deploy API adds /connectors endpoints
The `dwe_falkordb` Deploy Management FastAPI SHALL expose:
- `POST /connectors` — register a Connector node in FalkorDB
- `GET /connectors` — list all registered Connector nodes

#### Scenario: POST /connectors creates a Connector node
- **WHEN** `POST /connectors` is called with valid connector metadata and bearer token
- **THEN** a Connector node is created in FalkorDB and HTTP 200 is returned

#### Scenario: GET /connectors lists installed connectors
- **WHEN** `GET /connectors` is called
- **THEN** all registered Connector nodes are returned as JSON
