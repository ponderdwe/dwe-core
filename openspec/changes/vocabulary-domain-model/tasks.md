# Tasks: vocabulary-domain-model

## Phase 1: Spec and documentation

- [ ] Write `openspec/specs/dwe-vocabulary/spec.md` (the canonical spec, synced from this change)
- [ ] Update `openspec/config.yaml` context block with vocabulary definitions so all future AI-generated specs use correct terminology
- [ ] Audit existing specs (`adapter-dependencies`, `kg-client`, `kg-registration`, etc.) and replace any inconsistent terminology
- [ ] Update `dwe/adapters.json` comments / README to use "Adapter" consistently
- [ ] Update dwe-core `README.md` to use vocabulary definitions

## Phase 2: Code surface (CLI output)

- [ ] Ensure `dwe list-adapters` output header reads "DWE Adapter Catalog"
- [ ] Ensure CLI error messages use "adapter" not "component" or "service"
