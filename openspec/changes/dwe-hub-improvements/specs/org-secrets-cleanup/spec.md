### Requirement: Production secret resolution uses AWS Secrets Manager only
When `DWE_HUB_DEBUG` is not `true`, `get_org_secrets()` SHALL resolve org credentials from AWS Secrets Manager exclusively. The env var path SHALL NOT be attempted.

#### Scenario: Production ignores env var
- **WHEN** `DWE_HUB_DEBUG=false` and `SCHOOL_ACME_DEPLOY` env var is set
- **THEN** `get_org_secrets("acme")` does NOT read the env var; it queries Secrets Manager only

#### Scenario: Missing Secrets Manager entry raises clear error in production
- **WHEN** `DWE_HUB_DEBUG=false` and no Secrets Manager secret exists for the org
- **THEN** `SecretNotFoundError` is raised with a message identifying the expected Secrets Manager key

### Requirement: Local development retains env var fallback
When `DWE_HUB_DEBUG=true`, `get_org_secrets()` MAY check env vars before Secrets Manager, to support local development without AWS credentials.

#### Scenario: Local dev reads from env var
- **WHEN** `DWE_HUB_DEBUG=true` and `SCHOOL_ACME_DEPLOY={"key":"val"}` is set in .env
- **THEN** `get_org_secrets("acme")` returns the env var value without querying AWS

### Requirement: Org secrets are never logged
`get_org_secrets()` and its callers SHALL NOT log the secret dict or any of its values.

#### Scenario: Secret values not in logs
- **WHEN** `get_org_secrets()` is called in production
- **THEN** no log line contains AWS_ACCESS_KEY_ID, GIT_TOKEN, or any credential value
