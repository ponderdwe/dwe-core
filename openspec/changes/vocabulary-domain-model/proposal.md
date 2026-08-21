# Proposal: DWE Vocabulary — Adapter, Connector, Asset

## Problem

The DWE ecosystem has grown to include infrastructure components, data movement packages, and school-created content — but these concepts have no canonical definitions. Specs, READMEs, and UI copy use "adapter", "connector", and "asset" inconsistently, making it hard to reason about what each system does and who owns what.

## Solution

Establish a locked vocabulary with three terms that all specs, documentation, and interfaces must use consistently. Write a canonical spec that defines each term, gives examples, and explicitly says what each is NOT.

## Terms

**Adapter** — A deployable DWE infrastructure component. Deployed via `dwe create-service` + Pulumi into each organisation's own cloud VPC. Examples: `dwe_iceberg`, `dwe_cube`, `dwe_superset`, `dwe_airflow`, `dwe_falkordb`, `dwe_dbt_kg`. Each adapter is a Copier template + a real Docker Compose application + Pulumi IaC. Schools own the deployed infrastructure. dwe-hub never connects to org data directly.

**Connector** — A data movement package that bridges external school systems (SIS, MIS) to DWE-Iceberg, or pushes processed data back. A connector is NOT deployed DWE infrastructure — it is a library or operator installed into an existing adapter: a PyPI package, an Airflow operator, a Trino connector library, or a dbt package. Connectors run inside adapters (e.g. a DAG using `dwe-sims-connector` runs inside `dwe_airflow`).

**Asset** — School-created content uploaded to dwe-hub for sharing or backup. Examples: Superset dashboards, Cube semantic models, Airflow DAGs, dbt projects. Assets are stored in dwe-hub WITHOUT real school data — only logic and metadata. An asset can be private (org-only) or public (shared across MATs and Charter Schools).

## Privacy boundary

dwe-hub manages deployment metadata and assets. It must NEVER hold a connection to actual organisation data. Each org's deployment lives in their own VPC (AWS, Azure, or future cloud providers). dwe-hub stores only: deployment configs, asset ZIPs (no real data), and org metadata.

## Goals

- One canonical source of truth for vocabulary across all DWE specs
- Every new spec references `openspec/specs/dwe-vocabulary/spec.md`
- No ambiguous use of "component", "service", "package" as synonyms for these terms

## Non-goals

- Does not change any existing code
- Does not restructure the adapter registry
- Does not define internal implementation details of any adapter
