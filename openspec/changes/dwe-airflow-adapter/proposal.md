# Proposal: dwe_airflow Adapter

## Problem

Schools need a managed workflow orchestration layer to run data pipelines — specifically Connectors that move data from school systems (SIS, MIS) into DWE-Iceberg. Without a deployed Airflow, Connectors have no runtime environment.

## Solution

Build `dwe_airflow` — a DWE adapter that deploys Apache Airflow into a school's own cloud VPC. Airflow is the runtime for DWE Connectors: schools install connector packages into their Airflow environment and upload DAGs (as Assets to dwe-hub) that use those connectors to ingest data.

Components:
- **Airflow webserver** (port 8080) — DAG monitoring UI
- **Airflow scheduler** — triggers DAG runs on schedule
- **Postgres** — Airflow metadata database
- **Redis** — optional, for CeleryExecutor (schools start with LocalExecutor)

LocalExecutor by default (appropriate for most school-scale workloads). CeleryExecutor available via copier question for larger MATs with heavy parallel pipeline loads.

## Goals

- Deployment target for Connectors: schools install connector packages into this adapter's environment
- DAGs as Assets: schools upload DAGs to dwe-hub, import them into their Airflow instance
- Optional dep on dwe_iceberg: KG warns if Iceberg not deployed (connectors need somewhere to write), but does not block
- Local dev: `docker compose up` gives working Airflow in minutes

## Non-goals

- Does not ship any Connectors — connectors are separate packages installed by schools
- Does not provision CeleryExecutor workers on separate EC2 instances in this iteration
- Does not integrate with Airflow's managed cloud offerings (MWAA, Cloud Composer)
