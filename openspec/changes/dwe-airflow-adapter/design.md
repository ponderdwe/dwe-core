# Design: dwe_airflow Adapter

## Component architecture

```
┌─────────────────────────────────────────────────────┐
│                  EC2 Instance (prod)                 │
│                  Docker Compose                      │
│                                                      │
│  ┌─────────────────┐    ┌──────────────────────┐    │
│  │ Airflow          │    │ Airflow Scheduler    │    │
│  │ Webserver        │    │                      │    │
│  │ port 8080        │    │ Reads DAGs from      │    │
│  └─────────────────┘    │ /opt/airflow/dags    │    │
│           │              └──────────────────────┘    │
│  ┌─────────────────┐              │                  │
│  │   Postgres       │◀────────────┘                  │
│  │ (metadata DB)    │  (task state, DAG history)     │
│  └─────────────────┘                                 │
└─────────────────────────────────────────────────────┘
         │ ALB (HTTPS)
         ▼
   Schools access Airflow UI
   to monitor and trigger DAGs
```

## Connector runtime model

```
School installs connector:
  pip install dwe-sims-connector  (into Airflow's Python environment)

School uploads a DAG asset from dwe-hub:
  The DAG imports from dwe_sims_connector:
    from dwe_sims_connector import SIMSToIcebergOperator
    
  The DAG writes to dwe_iceberg via Trino connection:
    conn_id = "trino_default"  (configured in Airflow connections)
```

## Repo structure (dwe_airflow)

```
dwe_airflow/
├── copier.yml
├── docker-compose.yml            # webserver + scheduler + postgres (dev)
├── docker-compose.prod.yml       # prod (no dev ports)
├── .env.example
├── justfile
├── requirements.txt              # extra pip packages for Airflow
├── pulumi/
│   ├── __main__.py
│   ├── Pulumi.yaml.jinja
│   └── requirements.txt
└── ci-templates/
    ├── github.yaml
    └── gitlab.yaml
```

## _dwe_hub metadata

```yaml
_dwe_hub:
  hub_name: airflow
  display_name: "DWE Airflow"
  description: "Workflow orchestration — runs Connectors to move data into DWE-Iceberg"
  depends_on:
    - adapter: dwe_iceberg
      required: false
      inherited_secrets: []

  required_secrets:
    - key: AWS_ACCESS_KEY_ID
      destination: [ci, secrets_manager]
    - key: AWS_SECRET_ACCESS_KEY
      destination: [ci, secrets_manager]
    - key: PULUMI_ACCESS_TOKEN
      destination: ci
    - key: AIRFLOW__CORE__FERNET_KEY
      destination: secrets_manager
    - key: AIRFLOW_ADMIN_PASSWORD
      destination: secrets_manager

  optional_secrets:
    - key: AWS_REGION
      destination: ci
    - key: AIRFLOW_EXECUTOR
      destination: secrets_manager

  services:
    - name: airflow
      type: service
      kg:
        trigger_secret: ALB_DNS
        properties:
          endpoint: ALB_DNS

  kg_pulumi_outputs:
    airflow_endpoint: alb_dns_name
```

## Executor choice

Controlled by `AIRFLOW_EXECUTOR` secret (default: `LocalExecutor`).

| Executor | Use case | EC2 size |
|---|---|---|
| LocalExecutor | Most schools (<20 concurrent tasks) | t3.small |
| CeleryExecutor | Large MATs with heavy parallel pipelines | t3.medium + Redis |

CeleryExecutor adds Redis to docker-compose. Redis is already in the template, activated by the executor choice at runtime.

## Local testing

```bash
cd dwe_airflow
docker compose up

# Airflow UI: http://localhost:8080 (admin/admin)

# Test a connector DAG locally
pip install dwe-sims-connector
# Place test DAG in dags/ directory
# Trigger it from the UI or CLI:
docker exec airflow-scheduler airflow dags trigger test_sims_ingest

# Test dwe-core hydration
dwe create-service dwe_airflow \
  --adapters-path /path/to/dwe_airflow \
  --git-repo https://github.com/test-org/dummy-repo \
  --project-name test-school \
  --kg-api-host http://localhost:8000 \
  --kg-api-token dev-token
# Expect: optional dep warning for dwe_iceberg if not in KG, then proceeds
```
