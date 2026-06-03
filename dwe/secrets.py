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
Secret / CI-variable management for GitHub and GitLab.

GitHub  → repository Actions secrets  (encrypted, write-only via API)
GitLab  → project CI/CD variables     (can be read back — keys listed, values masked)
"""

import json
from typing import Optional

from rich.console import Console
from rich.table import Table

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# GitHub
# ─────────────────────────────────────────────────────────────────────────────

def _gh_repo(owner: str, repo: str, token: str):
    from github import Github
    return Github(token).get_repo(f"{owner}/{repo}")


def set_github_secrets(owner: str, repo: str, secrets: dict, token: str) -> dict[str, bool]:
    """Upsert secrets into a GitHub repo. Returns {key: success}."""
    results: dict[str, bool] = {}
    try:
        gh_repo = _gh_repo(owner, repo, token)
        for key, value in secrets.items():
            try:
                gh_repo.create_secret(key, str(value))
                console.print(f"  [green]✓[/green] {key}")
                results[key] = True
            except Exception as e:
                console.print(f"  [red]✗[/red] {key}: {e}")
                results[key] = False
    except Exception as e:
        console.print(f"[red]GitHub connection failed:[/red] {e}")
    return results


def list_github_secret_keys(owner: str, repo: str, token: str) -> list[str]:
    """Return the names of all Actions secrets in the repo (values are not accessible)."""
    try:
        gh_repo = _gh_repo(owner, repo, token)
        return [s.name for s in gh_repo.get_secrets()]
    except Exception as e:
        console.print(f"[red]GitHub list secrets failed:[/red] {e}")
        return []


def delete_github_secret(owner: str, repo: str, key: str, token: str) -> bool:
    try:
        _gh_repo(owner, repo, token).delete_secret(key)
        console.print(f"  [green]✓[/green] deleted {key}")
        return True
    except Exception as e:
        console.print(f"  [red]✗[/red] {key}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# GitLab
# ─────────────────────────────────────────────────────────────────────────────

def _gl_project(owner: str, repo: str, token: str):
    import gitlab
    gl = gitlab.Gitlab("https://gitlab.com", private_token=token)
    return gl.projects.get(f"{owner}/{repo}")


def set_gitlab_variables(owner: str, repo: str, secrets: dict, token: str) -> dict[str, bool]:
    """Upsert CI/CD variables into a GitLab project. Returns {key: success}."""
    results: dict[str, bool] = {}
    try:
        project = _gl_project(owner, repo, token)
        for key, value in secrets.items():
            try:
                try:
                    var = project.variables.get(key)
                    var.value = str(value)
                    var.save()
                except Exception:
                    project.variables.create({"key": key, "value": str(value), "masked": True})
                console.print(f"  [green]✓[/green] {key}")
                results[key] = True
            except Exception as e:
                console.print(f"  [red]✗[/red] {key}: {e}")
                results[key] = False
    except Exception as e:
        console.print(f"[red]GitLab connection failed:[/red] {e}")
    return results


def list_gitlab_variable_keys(owner: str, repo: str, token: str) -> list[str]:
    """Return the names of all CI/CD variables in the project."""
    try:
        return [v.key for v in _gl_project(owner, repo, token).variables.list(all=True)]
    except Exception as e:
        console.print(f"[red]GitLab list variables failed:[/red] {e}")
        return []


def delete_gitlab_variable(owner: str, repo: str, key: str, token: str) -> bool:
    try:
        _gl_project(owner, repo, token).variables.delete(key)
        console.print(f"  [green]✓[/green] deleted {key}")
        return True
    except Exception as e:
        console.print(f"  [red]✗[/red] {key}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Platform-agnostic helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_gitlab(git_url: str) -> bool:
    return "gitlab" in git_url.lower()


def set_secrets(
    git_url: str,
    owner: str,
    repo: str,
    secrets: dict,
    token: str,
) -> dict[str, bool]:
    if _is_gitlab(git_url):
        return set_gitlab_variables(owner, repo, secrets, token)
    return set_github_secrets(owner, repo, secrets, token)


def list_secret_keys(git_url: str, owner: str, repo: str, token: str) -> list[str]:
    if _is_gitlab(git_url):
        return list_gitlab_variable_keys(owner, repo, token)
    return list_github_secret_keys(owner, repo, token)


def delete_secret(git_url: str, owner: str, repo: str, key: str, token: str) -> bool:
    if _is_gitlab(git_url):
        return delete_gitlab_variable(owner, repo, key, token)
    return delete_github_secret(owner, repo, key, token)


# kept for backwards compat with create-service
def inject_secrets(
    git_url: str,
    owner: str,
    repo: str,
    secrets_json: Optional[str],
    token: Optional[str],
) -> None:
    if not secrets_json:
        return
    try:
        secrets = json.loads(secrets_json)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid secrets JSON:[/red] {e}")
        return
    if not token:
        console.print("[yellow]No API token — skipping secret injection[/yellow]")
        return
    set_secrets(git_url, owner, repo, secrets, token)
