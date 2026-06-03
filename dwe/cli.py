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
from dwe.secrets import (
    delete_secret,
    inject_secrets,
    list_secret_keys,
    set_secrets,
)
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
    """Render ci-templates/{platform}.yaml for each environment and write to repo."""
    ci_templates_dir = Path(adapter_path) / "ci-templates"
    template_file = f"{platform}.yaml"

    if not ci_templates_dir.exists() or not (ci_templates_dir / template_file).exists():
        console.print(
            f"[yellow]No ci-templates/{template_file} found in adapter, skipping CI/CD generation[/yellow]"
        )
        return

    # Use {@ @} as variable delimiters so ${{ }} GitHub/GitLab syntax is
    # never interpreted by Jinja2 and passes through verbatim.
    jinja_env = Environment(
        loader=FileSystemLoader(str(ci_templates_dir)),
        variable_start_string="{@",
        variable_end_string="@}",
        keep_trailing_newline=True,
    )

    if platform == "github":
        workflows_dir = Path(repo_path) / ".github" / "workflows"
    else:
        workflows_dir = Path(repo_path) / ".gitlab" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    template = jinja_env.get_template(template_file)
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


@app.command("set-secrets")
def set_secrets_cmd(
    git_repo: str = typer.Option(..., "--git-repo", help="Client repository URL"),
    secrets: Optional[str] = typer.Option(
        None, "--secrets", help='JSON string, e.g. \'{"AWS_KEY":"val"}\''
    ),
    secrets_file: Optional[str] = typer.Option(
        None, "--secrets-file", help="Path to a JSON file with secrets"
    ),
    adapter_name: Optional[str] = typer.Option(
        None, "--adapter", help="Validate against adapter required keys before pushing"
    ),
    token: Optional[str] = typer.Option(
        None, "--token",
        envvar=["GITHUB_TOKEN", "GITLAB_TOKEN"],
        help="API token for secret injection",
    ),
):
    """Create or update secrets / CI variables in a GitHub or GitLab repository."""
    if not token:
        console.print("[red]--token is required (or set GITHUB_TOKEN / GITLAB_TOKEN)[/red]")
        raise typer.Exit(1)

    if secrets_file:
        import pathlib
        raw = pathlib.Path(secrets_file).read_text()
    elif secrets:
        raw = secrets
    else:
        console.print("[red]Provide --secrets or --secrets-file[/red]")
        raise typer.Exit(1)

    try:
        secrets_dict = json.loads(raw)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON:[/red] {e}")
        raise typer.Exit(1)

    # Optional: validate required keys before pushing
    if adapter_name:
        catalog = get_adapter_catalog()
        info = catalog.get(adapter_name, {})
        required = [s["key"] for s in info.get("required_secrets", [])]
        missing = [k for k in required if k not in secrets_dict]
        if missing:
            console.print(f"[yellow]Warning — missing required keys:[/yellow] {', '.join(missing)}")

    owner, repo_name = parse_repo_info(git_repo)
    platform = "gitlab" if "gitlab" in git_repo.lower() else "github"
    console.print(
        f"\nPushing [bold]{len(secrets_dict)}[/bold] secret(s) to "
        f"[cyan]{owner}/{repo_name}[/cyan] ({platform})\n"
    )
    results = set_secrets(git_repo, owner, repo_name, secrets_dict, token)
    ok = sum(1 for v in results.values() if v)
    console.print(f"\n[bold]{ok}/{len(results)}[/bold] secret(s) pushed successfully.")


@app.command("list-secrets")
def list_secrets_cmd(
    git_repo: str = typer.Option(..., "--git-repo", help="Client repository URL"),
    adapter_name: Optional[str] = typer.Option(
        None, "--adapter", help="Cross-reference keys against adapter requirements"
    ),
    token: Optional[str] = typer.Option(
        None, "--token",
        envvar=["GITHUB_TOKEN", "GITLAB_TOKEN"],
    ),
):
    """List secret key names in a repository (values are never revealed)."""
    if not token:
        console.print("[red]--token is required (or set GITHUB_TOKEN / GITLAB_TOKEN)[/red]")
        raise typer.Exit(1)

    owner, repo_name = parse_repo_info(git_repo)
    existing = set(list_secret_keys(git_repo, owner, repo_name, token))

    required: list[str] = []
    optional: list[str] = []
    if adapter_name:
        catalog = get_adapter_catalog()
        info = catalog.get(adapter_name, {})
        required = [s["key"] for s in info.get("required_secrets", [])]
        optional = [s["key"] for s in info.get("optional_secrets", [])]

    all_keys = sorted(existing | set(required) | set(optional))

    table = Table(title=f"Secrets — [cyan]{owner}/{repo_name}[/cyan]")
    table.add_column("Key")
    table.add_column("Set", justify="center")
    if adapter_name:
        table.add_column("Required", justify="center")

    for key in all_keys:
        is_set = "[green]✓[/green]" if key in existing else "[red]✗[/red]"
        if adapter_name:
            if key in required:
                req_col = "[red]yes[/red]"
            elif key in optional:
                req_col = "[dim]optional[/dim]"
            else:
                req_col = ""
            table.add_row(key, is_set, req_col)
        else:
            table.add_row(key, is_set)
    console.print(table)


@app.command("delete-secret")
def delete_secret_cmd(
    git_repo: str = typer.Option(..., "--git-repo", help="Client repository URL"),
    key: str = typer.Option(..., "--key", help="Secret / variable key to delete"),
    token: Optional[str] = typer.Option(
        None, "--token",
        envvar=["GITHUB_TOKEN", "GITLAB_TOKEN"],
    ),
):
    """Delete a single secret / CI variable from a repository."""
    if not token:
        console.print("[red]--token is required (or set GITHUB_TOKEN / GITLAB_TOKEN)[/red]")
        raise typer.Exit(1)

    owner, repo_name = parse_repo_info(git_repo)
    delete_secret(git_repo, owner, repo_name, key, token)


@app.command("show-properties")
def show_properties(
    adapter_name: str = typer.Argument(..., help="Adapter name (as in adapters.json)"),
):
    """Show git providers, cloud providers, services, and CI templates for an adapter."""
    catalog = get_adapter_catalog()
    if adapter_name not in catalog:
        console.print(f"[red]Adapter '{adapter_name}' not found.[/red] Available: {list(catalog)}")
        raise typer.Exit(1)

    info = catalog[adapter_name]

    props = Table(title=f"[cyan]{adapter_name}[/cyan] properties", show_header=False, box=None)
    props.add_column("Property", style="dim", min_width=20)
    props.add_column("Value")
    props.add_row("Display name", info.get("display_name", ""))
    props.add_row("Description", info.get("description", ""))
    props.add_row("Hub name", info.get("hub_name", ""))
    props.add_row("Source URL", info.get("url") or info.get("path", ""))
    props.add_row("Type", info.get("type", ""))
    props.add_row("Git providers", ", ".join(info.get("git_providers", [])) or "—")
    props.add_row("Cloud providers", ", ".join(info.get("cloud_providers", [])) or "—")

    ci = info.get("ci_templates", {})
    props.add_row("CI templates", ", ".join(ci.keys()) if ci else "—")
    console.print(props)

    services = info.get("services", [])
    if services:
        svc_table = Table(title="Services", show_header=True)
        svc_table.add_column("Service", style="cyan")
        svc_table.add_column("Description")
        for s in services:
            svc_table.add_row(s.get("name", ""), s.get("description", ""))
        console.print(svc_table)


@app.command("show-services")
def show_services(
    adapter_name: str = typer.Argument(..., help="Adapter name (as in adapters.json)"),
):
    """List the services bundled in an adapter."""
    catalog = get_adapter_catalog()
    if adapter_name not in catalog:
        console.print(f"[red]Adapter '{adapter_name}' not found.[/red] Available: {list(catalog)}")
        raise typer.Exit(1)

    services = catalog[adapter_name].get("services", [])
    if not services:
        console.print(f"[yellow]No services defined for '{adapter_name}'.[/yellow]")
        return

    table = Table(title=f"[cyan]{adapter_name}[/cyan] services")
    table.add_column("Service", style="cyan bold")
    table.add_column("Description")
    for s in services:
        table.add_row(s.get("name", ""), s.get("description", ""))
    console.print(table)


@app.command("show-secrets-template")
def show_secrets_template(
    adapter_name: str = typer.Argument(..., help="Adapter name (as in adapters.json)"),
    cloud_provider: str = typer.Option("aws", "--cloud", help="Cloud provider filter (aws)"),
    git_provider: str = typer.Option("github", "--git-provider", help="Git provider (github | gitlab)"),
):
    """Print a JSON secrets template for the adapter — copy, fill values, upload to AWS/GitHub."""
    import json as _json

    catalog = get_adapter_catalog()
    if adapter_name not in catalog:
        console.print(f"[red]Adapter '{adapter_name}' not found.[/red] Available: {list(catalog)}")
        raise typer.Exit(1)

    info = catalog[adapter_name]
    required = info.get("required_secrets", [])
    optional = info.get("optional_secrets", [])

    template: dict = {}
    for s in required:
        template[s["key"]] = ""
    for s in optional:
        template[s["key"]] = ""

    console.print(f"\n[bold]Secrets template for[/bold] [cyan]{adapter_name}[/cyan] "
                  f"(cloud: {cloud_provider}, git: {git_provider})\n")
    console.print(_json.dumps(template, indent=2))

    if required:
        console.print("\n[bold red]Required keys:[/bold red]")
        for s in required:
            console.print(f"  [red]•[/red] [bold]{s['key']}[/bold] — {s.get('description', '')}")

    if optional:
        console.print("\n[dim]Optional keys:[/dim]")
        for s in optional:
            console.print(f"  [dim]•[/dim] {s['key']} — {s.get('description', '')}")


if __name__ == "__main__":
    app()
