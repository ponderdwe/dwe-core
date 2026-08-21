# Proposal: dwe_superset Adapter

## Problem

`dwe_superset` exists as a skeleton repo (only LICENSE + README.md). Schools have no way to deploy Superset as a DWE adapter. Without a deployed Superset, the dwe-hub Superset plugin (dashboard publish/import) has no target instance to connect to.

## Solution

Complete `dwe_superset` into a full DWE adapter on par with `dwe_cube` and `dwe_falkordb`. It deploys Apache Superset + supporting services into a school's own cloud VPC.

Components:
- **Apache Superset** (port 8088) — BI dashboards and data exploration
- **Postgres** — Superset metadata (charts, datasets, dashboard definitions)
- **Redis** — query result caching and async results backend

The adapter closes the dwe-hub loop: schools deploy `dwe_superset`, connect it to `dwe_cube` (Semantic Layer) or `dwe_iceberg` (direct Trino queries), build dashboards, and publish them as Assets to dwe-hub.

## Goals

- Full adapter: copier.yml + docker-compose.yml + Pulumi IaC + CI templates + justfile
- Integration with dwe-hub Superset plugin: the plugin publishes/imports dashboards to a deployed `dwe_superset` instance
- Optional deps: `dwe_cube` (semantic layer queries) and `dwe_iceberg` (direct Trino access)
- Local dev: `docker compose up` gives working Superset in minutes
- KG registration: Superset endpoint registered as a Service after `pulumi up`

## Non-goals

- Does not implement the Superset plugin (that is `dwe_hub_superset_plugin`)
- Does not configure database connections automatically — schools connect Superset to their Trino/Cube endpoints post-deploy
- Does not handle Row-Level Security configuration
