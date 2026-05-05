# ADR-001: Technology Stack Selection for DWE (Data & Web Environment)

- **Date:** 2026-05-01
- **Status:** Proposed

---

## Context

DWE is a data platform stack designed to be deployed for schools. It needs to support ingestion, storage, transformation, querying, orchestration, visualization, and semantic modeling of data, while remaining open-source-friendly, scalable across multiple tenants, and maintainable by teams with varying levels of data engineering maturity.

The platform must:

- Handle structured and semi-structured data at scale
- Support multi-tenant deployments across different educational organizations
- Provide governed, versioned data with audit trails
- Enable both technical users (engineers, analysts) and non-technical users (teachers, administrators) to derive insights
- Minimize vendor lock-in
- Be deployable on-premise or in cloud environments

---

## Decision

We adopt the following tools as the core DWE stack:

| Layer | Tool |
|---|---|
| Object Storage | Amazon S3 (or S3-compatible) |
| Table Format | Apache Iceberg |
| Query Engine | Trino |
| Data Catalog / Version Control | Project Nessie |
| Transformation | dbt |
| Orchestration | Apache Airflow |
| Visualization | Apache Superset |
| Semantic Layer | Cube.js / Cube.dev |
| Development Environment | Coder |
| Graph Database | FalkorDB |

---

## Tool-by-Tool Breakdown

### 1. Amazon S3 (Object Storage)

**Role:** Central storage layer for raw, processed, and curated data.

**Why S3:**
- De facto standard for data lake storage
- S3-compatible APIs are supported by SeaweedFS, Ceph, and others, enabling on-premise deployments
- Deep integration with Iceberg, Trino, and dbt
- Cost-effective for large volumes of infrequently accessed data

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| HDFS | Operationally complex, declining ecosystem adoption |
| Azure Data Lake Storage | Vendor lock-in to Azure, but can be chosen for specific clients |
| Google Cloud Storage | Vendor lock-in to GCP, but can be chosen for specific clients |
| Minio | Changed License |

**Pros:** Ubiquitous, cheap, S3-compatible ecosystem is vast  
**Cons:** AWS-native; requires SeaweedFS or similar for fully on-premise setups

---

### 2. Apache Iceberg (Table Format)

**Role:** Open table format sitting on top of S3, providing ACID transactions, schema evolution, time travel, and partition pruning.

**Why Iceberg:**
- Enables data lake tables to behave like database tables
- Time travel and snapshot isolation are critical for audit and reproducibility in education data
- Strong support from Trino, Spark, and Flink
- Nessie provides Git-like branching on top of Iceberg

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| Delta Lake | Tighter coupling to Spark/Databricks ecosystem |
| Apache Hudi | More complex operationally; upsert-focused use case less relevant here |
| Parquet files (raw) | No ACID, no schema evolution, no time travel |

**Pros:** Open standard, excellent Trino integration, snapshot/time travel support  
**Cons:** Metadata management overhead; requires a catalog (Nessie/Glue/Hive)

---

### 3. Trino (Query Engine)

**Role:** Distributed SQL query engine for interactive and ad-hoc queries across Iceberg tables and other data sources.

**Why Trino:**
- Federated queries across S3/Iceberg, relational DBs, and other connectors
- High performance for interactive analytics without moving data
- Strong Iceberg and Nessie connector support
- Open source with active community (PrestoSQL fork)

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| Apache Spark SQL | Higher latency for interactive queries |
| DuckDB | Excellent for local/single-node but not suited for distributed multi-tenant workloads |
| Databricks SQL | Proprietary, costly, vendor lock-in |
| Athena | AWS-only, limited customization |

**Pros:** Fast interactive queries, federation, open source, great Iceberg support  
**Cons:** Stateless (no built-in caching by default); requires tuning for large concurrent workloads

---

### 4. Project Nessie (Data Catalog & Versioning)

**Role:** Git-like catalog for Iceberg tables, providing branching, tagging, and commit history for data assets.

**Why Nessie:**
- Enables isolated data environments (branches) per school or deployment
- Supports safe experimentation without affecting production data
- Native integration with Iceberg, Trino, and dbt
- Open source (Apache 2.0)

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| AWS Glue Catalog | AWS-only, no branching/versioning |
| Apache Hive Metastore | Legacy, no versioning, operationally heavy |
| Unity Catalog | Tied to Databricks ecosystem |

**Pros:** Data versioning is a unique differentiator, multi-tenant branch isolation, open source  
**Cons:** Smaller community than Hive/Glue; relatively newer project

---

### 5. dbt (Data Transformation)

**Role:** SQL-based transformation layer for building and testing data models on top of Trino/Iceberg.

**Why dbt:**
- Industry standard for analytics engineering
- Code-based transformations with version control (Git)
- Built-in testing, documentation, and lineage
- dbt-trino adapter is mature and well-maintained

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| Apache Spark (PySpark) | More complex, requires Python expertise, heavier infra |
| SQLMesh | Promising but smaller ecosystem and community |
| Custom SQL scripts | No lineage, no testing, not maintainable at scale |

**Pros:** SQL-native, huge community, excellent docs and lineage, CI/CD friendly  
**Cons:** Primarily ELT (not ETL); complex Python models can be harder to debug

---

### 6. Apache Airflow (Orchestration)

**Role:** Workflow orchestration for scheduling and managing data pipelines (ingestion, dbt runs, exports).

**Why Airflow:**
- Mature, battle-tested, widely adopted
- Rich ecosystem of providers (S3, databases, APIs)
- DAG-based workflows are intuitive for pipeline dependencies
- Strong community and documentation
- We already have many plugins built for that tool

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| Prefect | Newer, good UX but smaller ecosystem |
| Dagster | Asset-based model is excellent but steeper learning curve and less suitable for reverse ETL |
| Mage | Promising for smaller teams but less mature for complex pipelines |

**Pros:** Mature ecosystem, huge provider library, well-understood operational model  
**Cons:** DAG-as-code can become unwieldy; scheduler can be a bottleneck at very high scale

---

### 7. Apache Superset (Visualization)

**Role:** BI and data visualization layer for dashboards and ad-hoc exploration by analysts and non-technical users.

**Why Superset:**
- Open source with no per-seat licensing (critical for cost-sensitive schools)
- Native Trino connector
- Rich chart library and dashboard capabilities
- Row-level security supports multi-tenant access control
- We already have many plugins built for that tool

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| Metabase | Less powerful for complex dashboards; licensing costs at scale |
| Grafana | Excellent for metrics/ops, not suited for business analytics |
| Tableau / Power BI | Proprietary, expensive per-seat licensing |
| Redash | Less actively maintained |

**Pros:** Open source, no licensing cost, strong Trino support, row-level security  
**Cons:** UI/UX less polished than commercial tools; requires engineering effort to maintain

---

### 8. Cube.js / Cube.dev (Semantic Layer)

**Role:** Centralized semantic layer and metrics store, providing consistent business definitions, caching, and APIs on top of Trino.

**Why Cube.dev:**
- Decouples metric definitions from BI tools, ensuring consistency across Superset and other consumers
- Pre-aggregation and caching reduces load on Trino for repetitive queries
- REST, SQL and GraphQL APIs enable embedding analytics in applications
- Open source core

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| dbt Metrics (MetricFlow) | Less mature API layer; no built-in caching, expensive |
| LookML / Looker | Proprietary, expensive |
| AtScale | Enterprise pricing |

**Pros:** Consistent metrics, query acceleration, API-first, open source  
**Cons:** Adds another layer of complexity; pre-aggregation configuration can be involved

---

### 9. Coder (Development Environment)

**Role:** Cloud development environments (CDEs) for data engineers and analysts working on DWE, providing reproducible, browser-accessible workspaces.

**Why Coder:**
- Self-hosted, open source
- Engineers get consistent, pre-configured environments without local setup
- Supports VS Code in the browser and SSH access
- Workspaces can be templated per role (data engineer, analyst, admin)

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| GitHub Codespaces | GitHub dependency, cloud-only |
| Gitpod | Cloud-focused, less control over infra |
| Local dev environments | Inconsistent across team members, hard to onboard |

**Pros:** Self-hosted, reproducible environments, role-based templates, open source  
**Cons:** Requires infra to host; smaller community than GitHub Codespaces

---

### 10. FalkorDB (Graph Database)

**Role:** Graph database serving primarily as the backbone for AI-powered analysis of the DWE stack itself — specifically dbt project structure, lineage, and dependencies queryable in plain language. Additionally, it lays the foundation for future modeling of relationship-heavy educational data such as organizational hierarchies, curriculum dependencies, and student-teacher-course relationships.

**Why FalkorDB:**
- High-performance in-memory graph queries (built on RedisGraph lineage)
- Cypher query language, familiar and well-documented
- Lightweight and fast to deploy
- Purpose-built for AI application use cases — graph structure maps naturally to LLM reasoning and retrieval
- Existing plugins allow ingestion of dbt project graphs (models, sources, tests, dependencies) into FalkorDB, enabling plain-language querying of the dbt DAG (e.g. "Which models depend on the students source?", "What tests cover the enrollment model?", "What is the full lineage of the grades mart?")

**AI + dbt Integration:** dbt projects expose a rich dependency graph (models, sources, exposures, tests, metrics). By ingesting this graph into FalkorDB, platform teams and analysts can query the dbt structure conversationally via LLM-powered interfaces — without needing to read YAML or navigate the dbt DAG manually. This significantly lowers the barrier for understanding data lineage and impact analysis across DWE deployments.

**Future Use Cases:** Once the core dbt integration is stable, FalkorDB may be extended to model educational domain relationships — organizational hierarchies, curriculum dependencies, student-teacher-course graphs — where relational databases are a poor fit for traversal queries.

**Alternatives Considered:**

| Alternative | Reason Not Chosen |
|---|---|
| Neo4j | Enterprise licensing costs; heavier deployment |
| Amazon Neptune | AWS lock-in, costly |
| ArangoDB | Multi-model complexity not needed here |

**Pros:** Fast, lightweight, Cypher-compatible, open source  
**Cons:** Smaller community than Neo4j; persistence model requires attention in production

---

## Consequences

### Positive

- Fully open-source stack, no per-seat or proprietary licensing costs — critical for budget-constrained educational organizations
- S3 + Iceberg + Nessie gives a strong foundation for governed, versioned, auditable data
- Trino + dbt + Superset + Cube.dev covers the full analytics workflow from transformation to visualization
- Coder ensures reproducible development environments across all deployments
- FalkorDB handles graph-native queries without overloading the relational/Iceberg layer

### Negative / Risks

- Operational complexity is high — 10 tools require significant DevOps/platform engineering investment
- Team needs expertise across multiple technologies; onboarding curve is steep
- Some tools (Nessie, FalkorDB, Cube.dev) are relatively newer and carry ecosystem maturity risk
- Multi-tenant isolation must be carefully designed across each layer (Nessie branches, Superset RLS, Trino schemas)