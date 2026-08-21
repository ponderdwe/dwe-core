# Design: dwe_superset Adapter

## Component architecture

```
┌─────────────────────────────────────────────────────┐
│                  EC2 Instance (prod)                 │
│                  Docker Compose                      │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              Apache Superset                  │   │
│  │              port 8088                        │   │
│  │                                               │   │
│  │  Connects to:                                 │   │
│  │  - dwe_cube (Cube SQL API / semantic layer)   │   │
│  │  - dwe_iceberg (Trino direct queries)         │   │
│  └──────────────────────────────────────────────┘   │
│         │                  │                         │
│  ┌──────────┐      ┌──────────────┐                 │
│  │ Postgres  │      │    Redis     │                 │
│  │ metadata  │      │  cache/async │                 │
│  └──────────┘      └──────────────┘                 │
└─────────────────────────────────────────────────────┘
         │ ALB (HTTPS)
         ▼
   Schools access Superset UI
   dwe-hub plugin publishes/imports dashboards here
```

## Repo structure (dwe_superset)

The repo at github.com/ponderdwe/dwe_superset currently has only LICENSE + README.md. This change adds all adapter files.

```
dwe_superset/
├── copier.yml
├── docker-compose.yml            # superset + postgres + redis (dev)
├── docker-compose.prod.yml       # prod (no exposed ports except via ALB)
├── .env.example
├── justfile                      # just up, just init-db, just deploy-prod
├── blueprint/
│   ├── superset_config.py.jinja  # Superset Python config (rendered)
│   └── instance-setup.sh         # EC2 user-data: pull secrets, start app
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
  hub_name: superset
  display_name: "DWE Superset"
  description: "Open-source BI — dashboards, charts, and data exploration"
  depends_on:
    - adapter: dwe_cube
      required: false
      inherited_secrets: []
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
    - key: SUPERSET_SECRET_KEY
      destination: secrets_manager
    - key: SUPERSET_ADMIN_USERNAME
      destination: secrets_manager
    - key: SUPERSET_ADMIN_PASSWORD
      destination: secrets_manager

  optional_secrets:
    - key: AWS_REGION
      destination: ci
    - key: INSTANCE_TYPE
      destination: ci
    - key: SUPERSET_ADMIN_EMAIL
      destination: secrets_manager

  services:
    - name: superset
      type: service
      description: "Apache Superset BI platform"
      kg:
        trigger_secret: ALB_DNS
        properties:
          endpoint: ALB_DNS

  kg_pulumi_outputs:
    superset_endpoint: alb_dns_name
```

## Pulumi stack

Provisions:
- EC2 (t3.small default)
- Postgres RDS or Docker Compose postgres (configurable)
- ElastiCache Redis or Docker Compose Redis (configurable)
- ALB with HTTPS listener + ACM cert
- Route53 A record: `superset.{project_name}.dwe.school`
- Secrets Manager: all superset secrets + DB URL + Redis URL

## dwe-hub plugin integration

The `dwe_hub_superset_plugin` (Superset browser plugin) connects to the org's deployed `dwe_superset` instance to publish and import dashboards. The connection is direct from the school's browser to their Superset — dwe-hub never proxies data.

```
Browser (in org's Superset)
    │  exports dashboard ZIP
    ▼
dwe-hub /publish endpoint
    │  stores ZIP (no data, just metadata + charts)
    ▼
dwe-hub S3

Later, another school:
    │  clicks Import in dwe-hub
    ▼
dwe-hub /download
    │  ZIP streamed to browser
    ▼
Superset import API (in their own deployed dwe_superset)
```

## Local testing

```bash
cd dwe_superset
docker compose up

# Superset UI: http://localhost:8088
# Default: admin/admin

# Connect to local Trino (from dwe_iceberg running in parallel)
# In Superset: Settings → Database Connections → Add
# SQLAlchemy URI: trino://localhost:8080/iceberg

# Test dashboard publish (requires dwe_hub_superset_plugin installed)
# In Superset: publish test dashboard → appears in local dwe-hub

# Test dwe-core hydration
dwe create-service dwe_superset \
  --adapters-path /path/to/dwe_superset \
  --git-repo https://github.com/test-org/dummy-repo \
  --project-name test-school
```
