import json
from datetime import date
from pathlib import Path


STATE_FILE = "dwe-state.json"


def read_state(repo_path: str) -> dict:
    state_file = Path(repo_path) / STATE_FILE
    if not state_file.exists():
        raise FileNotFoundError(f"No {STATE_FILE} found at {repo_path}")
    return json.loads(state_file.read_text())


def write_state(
    repo_path: str,
    adapter_name: str,
    version: str,
    environments: list[str],
) -> None:
    state = {
        "dwe_version": "1.0.0",
        "adapter": {
            "name": adapter_name,
            "version": version,
            "last_update": date.today().isoformat(),
        },
        "environments": environments,
        "infrastructure": "pulumi",
    }
    (Path(repo_path) / STATE_FILE).write_text(json.dumps(state, indent=2))


def update_state_version(repo_path: str, new_version: str) -> dict:
    state = read_state(repo_path)
    state["adapter"]["version"] = new_version
    state["adapter"]["last_update"] = date.today().isoformat()
    (Path(repo_path) / STATE_FILE).write_text(json.dumps(state, indent=2))
    return state
