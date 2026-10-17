# Product QA checklist — Norsup Smartpool (Home Assistant)

**Task:** Install path, config UX, and entity usability  
**Date:** 2026-10-16  
**Reviewer:** Loom Product QA (automated review + pytest; no live Home Assistant instance in CI workspace)  
**Integration version:** 0.1.1 (`manifest.json`)

## Environment

| Item | Value |
|------|--------|
| HA version targeted | ≥ 2024.1.0 per `hacs.json` / README |
| Live HA clean-room install | Not run (no HA Core/Container in QA workspace) |
| Automated verification | `python3 -m pytest tests/` — **17 passed** |

## Core flows

| Check | Result | Evidence |
|-------|--------|----------|
| **HACS install path** | **Pass** | `hacs.json` valid (no `content_in_root`; country; min HA). README + companion UI use repo `pitr-pitr/home-assistant-norsup-pool-controller-plugin`. Integration category; manifest at `custom_components/norsup_smartpool/manifest.json` (fixes HACS “No manifest.json” when `content_in_root` was true). |
| **Manual install path** | **Pass** | README manual section: copy `custom_components/norsup_smartpool` to `<config>/custom_components/`, restart, add integration. `dist/norsup_smartpool-0.1.0.zip` present for release-style manual download. INSTALL.md aligns with config flow fields. |
| **Invalid API key / pool ID** | **Pass** | `tests/test_config_flow.py`: malformed UUID → `invalid_pool_id` without API call; HTTP 401 → `invalid_auth`, no config entry. `translations/en.json` (+ `nl.json`, `de.json`) supply config-flow labels and errors so HA does not show raw keys like `invalid_auth`. Options flow keeps previous key on failed rotation (`test_options_flow_invalid_key`). |
| **Successful entity creation** | **Pass (code + tests)** | Config flow success test creates entry with pool unique_id. Platforms `sensor` + `binary_sensor` register temperature, pH, ORP, pump speed, pump running, cloud online. Live entity UI not exercised without HA; behavior covered by integration scaffold and fixtures. |

## Acceptance criteria

| Criterion | Result | Notes |
|-----------|--------|-------|
| Config labels mention API key + INSTALL.md for obtaining it | **Pass** | `strings.json`: field label “API key”; step description and `data_description.api_key` reference INSTALL.md → Obtaining an API key. README links `INSTALL.md#obtaining-an-api-key`. |
| One device per pool, recognizable name | **Pass** | `entity.py` `DeviceInfo`: `identifiers={(DOMAIN, pool_id)}`, default name **Norsup Smartpool** (portal name override when API returns it), manufacturer Norsup, model Smart Pool Connect. `integration_type`: hub in manifest. |
| No secrets in default info-level logs | **Pass** | `test_coordinator.py` asserts API key not in logs on auth failure and repeated warnings. Client/coordinator log paths at info/warning use pool_id only, not credentials. |
| Branding/docs specific to Norsup pool owners | **Pass** | INSTALL.md references Smart Pool Connect portal, MAC claim, pool UUID in URL, unofficial disclaimer in README. No generic “AI template” integration copy. |
| Blocking issues filed or fixed | **Pass** | Minor UX gap (config copy only said “see INSTALL.md”) fixed in `strings.json` during this QA pass. No other blockers. |

## Product-family notes (global / HA integration)

- No separate web UI: Loom “Made with Loom” and What’s new popup rules **N/A** for this Home Assistant custom integration.
- Runnable product for QA = integration package + docs + tests; not a Loom-hosted frontend/backend.

## Sign-off

**Status: Pass** — Install documentation, config UX, device grouping, error strings, and logging hygiene meet the task acceptance criteria. Recommend optional follow-up: smoke test on a real Home Assistant instance (HACS + one live pool) before first public release.

Signed off: Product QA, 2026-10-16.
