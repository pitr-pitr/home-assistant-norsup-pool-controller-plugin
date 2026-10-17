# Norsup Smartpool — Home Assistant

Unofficial Home Assistant integration for **Norsup** pools using the **Smart Pool Connect** cloud API ([smartpoolconnect.eu](https://www.smartpoolconnect.eu)).

Poll water chemistry, temperature, pump status, and connectivity into Home Assistant with an API key and pool UUID.

| | |
|---|---|
| **Domain** | `norsup_smartpool` |
| **IoT class** | Cloud polling |
| **Documentation** | [INSTALL.md](INSTALL.md) (credentials, troubleshooting) |
| **Architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Install guide (web)** | Run the companion UI (`companion/` + `web/`) for HACS URL copy and API key checklist |

> **Disclaimer:** Not affiliated with Norsup. Cloud API behavior may change without notice.

### Companion install UI (optional)

A small web app documents HACS setup and API key requirements. Build and run:

```bash
pip install -r requirements-companion.txt
cd web && npm install && npm run build && cd ..
python3 -m uvicorn companion.server:app --host 127.0.0.1 --port 8044
```

Open `http://127.0.0.1:8044/` (API: `/v1/health`, `/v1/integration`). Use any free port ≥ 8001 if 8044 is taken.

---

## Prerequisites

- **Home Assistant** **2024.1.0** or newer (Core, Container, or supervised).
- A **Smart Pool Connect** account with at least one **claimed** pool.
- An **API key** (or bearer token) and **pool UUID** — see [INSTALL.md](INSTALL.md#obtaining-an-api-key).
- Outbound HTTPS from Home Assistant to `www.smartpoolconnect.eu`.

---

## Installation

### HACS (recommended)

1. Install [HACS](https://hacs.xyz/docs/setup/download) if you have not already.
2. **HACS** → **Integrations** → **⋮** (menu) → **Custom repositories**.
3. Add this repository:
   - **Repository:** `https://github.com/pitr-pitr/home-assistant-norsup-pool-controller-plugin`
   - **Category:** Integration
4. **Download** the integration from HACS (search **Norsup Smartpool**). The short line under the name in HACS is the **GitHub repository description** (kept in [`.github/repository-description`](.github/repository-description), synced on push to `main`); see [INSTALL.md — HACS description](INSTALL.md#hacs-shows-a-generic-create-a-plugin-description) if it still shows an old Loom placeholder.
5. If HACS shows *No manifest.json file found*, see [INSTALL.md — HACS troubleshooting](INSTALL.md#hacs-no-manifestjson-file-found) (usually `content_in_root` on an older `hacs.json` — use latest `main`).
6. **Restart** Home Assistant.
7. **Settings** → **Devices & services** → **Add integration** → **Norsup Smartpool**, then follow [INSTALL.md](INSTALL.md#configure-in-home-assistant).

### Manual install

1. Download the latest release zip from [GitHub Releases](https://github.com/pitr-pitr/home-assistant-norsup-pool-controller-plugin/releases) or clone this repository.
2. Copy the folder `custom_components/norsup_smartpool` into your Home Assistant configuration directory:

   ```text
   <config>/custom_components/norsup_smartpool/
   ```

   Example on Home Assistant OS: `/config/custom_components/norsup_smartpool/`.

3. **Restart** Home Assistant.
4. Add the integration under **Settings** → **Devices & services** (see [INSTALL.md](INSTALL.md)).

Directory layout after manual copy:

```text
config/
  configuration.yaml
  custom_components/
    norsup_smartpool/
      __init__.py
      manifest.json
      …
```

---

## Features

- Sensors: water temperature, pH, ORP, pump speed (when returned by the API).
- Binary sensors: pump running, cloud online.
- Config and options flows with API key validation against live-status.
- Options: poll interval, API key rotation, optional diagnostics sensor.

Writable controls are only exposed when the API supports them (no fake switches).

---

## Troubleshooting

See [INSTALL.md — Troubleshooting](INSTALL.md#troubleshooting) for invalid keys, cloud outages, and **debug logging without sharing secrets**.

To test your API key and pool UUID **outside Home Assistant**, use `scripts/debug_auth.py` — see [INSTALL.md — Test credentials locally](INSTALL.md#test-credentials-in-your-local-python-environment).

### Security

**Never paste your API key in GitHub issues or public forums.** Use Home Assistant’s **Download logs** (redacted) when asking for help. See [INSTALL.md — Security](INSTALL.md#security).

---

## Testing

Install dev dependencies, then run the full suite (config flow, API client, coordinator):

```bash
python -m pip install -r requirements-dev.txt
pytest tests/
```

CI enforces **≥80% line coverage** on `custom_components/norsup_smartpool/api/client` (see `.github/workflows/ci.yml`). Representative API payloads live under `tests/fixtures/` and use field names from [ARCHITECTURE.md](ARCHITECTURE.md) (`water_temperature`, `pump_status`, `ph`, `rx`, etc.).

## Development

```bash
python -m pip install -r requirements-dev.txt
ruff check .
pytest tests/
```

CI runs the same lint and test steps on every push and pull request to `main`. See [CONTRIBUTING.md](CONTRIBUTING.md) for releases, branch protection, and pull request guidelines.

---

## License

[MIT](LICENSE)
