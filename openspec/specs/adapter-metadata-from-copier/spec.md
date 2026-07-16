### Requirement: adapters.json contains only url and type
`dwe/adapters.json` SHALL contain only `url` and `type` fields per adapter entry. No display metadata, secrets, or service definitions SHALL be stored there.

#### Scenario: Registry file has minimal shape
- **WHEN** `adapters.json` is loaded
- **THEN** each entry contains only `url` (string) and `type` (string)

### Requirement: Adapter metadata is sourced from copier.yml _dwe_hub
Each adapter repo's `copier.yml` SHALL contain a `_dwe_hub` section that is the sole source of truth for `hub_name`, `display_name`, `description`, `icon`, `git_providers`, `cloud_providers`, `services`, `required_secrets`, and `optional_secrets`.

#### Scenario: get_adapter_catalog returns full metadata from copier.yml
- **WHEN** `get_adapter_catalog()` is called for an adapter whose `adapters.json` entry has only `url` and `type`
- **THEN** the returned catalog entry contains populated `hub_name`, `display_name`, `description`, `icon`, `services`, `required_secrets`, and `optional_secrets` sourced from the adapter repo's `copier.yml` `_dwe_hub` section

#### Scenario: copier.yml fetch failure degrades gracefully
- **WHEN** the adapter repo's `copier.yml` cannot be fetched (network error, timeout)
- **THEN** the adapter still appears in the catalog with its `url` and `type`, and metadata fields default to empty strings or empty lists

### Requirement: _dwe_hub includes description field
Each adapter repo's `copier.yml` `_dwe_hub` section SHALL include a `description` field describing the adapter's purpose.

#### Scenario: description is populated in catalog
- **WHEN** `get_adapter_catalog()` is called
- **THEN** each adapter entry has a non-empty `description` sourced from `_dwe_hub.description` in its copier.yml
