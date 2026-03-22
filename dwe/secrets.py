import json
from typing import Optional

from rich.console import Console

console = Console()


def inject_github_secrets(owner: str, repo: str, secrets: dict, token: str) -> None:
    try:
        from github import Github
        g = Github(token)
        gh_repo = g.get_repo(f"{owner}/{repo}")
        for key, value in secrets.items():
            gh_repo.create_secret(key, str(value))
            console.print(f"[green]Secret injected:[/green] {key}")
    except ImportError:
        console.print("[yellow]PyGithub not installed, skipping secret injection[/yellow]")
    except Exception as e:
        console.print(f"[red]GitHub secret injection failed:[/red] {e}")


def inject_gitlab_secrets(owner: str, repo: str, secrets: dict, token: str) -> None:
    try:
        import gitlab
        gl = gitlab.Gitlab("https://gitlab.com", private_token=token)
        project = gl.projects.get(f"{owner}/{repo}")
        for key, value in secrets.items():
            try:
                var = project.variables.get(key)
                var.value = str(value)
                var.save()
            except Exception:
                project.variables.create({"key": key, "value": str(value)})
            console.print(f"[green]Variable injected:[/green] {key}")
    except ImportError:
        console.print("[yellow]python-gitlab not installed, skipping secret injection[/yellow]")
    except Exception as e:
        console.print(f"[red]GitLab variable injection failed:[/red] {e}")


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
        console.print("[yellow]No API token — skipping secret injection (set GITHUB_TOKEN or GITLAB_TOKEN)[/yellow]")
        return

    if "gitlab" in git_url.lower():
        inject_gitlab_secrets(owner, repo, secrets, token)
    else:
        inject_github_secrets(owner, repo, secrets, token)
