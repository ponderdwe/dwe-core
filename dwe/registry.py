import json
from pathlib import Path
from typing import Optional


REGISTRY_PATH = Path(__file__).parent.parent / "adapters.json"


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    return json.loads(REGISTRY_PATH.read_text())


def get_adapter(name: str) -> Optional[dict]:
    return load_registry().get(name)


def list_adapters() -> list[str]:
    return list(load_registry().keys())
