# Proposal: dwe_iceberg Adapter

## Problem

DWE has no open data lake layer. Schools currently have no managed way to store and query structured data in an open format across cloud providers. Without a foundational storage layer, adapters like `dwe_cube` and `dwe_airflow` have nowhere to read from or write to.

## Solution

Build `dwe_iceberg` — a DWE adapter that deploys a production-ready Apache Iceberg data lake stack into a school's own cloud VPC. It consists of three components:

- **Trino** — distributed SQL query engine (port 8080). Schools connect BI tools and notebooks to Trino to query Iceberg tables.
- **Nessie** — open-source Iceberg catalog (port 19120). Git-like versioning for table metadata. Chosen over AWS Glue to avoid cloud lock-in (orgs may use AWS or Azure).
- **S3 / MinIO** — object storage for Parquet data files. MinIO for local dev, S3/Azure Blob for production.

The adapter follows the same pattern as `dwe_cube`: a Copier template + real Docker Compose app + Pulumi IaC + CI templates.

## Goals

- Foundational data layer: other adapters declare optional `depends_on: dwe_iceberg`
- Cloud-agnostic: Nessie works on AWS, Azure, and local (MinIO)
- Local dev: `docker compose up` gives a fully working Iceberg stack in minutes
- KG registration: Trino and Nessie endpoints registered as Services after `pulumi up`

## Non-goals

- Does not include connectors (data movement to/from school systems is a Connector concern)
- Does not include dbt transformations (that is `dwe_dbt_kg`)
- Does not provision Azure Blob Storage in this iteration (S3 and MinIO only)
