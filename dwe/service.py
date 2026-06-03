# Copyright 2026 Ponder
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Programmatic API for dwe-core — callable from dwe-hub or any Python consumer.

hydrate_repo() is the single entry point that mirrors `dwe create-service` but
returns a result dict instead of printing to a console.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class HydrationError(Exception):
    pass


def hydrate_repo(
    *,
    adapter_hub_name: str,
    git_repo: str,
    workspace_mappings: list[dict],
    token: str,
    git_username: str = "",
    secrets: Optional[dict] = None,
    aws_region: str = "us-east-1",
    instance_type: str = "t3.xlarge",
    git_provider: str = "github",
    inject_ci_secrets: bool = False,
    branch_prefix: str = "dwe-hub",
) -> dict:
    """
    Clone a client repo, hydrate it with the adapter template via Copier,
    generate CI/CD, commit and push a new branch.

    Parameters
    ----------
    adapter_hub_name : str
        Hub alias (e.g. "cube").  Resolved to the adapter's source URL via the registry.
    git_repo : str
        Client repository URL (cloned, hydrated, pushed back to).
    workspace_mappings : list[dict]
        Each entry: {"branch": str, "workspace": str, "secret_name": str}.
        branch    — git branch name, triggers the CI workflow for that environment.
        workspace — Pulumi stack/workspace name selected at deploy time.
        secret_name — AWS Secrets Manager secret name for this environment
                      (e.g. "DWE_DEPLOY_CUBE_dev").
    token : str
        Git provider token for clone + push (and optionally secret injection).
    secrets : dict, optional
        Key/value secrets.  Injected into GitHub/GitLab if inject_ci_secrets=True.
    aws_region : str
        AWS region passed as a Copier variable.
    instance_type : str
        EC2 instance type passed as a Copier variable.
    git_provider : str
        "github" or "gitlab".
    inject_ci_secrets : bool
        If True, push only destination=ci secrets to the repo's CI/CD secret store.
    branch_prefix : str
        Prefix for the created branch (default "dwe-hub").

    Returns
    -------
    dict
        branch_name, repo_url, pushed (bool)
    """
    import copier

    from dwe.git_ops import (
        clone_repo,
        commit_all,
        create_and_checkout_branch,
        parse_repo_info,
        push_branch,
    )
    from dwe.registry import get_adapter_by_hub_name
    from dwe.secrets import set_secrets
    from dwe.state import write_state

    # ── 1. Resolve adapter ────────────────────────────────────────���──────────
    adapter_info = get_adapter_by_hub_name(adapter_hub_name)
    if not adapter_info:
        raise HydrationError(
            f"Adapter with hub_name='{adapter_hub_name}' not found in registry."
        )

    adapter_src = adapter_info.get("url") or adapter_info.get("path")
    if not adapter_src:
        raise HydrationError(f"Adapter '{adapter_hub_name}' has no url or path.")

    # Inject credentials into the adapter template URL so Copier can clone it.
    # Use git+ prefix so Copier always recognises it as a VCS URL regardless
    # of any credentials embedded in the URL.
    if adapter_src.startswith("https://"):
        _adapter_token = os.environ.get("GITHUB_TOKEN", "")
        _adapter_provider = "gitlab" if "gitlab.com" in adapter_src else "github"
        _authed = _inject_token(adapter_src, _adapter_token, _adapter_provider)
        adapter_src = "git+" + _authed

    adapter_key = adapter_info["name"]
    owner, repo_name = parse_repo_info(git_repo)

    # Derive unique ordered branch list for Copier + state
    environments = list(dict.fromkeys(m["branch"] for m in workspace_mappings)) or ["main"]

    # ── 2. Build authenticated clone URL ────────────────────────────────────
    authed_url = _inject_token(git_repo, token, git_provider, git_username)

    branch_name = f"{branch_prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    tmpdir = tempfile.mkdtemp(prefix=f"dwe-hydrate-{repo_name}-")
    try:
        # ── 3. Clone client repo ─────────────────────────────────────────────
        logger.info("Cloning %s into %s", git_repo, tmpdir)
        repo, repo_path = clone_repo(authed_url, tmpdir)

        # ── 4. Run Copier — hydrate adapter template into clone ──────────────
        logger.info("Running copier.run_copy src=%s dst=%s", adapter_src, repo_path)
        copier.run_copy(
            src_path=adapter_src,
            dst_path=repo_path,
            data={
                "project_name": repo_name,
                "adapter_name": adapter_key,
                "adapter_version": adapter_info.get("version", "v1.0.0"),
                "environments": environments,
                "aws_region": aws_region,
                "instance_type": instance_type,
                "git_platform": git_provider,
                "git_repo_url": git_repo,
            },
            defaults=True,
            overwrite=True,
            unsafe=True,
        )

        # ── 5. Write dwe-state.json ──────────────────────────────────────────
        write_state(repo_path, adapter_key, adapter_info.get("version", "v1.0.0"), environments)

        # ── 6. Generate CI/CD workflows ──────────────────────────────────────
        _generate_ci_workflows(
            adapter_src=adapter_src,
            repo_path=repo_path,
            workspace_mappings=workspace_mappings,
            platform=git_provider,
            aws_region=aws_region,
        )
        ci_templates_dir = Path(repo_path) / "ci-templates"
        if ci_templates_dir.exists():
            shutil.rmtree(ci_templates_dir)
            logger.info("Removed ci-templates from repo (CI files already generated)")

        # ── 7. Create branch, commit, push ───────────────────────────────────
        create_and_checkout_branch(repo, branch_name)
        commit_all(repo, f"chore: DWE Hub hydration [{adapter_key}] {datetime.now().isoformat()}")
        push_branch(repo, branch_name)
        logger.info("Pushed branch '%s' to %s", branch_name, git_repo)

        # ── 8. Optionally push CI-only secrets to GitHub/GitLab ─────────────
        if inject_ci_secrets and secrets and token:
            ci_secrets = _filter_ci_secrets(adapter_info, secrets)
            logger.info(
                "Injecting %d CI secrets (of %d total) into %s/%s",
                len(ci_secrets), len(secrets), owner, repo_name,
            )
            set_secrets(git_repo, owner, repo_name, ci_secrets, token)

        return {
            "branch_name": branch_name,
            "pushed": True,
            "repo_url": git_repo,
            "adapter": adapter_key,
        }

    except Exception as exc:
        logger.error("Hydration failed: %s", exc, exc_info=True)
        raise HydrationError(str(exc)) from exc
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _filter_ci_secrets(adapter_info: dict, secrets: dict) -> dict:
    """Return only the secrets whose destination includes 'ci' per the adapter catalog."""
    all_secrets = adapter_info.get("required_secrets", []) + adapter_info.get("optional_secrets", [])
    ci_keys = {s["key"] for s in all_secrets if _has_dest(s.get("destination"), "ci")}
    if not ci_keys:
        return secrets  # no destination metadata — inject everything (backwards compat)
    return {k: v for k, v in secrets.items() if k in ci_keys}


def _has_dest(destination, target: str) -> bool:
    if isinstance(destination, list):
        return target in destination
    return destination == target


def _inject_token(repo_url: str, token: str, git_provider: str, username: str = "") -> str:
    if not token or not repo_url.startswith("https://"):
        return repo_url
    base = repo_url[len("https://"):]
    if git_provider == "gitlab":
        # PAT: use username if provided, else fall back to oauth2
        user = username or "oauth2"
        return f"https://{user}:{token}@{base}"
    # GitHub: x-token-auth works for both PATs and deploy tokens
    return f"https://x-token-auth:{token}@{base}"


def _generate_ci_workflows(
    adapter_src: str,
    repo_path: str,
    workspace_mappings: list[dict],
    platform: str,
    aws_region: str,
) -> None:
    from jinja2 import Environment, FileSystemLoader

    ci_dir = Path(repo_path) / "ci-templates"
    if not ci_dir.exists() and not adapter_src.startswith("http"):
        ci_dir = Path(adapter_src) / "ci-templates"

    template_file = f"{platform}.yaml"
    if not ci_dir.exists() or not (ci_dir / template_file).exists():
        logger.warning("No ci-templates/%s found, skipping CI/CD generation", template_file)
        return

    jinja_env = Environment(
        loader=FileSystemLoader(str(ci_dir)),
        variable_start_string="{@",
        variable_end_string="@}",
        keep_trailing_newline=True,
    )

    template = jinja_env.get_template(template_file)

    if platform == "github":
        workflows_dir = Path(repo_path) / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        for mapping in workspace_mappings:
            env_name = mapping["branch"]
            workspace = mapping.get("workspace", env_name)
            secret_name = mapping.get("secret_name", f"DWE_DEPLOY_{env_name.upper()}")
            rendered = template.render(
                ENV_NAME=env_name,
                WORKSPACE_NAME=workspace,
                SECRET_NAME=secret_name,
                AWS_REGION=aws_region,
            )
            out = workflows_dir / f"deploy-{env_name}.yaml"
            out.write_text(rendered)
            logger.info("CI/CD generated: %s", out.relative_to(repo_path))
    else:
        # GitLab: single .gitlab-ci.yml at repo root with all environments
        sections = []
        for mapping in workspace_mappings:
            env_name = mapping["branch"]
            workspace = mapping.get("workspace", env_name)
            secret_name = mapping.get("secret_name", f"DWE_DEPLOY_{env_name.upper()}")
            sections.append(template.render(
                ENV_NAME=env_name,
                WORKSPACE_NAME=workspace,
                SECRET_NAME=secret_name,
                AWS_REGION=aws_region,
            ))
        out = Path(repo_path) / ".gitlab-ci.yml"
        out.write_text("\n".join(sections))
        logger.info("CI/CD generated: .gitlab-ci.yml (%d environments)", len(sections))
