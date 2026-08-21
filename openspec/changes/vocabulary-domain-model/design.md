# Design: DWE Vocabulary

## Canonical definitions

### Adapter
A deployable DWE infrastructure component. Managed by dwe-core, deployed via Copier + Pulumi into each organisation's own cloud VPC.

An adapter is always:
- A Git repository with a `copier.yml` (`_dwe_hub` section)
- A real Docker Compose application (runs locally with `docker compose up`)
- A Pulumi IaC stack (provisions cloud resources)
- Registered in `dwe/adapters.json`

An adapter is NOT: a library, a package, or anything without its own infrastructure lifecycle.

Known adapters: `dwe_iceberg`, `dwe_cube`, `dwe_superset`, `dwe_airflow`, `dwe_falkordb`, `dwe_dbt_kg`

### Connector
A data movement package. Bridges external school systems to DWE-Iceberg, or pushes processed data back to those systems.

A connector is always:
- A distributable package: PyPI package, Airflow operator, Trino connector library, or dbt package
- Installed INTO an existing adapter (not deployed independently)
- Registered in `dwe/connectors.json`

A connector is NOT: an adapter. It has no Copier template, no Pulumi stack, no independent cloud lifecycle.

Examples: `dwe-sims-connector` (PyPI, Airflow operator), `dwe-arbor-connector` (PyPI, Airflow operator)

Direction: `ingest` (external → DWE-Iceberg), `egress` (DWE → external), `bidirectional`

### Asset
School-created content uploaded to dwe-hub for sharing or backup.

An asset is always:
- Stored in dwe-hub WITHOUT real school data — only logic and metadata
- Either private (org-only backup) or public (shared across MATs and Charter Schools)
- A structured file (Superset ZIP, Cube YAML, Airflow DAG, dbt project)

An asset is NOT: infrastructure, a connector, or live data.

Examples: Superset dashboards, Cube semantic models, Airflow DAGs, dbt projects

## Privacy boundary

```
dwe-hub (knows)                    dwe-hub (never knows)
────────────────────────────────   ─────────────────────────────
Deployment configs                 Live school data
Asset ZIPs (no real data)          Database credentials of org
Org metadata (name, slug)          Direct connections to org VPC
Which adapters are deployed        Contents of S3 buckets
```

## Term usage rules

| Use this term | When referring to |
|---|---|
| Adapter | A DWE infra component with its own Pulumi stack |
| Connector | A package installed into an adapter for data movement |
| Asset | A dashboard, semantic model, DAG, or dbt project in dwe-hub |
| Service | An endpoint within a deployed adapter (Trino, Nessie, Cube API) |

Never use: "component", "plugin" (except for the Superset browser plugin), "module" as synonyms for these terms.
