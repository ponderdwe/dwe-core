### Requirement: Dashboard import returns adapter requirements (future)
The `GET /api/v1/assets/{uuid}/requirements` endpoint SHALL return the list of adapters required by the asset and whether each is deployed in the requesting org's environment. This endpoint is specced here but implementation is deferred.

#### Scenario: Requirements returned with deployment status
- **WHEN** `GET /api/v1/assets/{uuid}/requirements?org_id={org_id}&env=production` is called
- **THEN** the response includes each required adapter and `{"deployed": true/false}`

#### Scenario: Missing adapter flagged as warning or error
- **WHEN** the response includes `{"adapter": "dwe_cube", "required": false, "deployed": false}`
- **THEN** the UI shows a warning, not an error — import can proceed

#### Scenario: Missing required adapter blocks import
- **WHEN** the response includes `{"adapter": "dwe_superset", "required": true, "deployed": false}`
- **THEN** the UI shows an error and the import button is disabled

### Requirement: Dependency check queries the org's KG (future)
When checking adapter deployment status, dwe-hub SHALL query the org's `dwe_falkordb` Deploy API using the org's stored KG credentials.

#### Scenario: KG not configured for org returns unknown status
- **WHEN** the org does not have a `dwe_falkordb` deployment recorded in dwe-hub
- **THEN** the dependency check returns `{"status": "unknown"}` for all adapters and does not block the import

### Requirement: AdapterType enum covers all current adapters
`DeploymentConfig.adapter` SHALL accept all current adapter types: SUPERSET, CUBE, DBT_KG, ICEBERG, AIRFLOW, FALKORDB, CONNECTOR.

#### Scenario: New adapter types accepted in DeploymentConfig
- **WHEN** `POST /api/v1/organizations/{slug}/deploy-configs` is called with `adapter: "ICEBERG"`
- **THEN** the deployment config is created without validation error
