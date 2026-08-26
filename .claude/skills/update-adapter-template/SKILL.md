---
name: update-adapter-template
description: "Run after making structural changes to a DWE adapter repo. Reads the current state of key files and updates the dwe-adapter skill documentation to keep it accurate."
---

# /update-adapter-template

Run this after any structural change to a DWE adapter: new infra pattern, new config file, changed secret list, changed CI flow, changed startup script logic, etc.

## What to do when invoked

1. **Identify which adapter repo is active** — check the current working directory or ask if unclear.

2. **Read the key files** in parallel:
   - `copier.yml` — parameters, secrets, `_dwe_hub` block
   - `docker-compose.yml` — services and network topology
   - `envs_prod.json` — config templates
   - `pulumi/__main__.py` — cloud routing
   - `pulumi/_startup.py` — shared boot fragments
   - `pulumi/_azure.py` — Azure resources and startup script
   - `pulumi/_aws.py` — AWS resources and startup script
   - `ci-templates/github.yaml` — CI workflow

3. **Identify what changed** — compare against what the `dwe-adapter` skill documents. Look for:
   - New or removed Pulumi resources
   - Changed VM startup sequence (new steps, removed steps, reordered)
   - Changed `discovery.uri` or networking topology
   - New parameters in `copier.yml` (especially `x_dwe_editable` / `x_dwe_per_env`)
   - New or removed required secrets
   - Changed CI flow (new jobs, changed paths filter, new steps)
   - Changed `envs_prod.json` structure or new config file types

4. **Update the dwe-adapter skill** at `~/.claude/skills/dwe-adapter/SKILL.md`:
   - Update the relevant sections that reflect the changes
   - Do NOT rewrite sections that haven't changed
   - Keep the "Common pitfalls" section updated with any new gotchas discovered

5. **Report what was updated** — a short bullet list of which sections changed and why.

## Sections in dwe-adapter skill to check

| Section | Update when… |
|---------|-------------|
| Anatomy diagram | Files added/removed from adapter |
| copier.yml — `_dwe_hub` | Services, KG outputs, CI templates changed |
| copier.yml — Parameters | New params added, `x_dwe_editable` changed |
| copier.yml — `required_secrets` | Secrets added/removed/changed destination |
| dwe-core's role | Hydration flow or `dwe-hydration.yaml` structure changed |
| Pulumi structure — `_startup.py` | Shared boot fragments changed |
| Pulumi structure — `_azure.py` | Azure resources or Azure-specific boot steps changed |
| Pulumi structure — `_aws.py` | AWS resources or AWS-specific boot steps changed |
| VM startup flow | Boot sequence order or steps changed |
| `envs_prod.json` format | New file types, changed template patterns |
| CI workflow — two paths | New jobs, changed trigger paths |
| Common pitfalls | New bugs discovered and fixed |

## Example invocations

```
/update-adapter-template
/update-adapter-template — just updated the startup script to use blob storage
/update-adapter-template — added worker_count scaling support
```

## After updating the skill

If the changes also affect other adapters (e.g., a change to `_startup.py` shared logic), note that in your report so the user can decide whether to propagate to other adapter repos.
