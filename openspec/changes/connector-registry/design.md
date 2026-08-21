# Design: Connector Registry

## Data model

### connectors.json schema

```json
{
  "<connector_name>": {
    "type": "airflow_operator | pypi_package | trino_connector | dbt_package",
    "package": "<pip install name>",
    "pypi_url": "<optional>",
    "source_system": "<SIMS | Arbor | SchoolMIS | ...>",
    "direction": "ingest | egress | bidirectional",
    "target_adapter": "<dwe_iceberg | dwe_airflow | ...>",
    "description": "<human-readable>",
    "docs_url": "<optional>"
  }
}
```

### Example connectors.json

```json
{
  "sims_connector": {
    "type": "airflow_operator",
    "package": "dwe-sims-connector",
    "source_system": "SIMS",
    "direction": "ingest",
    "target_adapter": "dwe_iceberg",
    "description": "Brings student, attendance, and assessment data from SIMS into DWE-Iceberg"
  },
  "arbor_connector": {
    "type": "airflow_operator",
    "package": "dwe-arbor-connector",
    "source_system": "Arbor",
    "direction": "ingest",
    "target_adapter": "dwe_iceberg",
    "description": "Ingests data from Arbor MIS into DWE-Iceberg"
  }
}
```

## connector_registry.py module

```python
def load_connector_registry() -> dict[str, ConnectorEntry]:
    """Read dwe/connectors.json. Pure, fast, no network."""

def get_connector(name: str) -> ConnectorEntry:
    """Single connector lookup. Raises KeyError if not found."""

def get_connectors_for_adapter(adapter_name: str) -> list[ConnectorEntry]:
    """All connectors that target the given adapter."""
```

## CLI command: dwe list-connectors

```
$ dwe list-connectors

┌─────────────────────────────────────────────────────────────────────┐
│                        DWE Connector Catalog                         │
├──────────────────┬──────────────────┬─────────┬──────────────┬──────┤
│ Connector        │ Source System    │ Type    │ Target       │ Dir  │
├──────────────────┼──────────────────┼─────────┼──────────────┼──────┤
│ sims_connector   │ SIMS             │ airflow │ dwe_iceberg  │ in   │
│ arbor_connector  │ Arbor            │ airflow │ dwe_iceberg  │ in   │
└──────────────────┴──────────────────┴─────────┴──────────────┴──────┘

Install: pip install <package-name> into your dwe_airflow environment
```

## KG node type: Connector

Extend the Deploy API (`dwe_falkordb`'s FastAPI) with two new endpoints:

```
POST /connectors
  Body: { name, type, source_system, direction, target_adapter, org, env }
  Creates or upserts a Connector node in FalkorDB
  
GET /connectors
  Returns: list of registered Connector nodes
  
Relationship: Connector -[INSTALLED_IN]-> Adapter
```

FalkorDB schema extension:
```cypher
CREATE (:Connector {
  name: string,
  type: string,
  source_system: string,
  direction: string,
  target_adapter: string,
  org: string,
  env: string,
  installed_at: timestamp
})

MATCH (c:Connector), (a:Adapter)
WHERE c.target_adapter = a.name AND c.env = a.env
CREATE (c)-[:INSTALLED_IN]->(a)
```

## What connector KG registration does NOT do (yet)

- No pre-flight dependency check based on connectors
- No `dwe register-connector` CLI command
- No enforcement that a connector is installed before creating an Airflow DAG asset
- Registration is informational only

These are deferred to a future change when connector lifecycle management is designed.
