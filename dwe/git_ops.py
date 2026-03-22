import tempfile
from pathlib import Path
from typing import Optional

import git
from rich.console import Console

console = Console()


def detect_platform(git_url: str) -> str:
    return "gitlab" if "gitlab" in git_url.lower() else "github"


def parse_repo_info(git_url: str) -> tuple[str, str]:
    """Return (owner, repo_name) from a git URL (HTTPS or SSH)."""
    url = git_url.rstrip("/").removesuffix(".git")
    if "@" in url and ":" in url:
        # SSH: git@github.com:owner/repo
        path_part = url.split(":")[-1]
    else:
        # HTTPS: https://github.com/owner/repo
        parts = url.split("/")
        path_part = "/".join(parts[-2:])
    parts = path_part.split("/")
    return parts[-2], parts[-1]


def clone_repo(git_url: str, target_dir: Optional[str] = None) -> tuple[git.Repo, str]:
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix="dwe-")
    console.print(f"[blue]Cloning[/blue] {git_url} → {target_dir}")
    repo = git.Repo.clone_from(git_url, target_dir)
    return repo, target_dir


def create_and_checkout_branch(repo: git.Repo, branch_name: str) -> git.Head:
    """Create branch from current HEAD and check it out."""
    branch = repo.create_head(branch_name)
    branch.checkout()
    return branch


def commit_all(repo: git.Repo, message: str) -> None:
    """Stage all changes and commit."""
    repo.git.add(A=True)
    if not repo.is_dirty(index=True, untracked_files=True):
        console.print("[yellow]Nothing to commit[/yellow]")
        return
    repo.index.commit(message)


def push_branch(repo: git.Repo, branch_name: str) -> None:
    remote = repo.remote("origin")
    console.print(f"[blue]Pushing[/blue] {branch_name}")
    remote.push(refspec=f"refs/heads/{branch_name}:refs/heads/{branch_name}")


def checkout_adapter_tag(adapter_path: str, tag: Optional[str]) -> None:
    """Checkout a specific tag in the adapter repo (if it's a git repo)."""
    if tag is None:
        return
    try:
        adapter_repo = git.Repo(adapter_path)
        adapter_repo.git.checkout(tag)
        console.print(f"[green]Checked out[/green] adapter tag: {tag}")
    except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
        console.print(f"[yellow]Warning:[/yellow] Could not checkout tag {tag}: {e}")
