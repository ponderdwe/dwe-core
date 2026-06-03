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
