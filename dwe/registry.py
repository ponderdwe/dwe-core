import json
import os
import urllib.request
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

REGISTRY_PATH = Path(__file__).parent.parent / "adapters.json"


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


def get_adapter_catalog() -> dict:
    """
    Return full adapter metadata dict keyed by adapter name (as in adapters.json).

    Each entry contains:
      name, hub_name, url, path, type, description,
      display_name, icon, required_secrets, optional_secrets
    """
    catalog = {}
    for name, info in load_registry().items():
        copier = _load_copier_yml(info)
        meta = copier.get("_dwe_hub", {})
        catalog[name] = {
            "name": name,
            "hub_name": meta.get("hub_name", name),
            "url": info.get("url", ""),
            "path": info.get("path", ""),
            "type": info.get("type", "git"),
            "description": info.get("description", meta.get("description", "")),
            "display_name": meta.get("display_name", name.replace("_", " ").title()),
            "icon": meta.get("icon", "box"),
            "required_secrets": meta.get("required_secrets", []),
            "optional_secrets": meta.get("optional_secrets", []),
        }
    return catalog
