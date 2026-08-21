### Requirement: Adapter is the canonical term for a deployable DWE infrastructure component
All specs, READMEs, CLI output, and UI copy SHALL use "Adapter" when referring to a DWE infrastructure component deployed via dwe-core and Pulumi.

#### Scenario: Adapter referenced in CLI output
- **WHEN** `dwe list-adapters` is run
- **THEN** the output header reads "DWE Adapter Catalog", not "component catalog" or "service catalog"

#### Scenario: Adapter referenced in openspec specs
- **WHEN** a new spec describes a deployable DWE infrastructure component
- **THEN** it uses the word "adapter" and references this spec as the vocabulary source

### Requirement: Connector is the canonical term for a data movement package
All specs, READMEs, and UI copy SHALL use "Connector" when referring to a package that moves data between external school systems and DWE-Iceberg.

#### Scenario: Connector distinguished from Adapter in documentation
- **WHEN** a README or spec describes a PyPI package that ingests SIMS data
- **THEN** it calls the package a "connector", not an "adapter" or "plugin"

### Requirement: Asset is the canonical term for school-created content in dwe-hub
All specs, READMEs, and dwe-hub UI copy SHALL use "Asset" when referring to dashboards, semantic models, DAGs, or dbt projects uploaded to dwe-hub.

#### Scenario: Asset referenced in dwe-hub UI
- **WHEN** a school publishes a dashboard from Superset to dwe-hub
- **THEN** the UI confirmation reads "Asset published" not "Dashboard uploaded"

### Requirement: Assets contain no real school data
An asset stored in dwe-hub SHALL contain only logic and metadata — no actual student or staff records.

#### Scenario: Dashboard ZIP contains no real data
- **WHEN** a school publishes a Superset dashboard
- **THEN** the ZIP contains chart definitions, dataset SQL queries, and layout — but no query result data

### Requirement: dwe-hub never connects to org data infrastructure
dwe-hub SHALL NOT hold database credentials, direct connections, or API keys that provide access to a school's live data environment.

#### Scenario: Hydration metadata stored without data access
- **WHEN** dwe-hub records that org "acme" has deployed dwe_superset
- **THEN** dwe-hub stores only: git_repo_url, adapter_name, last_hydrated_at — not Superset's DB password or a live connection to Superset

### Requirement: Privacy boundary enforced in secret handling
Org deployment secrets (AWS credentials, git tokens) SHALL be fetched per-operation from AWS Secrets Manager and SHALL NOT be cached in dwe-hub's database or memory beyond the operation.

#### Scenario: Hydration secret not persisted
- **WHEN** dwe-hub fetches org secrets to trigger hydration
- **THEN** the secret dict is used once for the `hydrate_repo()` call and not stored in the database
