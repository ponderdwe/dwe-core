# Design: dwe_iceberg Adapter

## Component architecture

```
┌─────────────────────────────────────────────────────┐
│                  EC2 Instance (prod)                 │
│                  Docker Compose                      │
│                                                      │
│  ┌──────────────┐     ┌──────────────────────────┐  │
│  │    Trino     │────▶│         Nessie           │  │
│  │  port 8080   │     │  Iceberg catalog         │  │
│  │  (query eng) │     │  port 19120              │  │
│  └──────────────┘     └──────────────────────────┘  │
│         │                        │                   │
│         └────────────────────────┘                   │
│                       │                              │
│              S3 / MinIO (data files)                 │
└─────────────────────────────────────────────────────┘
         │ ALB (HTTPS)
         ▼
   Schools query via Trino SQL
   (Superset, notebooks, dbt)
```

## Repo structure (dwe_iceberg)

```
dwe_iceberg/
├── copier.yml                    # Copier config + _dwe_hub metadata
├── docker-compose.yml            # Trino + Nessie + MinIO (dev)
├── docker-compose.prod.yml       # Trino + Nessie only (prod uses real S3)
├── .env.example
├── justfile                      # just up, just deploy-prod
├── config/
│   ├── trino/
│   │   ├── catalog/
│   │   │   └── iceberg.properties.jinja   # Nessie catalog config
│   │   └── config.properties
│   └── nessie/
│       └── application.properties
├── pulumi/
│   ├── __main__.py               # Valid Python, reads dwe-hydration.yaml
│   ├── Pulumi.yaml.jinja
│   └── requirements.txt
└── ci-templates/
    ├── github.yaml
    └── gitlab.yaml
```

## copier.yml questions

```yaml
project_name:      # Client project name
adapter_name:      # when=false, set programmatically
adapter_version:   # when=false, set programmatically
environments:      # [development, main]
aws_region:        # default: us-east-1
instance_type:     # default: t3.small (Trino needs more memory than t3.micro)
git_platform:      # github | gitlab
s3_bucket_name:    # default: {project_name}-iceberg-data
```

## _dwe_hub metadata

```yaml
_dwe_hub:
  hub_name: iceberg
  display_name: "DWE Iceberg"
  description: "Open table format data lake — Trino + Nessie + S3"
  git_providers: [github, gitlab]
  cloud_providers: [aws]
  depends_on: []      # Foundational — no upstream deps

  required_secrets:
    - key: AWS_ACCESS_KEY_ID
      destination: [ci, secrets_manager]
    - key: AWS_SECRET_ACCESS_KEY
      destination: [ci, secrets_manager]
    - key: PULUMI_ACCESS_TOKEN
      destination: ci

  optional_secrets:
    - key: AWS_REGION
      destination: ci
    - key: INSTANCE_TYPE
      destination: ci

  services:
    - name: trino
      type: service
      description: "Trino SQL query engine"
      kg:
        trigger_secret: ALB_DNS
        properties:
          endpoint: ALB_DNS

    - name: nessie
      type: service
      description: "Nessie Iceberg catalog"
      kg:
        trigger_secret: NESSIE_URL
        properties:
          endpoint: NESSIE_URL

  kg_pulumi_outputs:
    trino_endpoint: alb_dns_name
    nessie_endpoint: nessie_private_url
```

## Pulumi stack

Provisions:
- EC2 (t3.small default, 4GB RAM minimum for Trino)
- S3 bucket (versioned, private, lifecycle: transition to Glacier after 90 days)
- ALB → Trino port 8080 with HTTPS listener
- Route53 A record: `iceberg.{project_name}.dwe.school`
- Secrets Manager: TRINO_URL, NESSIE_URL, S3_BUCKET, AWS_REGION, S3_ACCESS_KEY, S3_SECRET_KEY

## Local testing

```bash
cd dwe_iceberg
docker compose up

# Trino UI: http://localhost:8080
# Nessie API: http://localhost:19120/api/v1/trees

# Connect Trino CLI
docker exec -it trino trino
> SHOW CATALOGS;
> CREATE SCHEMA iceberg.test;
> CREATE TABLE iceberg.test.students (id BIGINT, name VARCHAR) WITH (format = 'PARQUET');
> INSERT INTO iceberg.test.students VALUES (1, 'Alice');
> SELECT * FROM iceberg.test.students;

# Test dwe-core hydration (no git push, just template rendering)
dwe create-service dwe_iceberg \
  --adapters-path /path/to/dwe_iceberg \
  --git-repo https://github.com/test-org/dummy-repo \
  --project-name test-school \
  --git-token $GITHUB_TOKEN
```
