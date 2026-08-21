# Tasks: connector-registry

## Phase 1: connectors.json and registry module

- [ ] Create `dwe/connectors.json` with schema definition and initial entries (sims_connector, arbor_connector as placeholders)
- [ ] Create `dwe/connector_registry.py` with:
  - `load_connector_registry() -> dict`
  - `get_connector(name: str) -> dict`
  - `get_connectors_for_adapter(adapter_name: str) -> list`
- [ ] Unit tests for all three functions

## Phase 2: CLI command

- [ ] Add `list-connectors` command to `dwe/cli.py`
- [ ] Display Rich table: name, source_system, type, target_adapter, direction
- [ ] Add install hint at the bottom: "Install: pip install <package-name> into your dwe_airflow environment"
- [ ] Test: `dwe list-connectors` works

## Phase 3: KG extension (in dwe_falkordb repo)

- [ ] Add `POST /connectors` endpoint to `deploy-api/main.py` in `dwe_falkordb`
- [ ] Add `GET /connectors` endpoint
- [ ] Add Connector node schema to FalkorDB creation logic
- [ ] Add `INSTALLED_IN` relationship between Connector and Adapter
- [ ] Test: `POST /connectors` with dummy data → verify node in FalkorDB

## Phase 4: dwe-core DeployAPIClient update

- [ ] Add `register_connector(connector: dict) -> None` to `KGClientProtocol`
- [ ] Implement in `DeployAPIClient` (calls `POST /connectors`)
- [ ] Implement as no-op in `NoOpKGClient`
