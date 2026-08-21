# Proposal: Connector Registry

## Problem

Connectors (data movement packages between school systems and DWE-Iceberg) exist conceptually but have no representation in the DWE tooling. Schools cannot discover available connectors, dwe-core has no awareness of them, and the KG cannot track which connectors an org has installed. The vocabulary "connector" is undefined in code.

## Solution

Add a Connector registry to dwe-core alongside the existing Adapter registry:

1. **`dwe/connectors.json`** — static registry of known connectors (PyPI package name, type, source system, direction, target adapter)
2. **`dwe/connector_registry.py`** — `load_connector_registry()`, `get_connector()`, `get_connectors_for_adapter()`
3. **`dwe list-connectors`** — new CLI command displaying the connector catalog in a Rich table
4. **New KG node type: Connector** — extends the Deploy API with `/connectors` endpoints (register, list)

Connectors are explicitly NOT adapters: they are packages installed into existing adapters, not Copier templates with Pulumi stacks. The registry records them as packages with metadata.

## Goals

- Schools can discover available connectors with `dwe list-connectors`
- dwe-core knows which connectors target which adapter (useful for future dependency checks)
- The KG can record which connectors an org has installed (informational, no pre-flight enforcement yet)
- Clear separation: connector vs adapter is enforced at the data model level

## Non-goals

- Does not install connectors — installation is `pip install <package>` inside the target adapter's environment
- Does not enforce connector presence as a KG pre-flight condition (deferred)
- Does not manage connector versions
