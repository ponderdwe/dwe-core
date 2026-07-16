## Context

`dwe-core` ships an `adapters.json` registry that maps adapter names to their source URLs and metadata. `registry.py:get_adapter_catalog()` was already built to fetch each adapter's `copier.yml` from GitHub and merge its `_dwe_hub` section — but adapters.json was winning over copier.yml, so the metadata was effectively duplicated. Each adapter repo already owned the canonical definition of its metadata; adapters.json was a stale copy.

## Goals / Non-Goals

**Goals:**
- `adapters.json` is a pointer file only: `{url, type}` per adapter
- Each adapter repo's `copier.yml` `_dwe_hub` section is the single source of truth for all display and deployment metadata
- No behavioral change to `get_adapter_catalog()` — the merge logic was already correct

**Non-Goals:**
- Caching or offline resilience for copier.yml fetches (existing timeout/fallback behavior is sufficient)
- Supporting non-GitHub adapter repos (existing `_github_raw_url` logic is unchanged)
- Changing the shape of the catalog dict returned to consumers

## Decisions

**Decision: Keep `type: git` in adapters.json alongside `url`**
Rationale: `type` describes the kind of source (git repo vs. future local/registry types), not metadata about the adapter itself. It belongs in the pointer file so the registry knows *how* to fetch the adapter before it can read copier.yml.

**Decision: `description` lives in `_dwe_hub` in copier.yml, not in adapters.json**
Rationale: Description is intrinsic to the adapter. The adapter team owns it. Keeping it in the adapter repo removes a coordination burden from dwe-core maintainers.

**Decision: No code changes to `registry.py`**
`get_adapter_catalog()` already falls through to `meta.get(field)` when `info.get(field)` is falsy. Removing the fields from adapters.json is sufficient to make copier.yml take over — no precedence logic needs to change.

## Risks / Trade-offs

- **[Risk] copier.yml fetch fails at runtime** → `_load_copier_yml` already returns `{}` on any exception; `get_adapter_catalog()` falls back to empty strings/lists. The adapter still appears in the catalog with its URL, just with blank metadata. Acceptable degradation.
- **[Risk] copier.yml `_dwe_hub` drifts in adapter repos** → This is the intended model: adapter maintainers own their metadata. dwe-core no longer needs to track it.
- **[Trade-off] Cold catalog load now requires a network round-trip per adapter** → Already the case when `url` is set and `path` is absent; no regression.

## Migration Plan

1. Update `_dwe_hub` in each adapter repo's `copier.yml` to include all fields previously only in adapters.json
2. Slim `adapters.json` to `{url, type}` — no code changes
3. dwe-hub requires no changes; it reads exclusively via `get_adapter_catalog()`
