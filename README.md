# dwe-core

The **DWE CLI** (`dwe`) is the orchestration brain of the Data Warehouse Ecosystem. It takes a blank or existing client Git repository and injects a fully working **Adapter** — infrastructure, application config, CI/CD pipelines, and local dev commands — in a single command.

## How it works

```
dwe create-service test_adapter --git-repo https://github.com/client/repo --envs dev --envs prod
```

Internally this does:

```
1. Clone        GitPython clones the client repo to a temp directory
2. Hydrate      Copier renders the adapter template into the clone
3. State        CLI writes dwe-state.json
4. CI/CD        CLI renders per-environment GitHub Actions / GitLab CI files
5. Branch       initial-commit branch is created and committed
6. Env branches dev, prod branches are created from initial-commit
7. Push         All branches are pushed to the remote
8. Secrets      GitHub/GitLab API uploads secrets to the repository settings
```

The result is a client repo that already has working infrastructure code, a `justfile` with `just up` / `just deploy-prod`, and CI/CD that deploys to the right environment when you push to its branch.

---

## Installation

```bash
pip install -e .          # from dwe-core source
# or once published:
pip install dwe-core
```

Verify:

```bash
dwe --help
dwe list-adapters
```

---

## Commands

### `dwe create-service`

```
dwe create-service <adapter_name> \
  --git-repo <url> \
  [--envs <name>]...       \   # default: development, main
  [--secrets <json>]       \   # e.g. '{"AWS_KEY":"abc"}'
  [--tag <version>]        \   # adapter git tag, e.g. v1.2.0
  [--token <api-token>]    \   # or set GITHUB_TOKEN / GITLAB_TOKEN
  [--aws-region <region>]  \
  [--instance-type <type>] \
  [--clone-dir <path>]         # default: temp dir
```

**Example — full run:**

```bash
export GITHUB_TOKEN=ghp_xxxx

dwe create-service test_adapter \
  --git-repo https://github.com/acme/data-platform \
  --envs development \
  --envs staging \
  --envs main \
  --secrets '{"PULUMI_ACCESS_TOKEN":"pul-xxx","AWS_ACCESS_KEY_ID":"AKI...","AWS_SECRET_ACCESS_KEY":"..."}' \
  --tag v1.0.0 \
  --aws-region eu-west-1 \
  --instance-type t3.small
```

After this runs, the `data-platform` repo has:

```
.github/workflows/
  deploy-development.yaml
  deploy-staging.yaml
  deploy-main.yaml
blueprint/
  html/index.html
  instance-setup.sh
docker-compose.yml
docker-compose.prod.yml
.env.example
justfile
infrastructure/
  __main__.py          <- project_name, instance_type already substituted
  Pulumi.yaml
  requirements.txt
dwe-state.json
.copier-answers.yml    <- Copier's internal state (enables future updates)
```

### `dwe update-service`

```
dwe update-service <adapter_name> <local_path> [--tag <version>]
```

**Example:**

```bash
dwe update-service test_adapter ./data-platform --tag v1.2.0
```

Internally:
1. Reads `dwe-state.json` and validates the adapter name matches
2. Creates a branch `dwe-update-20260322-1.2.0`
3. Runs `copier.run_update()` — **smart merge** that preserves your customisations
4. Updates `dwe-state.json` with the new version

Review the diff on the branch, then merge into your environment branches to trigger deployments.

### `dwe list-adapters`

```bash
dwe list-adapters
```

Shows all adapters registered in `adapters.json`.

---

## Adapter Registry (`adapters.json`)

```json
{
  "test_adapter": {
    "path": "/absolute/path/to/dwe_test_adapter",
    "type": "local",
    "description": "Test adapter: AWS EC2 instance via Pulumi"
  },
  "superset_adapter": {
    "url": "https://github.com/hipposys/dwe-superset-adapter",
    "type": "git",
    "description": "Apache Superset on ECS"
  }
}
```

---

## How to Define a New Adapter

An adapter is a **real, runnable project** that also serves as a Copier template. The guiding principle:

> **The adapter must work locally as-is.** A developer should be able to `git clone` the adapter, run `just up`, and have a working service — without running the DWE CLI at all.

### Step 1: Create the adapter repository

```bash
mkdir my_adapter && cd my_adapter
git init
```

### Step 2: Build a working application first

Build your service as a real project before adding any template variables. For example, if you're building a Superset adapter:

```bash
# Make it work locally first
docker compose up    # verify it runs
```

Only once everything works locally do you introduce `{{ variables }}`.

### Step 3: Directory structure

```
my_adapter/
├── copier.yml                  # Copier config + question definitions
│
├── docker-compose.yml          # Real, runnable. Uses ${ENV_VAR:-default} for runtime values.
├── docker-compose.prod.yml     # Production overrides (restart policy, logging)
├── .env.example                # Template for secrets — committed; .env is git-ignored
├── .gitignore
│
├── justfile                    # Dev commands (just up, just deploy-prod, just infra-up)
│
├── blueprint/                  # Application-level config files
│   ├── html/                   # or nginx.conf, superset_config.py, etc.
│   └── instance-setup.sh       # EC2 user-data bootstrap script
│
├── infrastructure/             # Pulumi IaC — only files here use .jinja
│   ├── __main__.py.jinja       # <- .jinja because it embeds {{ project_name }}
│   ├── Pulumi.yaml.jinja       # <- .jinja because it embeds {{ project_name }}
│   └── requirements.txt
│
└── ci-templates/               # Jinja2 templates rendered by the CLI (not Copier)
    └── deploy.yaml             # Uses {{ ENV_NAME }}, {{ AWS_REGION }}
```

### Step 4: Write `copier.yml`

`copier.yml` controls how Copier processes the adapter. Key settings:

```yaml
_templates_suffix: .jinja    # ONLY files ending in .jinja are treated as templates
                              # Everything else is copied verbatim

_exclude:
  - copier.yml               # Don't copy Copier's own config
  - ci-templates             # CLI handles this separately
  - README.md                # Adapter's README is not for client repos
  - .git
  - .env                     # Never copy actual secrets
  - __pycache__
  - "*.pyc"

_skip_if_exists:
  - .env.example             # Preserve user customisations on updates

# Questions (answered non-interactively by the dwe CLI):
project_name:
  type: str
  help: "Client project name (used for cloud resource naming)"

adapter_name:
  type: str
  default: "my_adapter"
  when: false    # always set programmatically

adapter_version:
  type: str
  default: "v1.0.0"
  when: false    # always set programmatically

environments:
  type: yaml
  default: "[development, main]"

aws_region:
  type: str
  default: "us-east-1"
```

### Step 5: Decide what needs Jinja2

Apply this rule: **if the value changes per client, use `{{ variable }}`. If it changes per deployment environment, use a `.env` variable.**

| File | Approach | Reason |
|---|---|---|
| `docker-compose.yml` | `.env` interpolation (`${VAR:-default}`) | Works locally without any substitution; runtime config |
| `infrastructure/__main__.py` | Jinja2 (`.jinja` extension) | Cloud resource names must be unique per client at provision time |
| `infrastructure/Pulumi.yaml` | Jinja2 (`.jinja` extension) | Stack name must be unique per client |
| `justfile` | Verbatim copy (no `.jinja`) | Commands are identical across clients |
| `blueprint/instance-setup.sh` | Verbatim copy | Generic bootstrap, no client-specific values |
| `.env.example` | Verbatim copy | Users fill in real values after cloning |

**Jinja2 syntax in `.jinja` files:**

```python
# infrastructure/__main__.py.jinja
instance = aws.ec2.Instance(
    "{{ project_name }}-instance",          # <- substituted by Copier
    instance_type="{{ instance_type }}",
    ...
)
```

After `dwe create-service` this becomes:

```python
instance = aws.ec2.Instance(
    "acme-data-platform-instance",
    instance_type="t3.small",
    ...
)
```

### Step 6: Write `ci-templates/deploy.yaml`

This is a Jinja2 file rendered by the `dwe` CLI (not by Copier) to generate one workflow file per environment. The CLI uses `{@ @}` as variable delimiters (not `{{ }}`), so GitHub Actions `${{ secrets.X }}` syntax passes through **untouched** — no escaping needed.

```yaml
name: Deploy to {@ ENV_NAME @}

on:
  push:
    branches:
      - {@ ENV_NAME @}
  pull_request:
    branches:
      - {@ ENV_NAME @}

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: {@ ENV_NAME @}
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: just deploy-prod
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}    # passes through unchanged
          AWS_REGION: {@ AWS_REGION @}                           # substituted by dwe CLI
```

Available variables: `{@ ENV_NAME @}`, `{@ AWS_REGION @}`.

### Step 7: Register the adapter

Add an entry to `dwe-core/adapters.json`:

**Local (development):**
```json
{
  "my_adapter": {
    "path": "/absolute/path/to/my_adapter",
    "type": "local",
    "description": "My adapter description"
  }
}
```

**Remote Git (production):**
```json
{
  "my_adapter": {
    "url": "https://github.com/your-org/my-adapter",
    "type": "git",
    "description": "My adapter description"
  }
}
```

### Step 8: Test the adapter

**Test locally first (without DWE CLI):**

```bash
cd my_adapter
cp .env.example .env
just up                    # docker compose up — must work here
```

**Test Copier rendering in isolation:**

```bash
pip install copier
copier copy /path/to/my_adapter /tmp/test-output \
  --data project_name=testproject \
  --data aws_region=us-east-1 \
  --defaults --overwrite --trust

# Inspect the output
ls /tmp/test-output
cat /tmp/test-output/infrastructure/Pulumi.yaml    # should have project_name substituted
cat /tmp/test-output/docker-compose.yml            # should be identical to source
cd /tmp/test-output && docker compose up           # should still work
```

**Test via dwe CLI:**

```bash
dwe create-service my_adapter \
  --git-repo https://github.com/test-org/empty-repo \
  --envs development \
  --envs main
```

---

## Adapter Versioning and Updates

Tag your adapter repository with semantic version tags. The DWE CLI and Copier use these tags for `update-service`:

```bash
cd my_adapter
git add -A && git commit -m "feat: add postgres service"
git tag v1.1.0
git push origin v1.1.0
```

When a client wants to update:

```bash
dwe update-service my_adapter ./client-repo --tag v1.1.0
```

Copier reads the source URL from `.copier-answers.yml` in the client repo, checks out `v1.1.0`, and runs a 3-way merge. Files the user has customised are preserved where possible; conflicts surface as standard git merge conflicts.

**What gets updated:**
- `infrastructure/` — Pulumi code (Jinja2 re-rendered with new template)
- `blueprint/` — Application config files
- `justfile` — Dev commands

**What is NOT updated (protected):**
- `.env.example` — skipped if it already exists (`_skip_if_exists` in `copier.yml`)
- `.copier-answers.yml` — managed by Copier internally

---

## State Files

### `dwe-state.json` (DWE-managed)

Written by the `dwe` CLI after `copier.run_copy()`. Tracks DWE-specific metadata:

```json
{
  "dwe_version": "1.0.0",
  "adapter": {
    "name": "test_adapter",
    "version": "v1.0.0",
    "last_update": "2026-03-22"
  },
  "environments": ["development", "main"],
  "infrastructure": "pulumi"
}
```

### `.copier-answers.yml` (Copier-managed)

Written by Copier. Tracks the template source, version, and question answers. **Do not edit manually.** This is what enables `copier.run_update()` to know where the template came from.

```yaml
# Changes here will be overwritten by copier
_commit: v1.0.0
_src_path: /path/to/my_adapter
project_name: acme-data-platform
aws_region: eu-west-1
instance_type: t3.small
```

Both files coexist. `dwe-state.json` is for DWE tooling; `.copier-answers.yml` is for Copier's update machinery.

---

## Developer Workflow After `create-service`

Once the client repo is hydrated, the full developer loop is:

**1. Local development (laptop):**

```bash
git clone https://github.com/client/data-platform
cd data-platform
cp .env.example .env      # fill in local values (no real AWS keys needed)
just up                   # docker compose up — app is running at localhost:8080
```

**2. Provision cloud infrastructure (once):**

```bash
# Fill in real AWS keys in .env
just install-infra         # pip install pulumi pulumi-aws
just infra-preview         # see what Pulumi will create
just infra-up              # provision the EC2 instance
```

**3. Deploy to EC2 (SSH into the instance, then):**

```bash
git clone https://github.com/client/data-platform /srv/app
cd /srv/app
cp .env.example .env       # fill in production values
just deploy-prod           # docker compose -f ... up -d
```

**4. CI/CD (automatic after push):**

Pushing to `development` or `main` triggers the corresponding GitHub Actions workflow. See the [CI/CD Workflow Design](#cicd-workflow-design) section below for the full two-path logic.

---

## CI/CD Workflow Design

The generated CI/CD workflow (`.github/workflows/deploy-{env}.yaml`) implements a **two-path** logic inspired by the Superset production setup. The key insight: infrastructure changes and application changes require completely different responses.

### The Two Paths

```
Push to branch
       │
       ▼
  Detect changes
  (dorny/paths-filter)
       │
       ├─── infrastructure/** changed?
       │         │
       │         ├─ Pull Request → pulumi preview  (validate, no apply)
       │         └─ Push        → pulumi up --yes  (apply infra changes)
       │
       └─── docker-compose / blueprint changed?
                 AND infrastructure NOT changed?
                         │
                         └─ Push → SSM: git pull + just deploy-prod
                                   (redeploy app on the live EC2 instance)
```

**Why skip deploy when infra also changed?** The `pulumi up` step re-provisions the EC2 instance itself, which already pulls the latest code via its user-data script. Running the app deploy on top of that would be redundant and potentially racy.

### Job Summary

| Job | Trigger | What it does |
|---|---|---|
| `pulumi-preview` | PR, `infrastructure/**` changed | Runs `pulumi preview` — shows what *would* change, no side effects |
| `pulumi-apply` | Push, `infrastructure/**` changed | Runs `pulumi up --yes` — applies infra changes |
| `deploy-app` | Push, app files changed, infra NOT changed | AWS SSM command: `git pull && just deploy-prod` on live EC2 |

### Required Secrets

Set these via `dwe create-service --secrets '{...}'` or manually in GitHub repository settings:

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS credentials for Pulumi and SSM |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `PULUMI_ACCESS_TOKEN` | Pulumi Cloud token |
| `PULUMI_CONFIG_PASSPHRASE` | Pulumi stack encryption passphrase |
| `PULUMI_STACK` | Pulumi stack reference, e.g. `myorg/myproject/development` |
| `EC2_INSTANCE_ID` | Instance ID from `pulumi stack output instance_id`, e.g. `i-0abc1234` |

### SSM Prerequisites

The `deploy-app` job uses **AWS Systems Manager (SSM)** instead of SSH — no port 22, no SSH key stored as a secret.

To enable SSM on the EC2 instance:

**1. IAM instance profile** — attach a role with these policies to the EC2:
```json
{
  "Effect": "Allow",
  "Action": [
    "ssm:UpdateInstanceInformation",
    "ssmmessages:CreateControlChannel",
    "ssmmessages:OpenControlChannel",
    "ec2messages:GetMessages",
    "ec2messages:SendReply"
  ],
  "Resource": "*"
}
```

Or simply attach the AWS managed policy `AmazonSSMManagedInstanceCore`.

**2. SSM agent** — Amazon Linux 2023 ships with it pre-installed. The `blueprint/instance-setup.sh` bootstrap script ensures it's running:
```bash
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent
```

**3. Store the instance ID** — after running `just infra-up`, get the instance ID and store it as a secret:
```bash
cd infrastructure && pulumi stack output instance_id
# → i-0abc1234567890def
# Add this to GitHub repository secrets as EC2_INSTANCE_ID
```

### Example: What Happens on a Typical Push

**Scenario 1 — you edited `blueprint/html/index.html`:**

```
Push to development branch
  ↓
detect-changes: infrastructure=false, app=true
  ↓
deploy-app runs:
  aws ssm send-command "git pull && just deploy-prod"
  polls every 10s until success
  prints stdout from EC2 instance
  ↓
New HTML is live ~30 seconds after push
```

**Scenario 2 — you changed `infrastructure/__main__.py.jinja` (e.g. bigger instance type):**

```
Push to development branch
  ↓
detect-changes: infrastructure=true, app=false
  ↓
pulumi-apply runs:
  pulumi up --yes
  Pulumi modifies the EC2 instance type in-place (or replaces it)
  ↓
Infrastructure updated. New instance pulls latest code via user-data.
```

**Scenario 3 — you opened a PR with Pulumi changes:**

```
Pull Request to development
  ↓
detect-changes: infrastructure=true
  ↓
pulumi-preview runs:
  pulumi preview
  Output shown in CI logs — no changes applied
  ↓
Reviewer can see exactly what Pulumi will do before merging.
```

### Adapting for Other Platforms

The same two-path logic works for GitLab CI. The superset's `.gitlab-ci.yml` uses:

```yaml
# Skip deploy if terraform changed
- if: $CI_COMMIT_BRANCH == "main"
  changes:
    - terraform_scalling/**/*
  when: never
# Only deploy if docker/compose changed
- if: $CI_COMMIT_BRANCH == "main"
  changes:
    - docker/**/*
    - docker-compose.yml
```

For your adapter's GitLab template, mirror this pattern with `pulumi` instead of `terraform` and `infrastructure/**` instead of `terraform_scalling/**`.

---

## Adding a New Environment Later

Environments are set up at `create-service` time. To add one later:

```bash
# Create the branch
git checkout initial-commit
git checkout -b staging
git push origin staging

# Generate the workflow file
cp .github/workflows/deploy-development.yaml .github/workflows/deploy-staging.yaml
# Edit deploy-staging.yaml: change all occurrences of "development" to "staging"
git add .github/workflows/deploy-staging.yaml
git commit -m "chore: add staging environment"
git push
```

---

## Technical Stack

| Concern | Library |
|---|---|
| CLI framework | [Typer](https://typer.tiangolo.com/) |
| Template engine | [Copier](https://copier.readthedocs.io/) |
| Git operations | [GitPython](https://gitpython.readthedocs.io/) |
| GitHub secrets | [PyGithub](https://pygithub.readthedocs.io/) |
| GitLab variables | [python-gitlab](https://python-gitlab.readthedocs.io/) |
| Runtime templating | [Jinja2](https://jinja.palletsprojects.com/) (for CI templates) |
| Infrastructure | [Pulumi](https://www.pulumi.com/) |
| Task runner | [Just](https://just.systems/) |
