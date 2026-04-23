import json
import os
import urllib.request
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

REGISTRY_PATH = Path(__file__).parent / "adapters.json"


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    return json.loads(REGISTRY_PATH.read_text())


def get_adapter(name: str) -> Optional[dict]:
    return load_registry().get(name)


def list_adapters() -> list[str]:
    return list(load_registry().keys())


# ─────────────────────────────────────────────────────────────────────────────
# Catalog — full metadata including copier.yml _dwe_hub section
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_url(url: str) -> str:
    req = urllib.request.Request(url)
    token = os.environ.get("GITHUB_TOKEN", "")
    if token and "github" in url:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode()


def _github_raw_url(repo_url: str, path: str = "copier.yml", branch: str = "main") -> str:
    url = repo_url.rstrip("/").removesuffix(".git")
    if url.startswith("https://github.com/"):
        slug = url[len("https://github.com/"):]
        return f"https://raw.githubusercontent.com/{slug}/{branch}/{path}"
    return ""


def _load_copier_yml(adapter_info: dict) -> dict:
    if yaml is None:
        return {}
    git_url = adapter_info.get("url", "")
    local_path = adapter_info.get("path", "")

    if git_url and git_url.startswith("http"):
        raw_url = _github_raw_url(git_url)
        if not raw_url:
            return {}
        try:
            return yaml.safe_load(_fetch_url(raw_url)) or {}
        except Exception:
            return {}

    if local_path:
        copier_file = Path(local_path) / "copier.yml"
        if copier_file.exists():
            return yaml.safe_load(copier_file.read_text()) or {}

    return {}


def get_adapter_by_hub_name(hub_name: str) -> Optional[dict]:
    """Look up a catalog entry by its dwe-hub alias (e.g. 'cube' → dwe_cube entry)."""
    for entry in get_adapter_catalog().values():
        if entry.get("hub_name") == hub_name:
            return entry
    return None


def _has_dest(destination, target: str) -> bool:
    """Return True if target is in destination (string or list)."""
    if isinstance(destination, list):
        return target in destination
    return destination == target


def _filter_by_dest(secrets: list, target: str) -> list:
    """Return secrets whose destination includes target."""
    return [s for s in secrets if _has_dest(s.get("destination"), target)]


def get_adapter_catalog() -> dict:
    """
    Return full adapter metadata dict keyed by adapter name (as in adapters.json).

    Each entry contains:
      name, hub_name, url, path, type, description,
      display_name, icon, required_secrets, optional_secrets,
      ci_secrets, sm_secrets (pre-split by destination for display)
    """
    catalog = {}
    for name, info in load_registry().items():
        copier = _load_copier_yml(info)
        meta = copier.get("_dwe_hub", {})
        # adapters.json keys take precedence; copier.yml _dwe_hub is supplemental
        required = info.get("required_secrets") or meta.get("required_secrets", [])
        optional = info.get("optional_secrets") or meta.get("optional_secrets", [])
        catalog[name] = {
            "name": name,
            "hub_name": info.get("hub_name") or meta.get("hub_name", name),
            "url": info.get("url", ""),
            "path": info.get("path", ""),
            "type": info.get("type", "git"),
            "description": info.get("description") or meta.get("description", ""),
            "display_name": info.get("display_name") or meta.get("display_name", name.replace("_", " ").title()),
            "icon": info.get("icon") or meta.get("icon", "box"),
            "git_providers": info.get("git_providers") or meta.get("git_providers", []),
            "cloud_providers": info.get("cloud_providers") or meta.get("cloud_providers", []),
            "services": info.get("services") or meta.get("services", []),
            "ci_templates": info.get("ci_templates") or meta.get("ci_templates", {}),
            "required_secrets": required,
            "optional_secrets": optional,
            # Pre-split by destination so consumers don't need to know about the field
            "ci_secrets": _filter_by_dest(required, "ci"),
            "sm_required_secrets": _filter_by_dest(required, "secrets_manager"),
            "sm_optional_secrets": _filter_by_dest(optional, "secrets_manager"),
        }
    return catalog
