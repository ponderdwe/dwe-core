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
pip install poetry        # if not already installed
poetry install            # from dwe-core source (creates venv, installs deps)
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
  [--envs <name>]...       \   # repeat for multiple environments; default: development, main
  [--secrets <json>]       \   # e.g. '{"AWS_KEY":"abc"}'
  [--tag <version>]        \   # adapter git tag, e.g. v1.2.0
  [--token <api-token>]    \   # or set GITHUB_TOKEN / GITLAB_TOKEN
  [--set key=value]...     \   # override copier questions (run `dwe adapter-questions` to see keys)
  [--clone-dir <path>]         # default: temp dir
```

**Example — full run:**

```bash
export GITHUB_TOKEN=ghp_xxxx

dwe create-service dwe_cube \
  --git-repo https://github.com/acme/cube-deploy \
  --envs dev \
  --envs prod \
  --secrets '{"AZURE_CLIENT_ID":"...","AZURE_CLIENT_SECRET":"...","PULUMI_AZURE_STATE":"azblob://deploy-state/cube-state"}' \
  --tag v1.0.0 \
  --set git_repo_url=https://github.com/acme/cube-deploy \
  --set cloud_provider=azure
```

After this runs, the `cube-deploy` repo has:

```
.github/workflows/
  deploy-dev.yaml
  deploy-prod.yaml
docker-compose.yml
.env.example
justfile
pulumi/
  __main__.py          <- project_name already substituted
  Pulumi.yaml
  requirements.txt
dwe-hydration.yaml
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

### `dwe local-development`

```
dwe local-development <adapter_name> <secret> \
  [--output-dir <path>]      \   # default: current directory
  [--adapter-path <path>]    \   # override auto-detected template path
  [--aws-region <region>]        # default: us-east-1
```

Creates a local development folder from an adapter template, seeded with runtime config pulled directly from AWS Secrets Manager. No git repository is initialised — the output is a plain directory ready for `docker compose up`.

**If the folder already exists it is wiped and recreated from scratch** — running the command again is a clean reset.

**Example:**

```bash
dwe local-development dwe_cube my-cube-secret --aws-region us-east-1
```

What happens internally:

```
1. Locate       Finds the local Copier template for the adapter
                (auto-detected from monorepo structure, or --adapter-path)
2. Reset        Deletes <output-dir>/<adapter_name>/ if it already exists
3. Fetch        Calls AWS Secrets Manager to retrieve <secret> as JSON
4. Hydrate      Runs Copier to render the adapter template into the new folder
5. .env         Writes all secret key=value pairs to .env in the output folder
```

After the command completes:

```
dwe_cube/
├── docker-compose.yml
├── justfile
├── .env                  ← populated from AWS Secrets Manager
└── ...                   ← everything else from the adapter template
```

Start the stack:

```bash
cd dwe_cube
docker compose up
```

**Adapter path resolution** (in order):
1. `--adapter-path` flag (explicit override)
2. `path` field in `adapters.json` (if set)
3. Auto-detect: sibling directory of `dwe-core/` in the monorepo root named `<adapter_name>`

**AWS credentials** — the command uses `boto3` and picks up credentials the standard way: environment variables (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`), `~/.aws/credentials`, an IAM role, etc.

### `dwe adapter-questions`

```bash
dwe adapter-questions <adapter_name>
```

Lists the copier questions an adapter accepts. Use these as `--set key=value` overrides in `create-service`.

### `dwe show-properties`

```bash
dwe show-properties <adapter_name>
```

Shows supported cloud providers, git providers, services, and CI templates for an adapter.

### `dwe show-services`

```bash
dwe show-services <adapter_name>
```

Lists the Docker services bundled in an adapter.

### `dwe show-secrets-template`

```bash
dwe show-secrets-template <adapter_name> [--cloud aws|azure] [--git-provider github|gitlab]
```

Prints a JSON template of all secrets the adapter requires. Fill it in and upload with `set-secrets`.

### `dwe set-secrets`

```bash
dwe set-secrets \
  --git-repo <url> \
  [--secrets <json>]        \   # inline JSON
  [--secrets-file <path>]   \   # or a JSON file
  [--adapter <name>]        \   # validate required keys before pushing
  [--token <api-token>]         # or GITHUB_TOKEN / GITLAB_TOKEN
```

Creates or updates GitHub Actions secrets / GitLab CI variables in a repository.

### `dwe list-secrets`

```bash
dwe list-secrets --git-repo <url> [--adapter <name>] [--token <api-token>]
```

Lists secret key names in a repository. Values are never revealed. Pass `--adapter` to cross-reference against what the adapter requires.

### `dwe delete-secret`

```bash
dwe delete-secret --git-repo <url> --key <KEY> [--token <api-token>]
```

Deletes a single secret / CI variable from a repository.

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
├── justfile                    # Dev commands (just up, just logs, etc.)
│
├── blueprint/                  # Application-level config files
│   └── instance-setup.sh       # VM user-data bootstrap script
│
├── pulumi/                     # Pulumi IaC — only .jinja files are templated
│   ├── __main__.py             # Entry point (imports _aws.py / _azure.py)
│   ├── _aws.py                 # AWS-specific resources (ASG, ALB, Route53…)
│   ├── _azure.py               # Azure-specific resources (VMSS, AppGW, NLB…)
│   ├── Pulumi.yaml.jinja       # <- .jinja because it embeds {{ project_name }}
│   ├── dwe-hydration.yaml.jinja
│   └── requirements.txt.jinja
│
└── ci-templates/               # Jinja2 templates rendered by the CLI (not Copier)
    ├── github.yaml             # GitHub Actions — two-path deploy
    └── gitlab.yaml             # GitLab CI — two-path deploy
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
| `pulumi/Pulumi.yaml` | Jinja2 (`.jinja` extension) | Stack name must be unique per client |
| `pulumi/dwe-hydration.yaml` | Jinja2 (`.jinja` extension) | Adapter metadata stamped per client |
| `pulumi/requirements.txt` | Jinja2 (`.jinja` extension) | Pin adapter version at hydration time |
| `justfile` | Verbatim copy (no `.jinja`) | Commands are identical across clients |
| `blueprint/instance-setup.sh` | Verbatim copy | Generic bootstrap, no client-specific values |
| `.env.example` | Verbatim copy | Users fill in real values after cloning |

**Jinja2 syntax in `.jinja` files:**

```yaml
# pulumi/Pulumi.yaml.jinja
name: {{ project_name }}    # <- substituted by Copier
runtime: python
```

After `dwe create-service` this becomes:

```yaml
name: acme-cube-deploy
runtime: python
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

Available variables:

| Variable | Description |
|---|---|
| `{@ ENV_NAME @}` | Environment branch name (e.g. `dev`, `prod`) |
| `{@ WORKSPACE_NAME @}` | Pulumi stack / workspace name |
| `{@ SECRET_NAME @}` | Secret Manager secret name (Key Vault / Secrets Manager) |
| `{@ PROJECT_NAME @}` | Pulumi project name (used for config key prefix) |
| `{@ CLOUD_PROVIDER @}` | `aws` or `azure` |
| `{@ AWS_REGION @}` | AWS region (AWS only) |

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
       ├─── pulumi/** changed?
       │         │
       │         ├─ Pull Request → pulumi preview  (validate, no apply)
       │         └─ Push        → pulumi up --yes  (apply infra changes)
       │
       └─── docker-compose / blueprint changed?
                 AND pulumi NOT changed?
                         │
                         └─ Push → instance refresh (ASG) or VMSS update-instances
                                   (VMs reboot from base image, no Pulumi run)
```

**Why skip deploy when infra also changed?** The `pulumi up` step re-provisions the EC2 instance itself, which already pulls the latest code via its user-data script. Running the app deploy on top of that would be redundant and potentially racy.

### Job Summary

| Job | Trigger | What it does |
|---|---|---|
| `pulumi-preview` | PR, `pulumi/**` changed | Runs `pulumi preview` — shows what *would* change, no side effects |
| `pulumi-apply` | Push, `pulumi/**` changed | Runs `pulumi up --yes` + triggers instance refresh / VMSS update |
| `deploy-app` | Push, app files changed, `pulumi/**` NOT changed | Triggers instance refresh (ASG) or VMSS update-instances (Azure) — skips Pulumi entirely |

### Required Secrets

Set these via `dwe set-secrets` or manually in GitHub / GitLab repository settings. Use `dwe show-secrets-template <adapter>` to get the full list for a specific adapter.

**AWS:**

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS credentials for Pulumi + ASG |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `PULUMI_S3_STATE` | S3 backend URL, e.g. `s3://my-pulumi-state-bucket` |

**Azure:**

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_CLIENT_SECRET` | Service principal secret |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_STORAGE_ACCOUNT` | Storage account name for Pulumi state backend |
| `PULUMI_AZURE_STATE` | Azure Blob Storage URL, e.g. `azblob://container-name` |
| `KEY_VAULT_NAME` | Key Vault containing adapter runtime secrets |
| `RESOURCE_GROUP` | Resource group containing the VMSS |

### Example: What Happens on a Typical Push

**Scenario 1 — you edited `docker-compose.yml` or `blueprint/instance-setup.sh`:**

```
Push to development branch
  ↓
detect-changes: pulumi=false, app=true
  ↓
deploy-app runs:
  AWS:   starts ASG instance refresh (rolling, waits for Successful)
  Azure: az vmss update-instances --instance-ids '*' (waits for Succeeded)
  ↓
VMs reboot from base image, pick up latest code at startup
```

**Scenario 2 — you changed `pulumi/_azure.py` (e.g. bigger VM SKU):**

```
Push to development branch
  ↓
detect-changes: pulumi=true, app=false
  ↓
pulumi-apply runs:
  pulumi up --yes
  Azure auto-applies VMSS model change (Automatic upgrade policy)
  az vmss update-instances triggered for belt-and-suspenders
  ↓
Infrastructure updated. New instance picks up latest code at boot.
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

The same two-path logic works for GitLab CI. The adapter's `ci-templates/gitlab.yaml` mirrors `github.yaml` exactly — same `pulumi/**` path filter, same three jobs (`pulumi-preview`, `pulumi-apply`, `deploy-app`), same cloud-provider branching with `{% if CLOUD_PROVIDER == "azure" %}`.

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

## Releasing to PyPI

Two workflows handle the full release lifecycle:

```
bump version in pyproject.toml → merge to main
         │
         ▼
  tag-version.yml          triggers on: push to main, pyproject.toml changed
  reads Poetry version      creates git tag vX.Y.Z automatically
         │
         ▼
  (go to GitHub → Releases → Draft a new release → publish it)
         │
         ▼
  pypi-publish.yml          triggers on: release published
  poetry build + publish    pushes to PyPI via PYPI_TOKEN
```

### One-time setup

Add `PYPI_TOKEN` to the repository secrets (`Settings → Secrets → Actions`):

1. Go to **https://pypi.org/manage/account/token/** and create an API token scoped to `dwe-core`
2. In GitHub: `Settings → Secrets and variables → Actions → New repository secret`
   - Name: `PYPI_TOKEN`
   - Value: the token from PyPI (starts with `pypi-`)

### Release flow

**Step 1 — bump the version and merge to `main`:**

```bash
poetry version patch        # 1.0.0 → 1.0.1
poetry version minor        # 1.0.0 → 1.1.0
poetry version major        # 1.0.0 → 2.0.0
poetry version prerelease   # 1.0.0 → 1.0.1a1
poetry version 1.2.0        # set explicit version

git add pyproject.toml
git commit -m "chore: bump version to $(poetry version -s)"
git push origin main
```

`tag-version.yml` fires on the push, reads the version from `pyproject.toml`, and pushes tag `vX.Y.Z`. No manual tagging needed, and it only runs on `main`.

**Step 2 — publish the GitHub Release:**

Go to `github.com/<org>/dwe-core/releases`, click **Draft a new release**, select the tag just created, and click **Publish release**.

`pypi-publish.yml` fires on the publish event: runs `poetry install`, `poetry build`, then `poetry publish -u __token__ -p $PYPI_TOKEN`.

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
| AWS Secrets Manager | [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) |
| Infrastructure | [Pulumi](https://www.pulumi.com/) |
| Task runner | [Just](https://just.systems/) |
