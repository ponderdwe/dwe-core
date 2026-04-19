"""DWE CLI — Data Warehouse Ecosystem Orchestrator.

Workflow (create-service):
  1. Clone client repo  →  GitPython
  2. Run copier.run_copy(adapter → local clone)  →  Copier (smart template engine)
  3. Write dwe-state.json  →  CLI post-processing
  4. Generate per-env CI/CD workflows  →  Jinja2 post-processing
  5. Branch (initial-commit) + per-env branches  →  GitPython
  6. Push  →  GitPython
  7. Inject secrets  →  PyGithub / python-gitlab
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dwe.git_ops import (
    checkout_adapter_tag,
    clone_repo,
    commit_all,
    create_and_checkout_branch,
    detect_platform,
    parse_repo_info,
    push_branch,
)
from dwe.registry import get_adapter, get_adapter_catalog, list_adapters, load_registry
from dwe.secrets import inject_secrets
from dwe.state import read_state, update_state_version, write_state

app = typer.Typer(
    name="dwe",
    help="DWE CLI — Data Warehouse Ecosystem Orchestrator",
    add_completion=False,
)
console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_adapter_version(adapter_path: str, tag: Optional[str]) -> str:
    """Read version from adapter.json (or copier.yml default), preferring --tag."""
    if tag:
        return tag
    meta_file = Path(adapter_path) / "adapter.json"
    if meta_file.exists():
        return json.loads(meta_file.read_text()).get("version", "v1.0.0")
    return "v1.0.0"


def _generate_ci_workflows(
    adapter_path: str,
    repo_path: str,
    environments: list[str],
    platform: str,
    aws_region: str,
) -> None:
    """Render ci-templates/deploy.yaml for each environment and write to repo."""
    ci_templates_dir = Path(adapter_path) / "ci-templates"
    if not ci_templates_dir.exists():
        console.print("[yellow]No ci-templates/ found in adapter, skipping CI/CD generation[/yellow]")
        return

    # Use {@ @} as variable delimiters so GitHub Actions ${{ }} syntax is
    # never interpreted by Jinja2 and passes through verbatim.
    jinja_env = Environment(
        loader=FileSystemLoader(str(ci_templates_dir)),
        variable_start_string="{@",
        variable_end_string="@}",
        keep_trailing_newline=True,
    )

    workflows_dir = (
        Path(repo_path) / ".github" / "workflows"
        if platform == "github"
        else Path(repo_path) / ".gitlab"
    )
    workflows_dir.mkdir(parents=True, exist_ok=True)

    template = jinja_env.get_template("deploy.yaml")
    for env_name in environments:
        rendered = template.render(ENV_NAME=env_name, AWS_REGION=aws_region)
        output = workflows_dir / f"deploy-{env_name}.yaml"
        output.write_text(rendered)
        console.print(f"[green]CI/CD generated:[/green] {output.relative_to(repo_path)}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command("create-service")
def create_service(
    adapter_name: str = typer.Argument(..., help="Adapter name (from registry, e.g. test_adapter)"),
    git_repo: str = typer.Option(..., "--git-repo", help="URL of the client's git repository"),
    secrets: Optional[str] = typer.Option(
        None, "--secrets", help='JSON string of secrets, e.g. \'{"AWS_KEY":"val"}\''
    ),
    envs: Optional[list[str]] = typer.Option(
        None, "--envs", help="Environment branches (repeat for multiple: --envs dev --envs prod)",
    ),
    tag: Optional[str] = typer.Option(None, "--tag", help="Adapter version tag to use"),
    token: Optional[str] = typer.Option(
        None, "--token",
        envvar=["GITHUB_TOKEN", "GITLAB_TOKEN"],
        help="API token for secret injection",
    ),
    aws_region: str = typer.Option("us-east-1", "--aws-region", help="AWS region"),
    instance_type: str = typer.Option("t3.micro", "--instance-type", help="EC2 instance type"),
    clone_dir: Optional[str] = typer.Option(
        None, "--clone-dir", help="Directory to clone into (default: temp dir)"
    ),
):
    """Clone a client repo and inject an adapter (blueprint + infra + CI/CD)."""
    import copier

    console.print(Panel(
        f"[bold]DWE Create Service[/bold]\n"
        f"Adapter: [cyan]{adapter_name}[/cyan]  Repo: [cyan]{git_repo}[/cyan]",
        expand=False,
    ))

    # Resolve adapter
    adapter_info = get_adapter(adapter_name)
    if not adapter_info:
        console.print(f"[red]Adapter '{adapter_name}' not found.[/red] Available: {list_adapters()}")
        raise typer.Exit(1)

    adapter_path = adapter_info["path"]
    if not Path(adapter_path).exists():
        console.print(f"[red]Adapter path does not exist:[/red] {adapter_path}")
        raise typer.Exit(1)

    checkout_adapter_tag(adapter_path, tag)
    adapter_version = _resolve_adapter_version(adapter_path, tag)
    environments = envs or ["development", "main"]
    platform = detect_platform(git_repo)
    owner, repo_name = parse_repo_info(git_repo)

    console.print(
        f"[dim]Platform: {platform} | Owner: {owner} | Repo: {repo_name} | "
        f"Envs: {environments} | Version: {adapter_version}[/dim]"
    )

    # 1. Clone client repo
    repo, repo_path = clone_repo(git_repo, clone_dir)

    # 2. Run Copier — hydrates infrastructure/ blueprint/ justfile
    console.print("[blue]Running Copier...[/blue]")
    copier.run_copy(
        src_path=adapter_path,
        dst_path=repo_path,
        data={
            "project_name": repo_name,
            "adapter_name": adapter_name,
            "adapter_version": adapter_version,
            "environments": environments,
            "aws_region": aws_region,
            "instance_type": instance_type,
            "git_platform": platform,
        },
        defaults=True,
        overwrite=True,
        unsafe=True,  # allow local paths as template source
    )

    # 3. Write dwe-state.json (CLI-managed, not Copier-managed)
    console.print("[blue]Writing dwe-state.json...[/blue]")
    write_state(repo_path, adapter_name, adapter_version, environments)

    # 4. Generate per-environment CI/CD workflow files
    console.print("[blue]Generating CI/CD workflows...[/blue]")
    _generate_ci_workflows(adapter_path, repo_path, environments, platform, aws_region)

    # 5. Create initial-commit branch and commit everything
    console.print("[blue]Creating branch: initial-commit[/blue]")
    create_and_checkout_branch(repo, "initial-commit")
    commit_all(repo, f"chore: inject {adapter_name} {adapter_version} via dwe")

    # 6. Push initial-commit
    push_branch(repo, "initial-commit")

    # 7. Create and push per-env branches (from initial-commit)
    for env_name in environments:
        console.print(f"[blue]Creating branch:[/blue] {env_name}")
        create_and_checkout_branch(repo, env_name)
        push_branch(repo, env_name)
        # Return to initial-commit for next env branch
        repo.heads["initial-commit"].checkout()

    # 8. Inject secrets
    inject_secrets(git_repo, owner, repo_name, secrets, token)

    # Summary
    table = Table(title="[green]Service Created[/green]")
    table.add_column("", style="dim")
    table.add_column("")
    table.add_row("Adapter", adapter_name)
    table.add_row("Version", adapter_version)
    table.add_row("Local path", repo_path)
    table.add_row("Branches", ", ".join(["initial-commit", *environments]))
    table.add_row("Infrastructure", "Pulumi")
    table.add_row("Run", "cd " + repo_path + " && just preview")
    console.print(table)


@app.command("update-service")
def update_service(
    adapter_name: str = typer.Argument(..., help="Adapter name to update"),
    local_path: str = typer.Argument(..., help="Local path to the client repository"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Adapter version tag to update to"),
):
    """Update an existing service with a newer adapter version (smart merge via Copier)."""
    import copier
    from datetime import date

    console.print(Panel(
        f"[bold]DWE Update Service[/bold]\n"
        f"Adapter: [cyan]{adapter_name}[/cyan]  Path: [cyan]{local_path}[/cyan]",
        expand=False,
    ))

    # Validate state
    try:
        state = read_state(local_path)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if state["adapter"]["name"] != adapter_name:
        console.print(
            f"[red]Adapter mismatch:[/red] state says '{state['adapter']['name']}' "
            f"but you specified '{adapter_name}'"
        )
        raise typer.Exit(1)

    current_version = state["adapter"]["version"]
    console.print(f"[dim]Current version: {current_version}[/dim]")

    # Resolve adapter
    adapter_info = get_adapter(adapter_name)
    if not adapter_info:
        console.print(f"[red]Adapter '{adapter_name}' not found.[/red]")
        raise typer.Exit(1)

    adapter_path = adapter_info["path"]
    checkout_adapter_tag(adapter_path, tag)
    new_version = _resolve_adapter_version(adapter_path, tag)
    console.print(f"[dim]New version: {new_version}[/dim]")

    # Open local repo and create update branch
    import git as gitlib
    try:
        repo = gitlib.Repo(local_path)
    except gitlib.InvalidGitRepositoryError:
        console.print(f"[red]{local_path} is not a git repository[/red]")
        raise typer.Exit(1)

    today = date.today().strftime("%Y%m%d")
    update_branch = f"dwe-update-{today}-{new_version.lstrip('v')}"
    console.print(f"[blue]Creating update branch:[/blue] {update_branch}")
    create_and_checkout_branch(repo, update_branch)

    # Run Copier update — smart merge: preserves user customisations
    console.print("[blue]Running copier.run_update (smart merge)...[/blue]")
    copier.run_update(
        dst_path=local_path,
        defaults=True,
        overwrite=True,
        unsafe=True,
        vcs_ref=tag,
    )

    # Update dwe-state.json
    update_state_version(local_path, new_version)
    console.print(f"[green]Version updated:[/green] {current_version} → {new_version}")

    # Commit update
    commit_all(repo, f"chore: update {adapter_name} {current_version} → {new_version}")

    console.print(Panel(
        f"[green]Update branch ready:[/green] {update_branch}\n\n"
        "Review the diff, then merge into your environment branches to trigger deployments.",
        title="Next Steps",
        expand=False,
    ))


@app.command("list-adapters")
def list_adapters_cmd(
    full: bool = typer.Option(False, "--full", help="Show required secrets for each adapter"),
):
    """List all registered adapters with metadata from their copier.yml."""
    catalog = get_adapter_catalog()
    if not catalog:
        console.print("[yellow]No adapters registered.[/yellow]")
        return

    table = Table(title="Registered Adapters")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name", style="bold")
    table.add_column("Type", style="green")
    table.add_column("Source")
    table.add_column("Description")

    for name, info in catalog.items():
        source = info.get("url") or info.get("path") or "N/A"
        table.add_row(
            name,
            info.get("display_name", name),
            info.get("type", "git"),
            source,
            info.get("description", ""),
        )
    console.print(table)

    if full:
        for name, info in catalog.items():
            required = info.get("required_secrets", [])
            optional = info.get("optional_secrets", [])
            if not required and not optional:
                continue
            secrets_table = Table(title=f"[cyan]{name}[/cyan] secrets", show_header=True)
            secrets_table.add_column("Key", style="bold")
            secrets_table.add_column("Required")
            secrets_table.add_column("Description")
            for s in required:
                secrets_table.add_row(s["key"], "[red]yes[/red]", s.get("description", ""))
            for s in optional:
                secrets_table.add_row(s["key"], "[dim]no[/dim]", s.get("description", ""))
            console.print(secrets_table)


if __name__ == "__main__":
    app()
