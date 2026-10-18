# Installation and credentials

This guide explains how to install the integration, obtain credentials for **Smart Pool Connect** (Norsup), and configure Home Assistant.

**Portal:** [https://www.smartpoolconnect.eu](https://www.smartpoolconnect.eu)  
**OAuth login:** [https://oauth.smartpoolconnect.eu](https://oauth.smartpoolconnect.eu)

---

## What you need before setup

| Item | Required at setup? | Notes |
|------|------------------|--------|
| **Smart Pool Connect account** | Yes | Email and password for the owner portal. |
| **API key** (or bearer token) | Yes | Entered in the Home Assistant config flow. See [Obtaining an API key](#obtaining-an-api-key). |
| **Pool ID (UUID)** | Yes | Runtime identifier for your pool in the cloud API. |
| **Controller MAC address** | No (for HA) | Used **once** when you **claim** the pool in the portal; not entered in this integration. |
| **On-device API key on the NorsupOne box** | No | Installer provisioning key on the physical controller is **not** the same as the cloud API credential. |

You configure **one Home Assistant config entry per pool**. Multiple pools need multiple entries (they may share the same account-scoped API key if Norsup issues keys per account).

---

## Obtaining an API key

Norsup’s public manuals describe the **owner portal** (login, pool claim, MAC address). For third-party apps, Smart Pool Connect issues **SPC REST API keys** (they start with `spc_`). Those keys authenticate against the REST host `https://api.smartpoolconnect.eu` with the `X-API-Key` header — **not** against `/api/live-status/…` on the owner portal (that path expects a browser session after OAuth login).

1. **Sign in** to [Smart Pool Connect](https://www.smartpoolconnect.eu) with your pool owner account (legacy “Smart Pool Control” accounts use the same credentials on the OAuth host after the 2025 portal migration).
2. **Claim your pool** if you have not already: follow Norsup’s in-portal steps using the **MAC address** shown on your NorsupOne display. This links the controller to your account.
3. **Obtain the API key:**
   - If your portal has **Settings**, **Integrations**, **API**, or **Developer** section with an API key or access token, create or copy that value. That is what you paste into Home Assistant as **API key**.
   - If you do not see an API key option, use **Smart Pool Connect account (email & password)** in the config flow instead — that path uses OAuth and the portal live-status API.
4. **Do not** use the small API key printed on the NorsupOne enclosure for installer pairing unless Norsup explicitly documents it for cloud API access (it is usually for on-site provisioning only).

Store the key only in Home Assistant (config entry). Do not commit it to git or post it in issues.

---

## Finding your Pool ID (UUID)

The **Pool ID** is a UUID (for example `a1b2c3d4-e5f6-7890-abcd-ef1234567890`).

1. Log in to [Smart Pool Connect](https://www.smartpoolconnect.eu).
2. Open **Pools** and select your pool.
3. Look at the browser address bar. The path contains the pool UUID, for example:
   - `https://www.smartpoolconnect.eu/pool/<POOL_UUID>/filter`
   - or similar routes under `/pool/<POOL_UUID>/…`

Copy the full UUID into the config flow field **Pool ID (UUID)**.

---

## Configure in Home Assistant

1. **Settings** → **Devices & services** → **Add integration**.
2. Search for **Norsup Smartpool**.
3. Choose **Smart Pool Connect account (email & password)** — this is what the website and mobile app use. Session cookies authenticate API calls; you do **not** need a separate bearer token for most accounts.
4. Enter your **email** and **password** (same as [smartpoolconnect.eu](https://www.smartpoolconnect.eu)).
5. **Pool ID (UUID)** is optional when you have a single pool; the integration discovers it from your account. If you have multiple pools, pick one in the next step.
6. **API base URL** — leave default unless Norsup instructed a different host.

**API key:** choose **SPC API key** and paste your `spc_…` key from the portal. **Pool ID is optional** — the integration lists pools from `GET https://api.smartpoolconnect.eu/pool` and picks the only pool automatically. A 36-character UUID from the portal URL is the **pool ID**, not the API key.

After setup, entities appear under a single device (water temperature, pH, ORP, pump speed, pump running, cloud connectivity, and related sensors). **SPC API key** setups read the full module tree from `GET https://api.smartpoolconnect.eu/pool/{pool_id}` (pH, chlorine/ORP, filter pump speed, targets). **Portal login** also polls `filter.data` for pump speed when live-status omits it. Optional entities (ambient temperature, free chlorine, pump current, targets) are disabled by default until you enable them under the device. Optional diagnostics are available in the integration **Options** (requires reload).

### Pool Health Lovelace card

The integration serves a **Pool Health** dashboard card that visualizes chemistry from your **pH** and **ORP** entities (ring gauges and an overall status badge).

1. **Restart** Home Assistant after installing or updating the integration (the card is registered on load).
2. **Settings** → **Dashboards** → **Resources** → **Add resource**:
   - **URL:** `/norsup_smartpool/pool-health-card.js`
   - **Resource type:** JavaScript module
3. Open your dashboard → **Edit** → **Add card** → **Manual** (or YAML mode) and use:

```yaml
type: custom:norsup-pool-health-card
title: Pool health
ph_entity: sensor.YOUR_PH_ENTITY
orp_entity: sensor.YOUR_ORP_ENTITY
# Optional — show dosing targets on the ring (green band + tick):
ph_target_entity: sensor.YOUR_PH_TARGET_ENTITY
orp_target_entity: sensor.YOUR_ORP_TARGET_ENTITY
# If the API does not expose targets, set them manually instead:
# ph_target: 7.2
# orp_target: 700
```

Replace the entity IDs with the **pH** and **ORP** sensors on your Norsup device (**Settings** → **Devices & services** → your pool → **Entities**). In the card picker you can also search for **Norsup Pool Health** after the resource is loaded.

**Targets:** enable the **pH target** and **ORP target** sensors on your Norsup device when the cloud API returns them, then point `ph_target_entity` / `orp_target_entity` at those entities. The card draws a green target band and tick on each gauge and scores “Ideal / OK” relative to that target. If targets are missing from the API, omit the entity IDs and set `ph_target` / `orp_target` numbers in YAML instead.

Optional tuning: `ph_min` / `ph_max` (default 6.8–8.0) and `orp_min` / `orp_max` (default 400–850) adjust the gauge scale; `ph_target_tolerance` (default `0.2`) and `orp_target_tolerance` (default `50`) set the width of the green target band in pH / mV.

To **rotate credentials**, open the integration → **Configure** → update your portal password or API key; the new value is validated before it replaces the stored secret.

#### Pool Health card URL returns 404

A **404** on `/norsup_smartpool/pool-health-card.js` means Home Assistant has **not registered** the static route yet. HA does **not** serve files from `custom_components/` automatically.

1. Confirm the file is at **`custom_components/norsup_smartpool/www/pool-health-card.js`** (inside `www/`, not the integration root).
2. Confirm **`frontend.py`** exists next to `__init__.py` and that **`__init__.py`** calls `async_register_frontend` from `async_setup` (and on config entry setup).
3. **Update via HACS** (or copy the full `norsup_smartpool` folder), then perform a **full Home Assistant restart** — reloading only the integration is not enough after installing the card for the first time.
4. Ensure the **Norsup Smartpool** integration is installed and has loaded at least once (manifest **0.1.4+** for the Pool Health card).
5. In a browser while logged into HA, open `/norsup_smartpool/pool-health-card.js` — you should see JavaScript, not an HTML 404 page.

---

## Troubleshooting

### HACS: “No manifest.json file found”

When adding this repo under **Custom repositories** with category **Integration**, HACS looks for `custom_components/<domain>/manifest.json`. This project uses `custom_components/norsup_smartpool/manifest.json`.

If HACS reports that no `manifest.json` was found:

1. Confirm the repository URL is exactly `https://github.com/pitr-pitr/home-assistant-norsup-pool-controller-plugin` (no typo or truncated path).
2. Choose category **Integration**, not Plugin or Theme.
3. Ensure `hacs.json` on the default branch does **not** set `"content_in_root": true` (that mode expects `manifest.json` at the repository root, which this integration does not use). Pull the latest `main` from GitHub after updating the repo.
4. After a successful add, open **HACS** → **Integrations**, search **Norsup Smartpool**, install, then restart Home Assistant.

### HACS shows a generic “Create a plugin…” description

HACS does **not** read `hacs.json` or `manifest.json` for the one-line summary in the integration list. It shows the **GitHub repository description** from [github.com/pitr-pitr/home-assistant-norsup-pool-controller-plugin](https://github.com/pitr-pitr/home-assistant-norsup-pool-controller-plugin).

This repo stores the intended HACS blurb in [`.github/repository-description`](.github/repository-description). Pushing that file to `main` runs the **Sync repository metadata** workflow (or trigger it manually under **Actions**) so GitHub’s description updates. After that, use **HACS** → **Integrations** → **⋮** → **Update** (or remove and re-add the custom repository) to refresh the cached text.

The longer install text in HACS detail view comes from [`info.md`](info.md) at the repository root.

### Invalid API key or pool ID

Symptoms: Config flow error *Invalid API key or pool ID*, or entities stay unavailable after setup.

Checks:

1. Prefer **portal login** (email/password) instead of API key unless Norsup gave you a bearer token.
2. **Pool ID** matches the UUID in the portal URL exactly (including hyphens) when you enter it manually.
3. **API key** has no leading or trailing spaces; do not paste your pool UUID into the API key field.
4. The pool is **claimed** to your account and visible in the portal.
5. Your Norsup account can open the pool in a browser while you test (confirms cloud access).
6. Re-enter credentials via **Configure** on the integration (options flow).

If API key mode fails, run `python scripts/debug_auth.py --verbose` and confirm `GET https://api.smartpoolconnect.eu/pool` returns HTTP 200 with `X-API-Key`. HTTP 401 on `www.smartpoolconnect.eu/api/live-status/…` is expected for API keys — use portal login for that host instead.

### Test credentials in your local Python environment

Before changing Home Assistant, run the same **REST `/pool`** check the API-key config flow uses. From a clone of this repository (workspace root):

```bash
cd /path/to/this/repo

python -m pip install -r requirements-dev.txt   # or: pip install aiohttp

export NORSUP_POOL_ID='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
export NORSUP_API_KEY='your-secret'
# optional; default is https://www.smartpoolconnect.eu
# export NORSUP_BASE_URL='https://www.smartpoolconnect.eu'

python scripts/debug_auth.py

# Recommended when Bearer / X-Api-Key return 401:
export NORSUP_EMAIL='you@example.com'
export NORSUP_PASSWORD='your-portal-password'
python scripts/debug_auth.py --portal
python scripts/debug_auth.py --portal --verbose --insecure
```

- **Exit 0** — credentials work; HA setup should accept the same pool ID and key (or portal login).
- **Exit 1** — authentication rejected (same as HA `invalid_auth`). Try `--portal` with your smartpoolconnect.eu password instead of an API key.
- **Exit 2** — network or server error (not an invalid key).

Add `--verbose` to print HTTP status for `X-API-Key` on the REST API and (for comparison) legacy portal live-status probes. The script never prints your API key. **Pool ID is optional** when your key has access to a single pool.

If the script fails with an SSL or certificate error (common on macOS with the python.org installer before CA bundles are installed), add **`--insecure`** for a **local-only** check that skips TLS verification. Home Assistant still verifies certificates; fix your Python CA store for production use (`Install Certificates.command` in the Python folder, or `pip install certifi` and follow your OS docs).

You can pass flags instead of environment variables: `python scripts/debug_auth.py --pool-id … --api-key …`.

After a **successful** auth check, the script (by default) calls every Smart Pool Connect endpoint the Home Assistant integration uses, prints the full JSON to the terminal, and writes the same payload to **`norsup_api_dump.json`** in the current directory. Use `--output /path/to/file.json` to choose another path. The file includes raw REST/portal responses plus a `normalized` block (the same fields the integration maps to entities). Redact the file before sharing — it can contain pool names and live readings. Use **`--auth-only`** for a quick credential check without the extra API round-trips or JSON file.

### Cloud outage or “cannot connect”

Symptoms: *Could not reach Smart Pool Connect*, `binary_sensor` cloud offline, or `UpdateFailed` in logs.

- Confirm [Smart Pool Connect](https://www.smartpoolconnect.eu) loads in a browser from the same network as Home Assistant.
- Check DNS and firewall rules (Home Assistant needs outbound HTTPS to `www.smartpoolconnect.eu`).
- Norsup maintenance or outages are outside this integration; wait and retry. The coordinator retries on a schedule; transient 502/503 responses do not clear your stored credentials.
- For critical local control during cloud loss, consider Norsup’s documented **local Modbus** options (separate from this cloud integration).

### Enable debug logging (without sharing secrets)

To troubleshoot parsing or update issues, enable debug logs **only on your instance**:

1. **Settings** → **System** → **Logs** → **Enable debug logging**, or add to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.norsup_smartpool: debug
```

2. Reproduce the issue, then **Settings** → **System** → **Logs** → **Download logs**.

Home Assistant’s download applies **redaction** to secrets in many cases. Still:

- **Do not** paste API keys, cookies, or `Authorization` headers into GitHub issues.
- Prefer attaching the **redacted** log file or a short excerpt with secrets removed.
- When filing issues, describe pool ID only as the first 8 characters if needed (for example `a1b2c3d4…`), not the full UUID, unless support explicitly needs it.

To turn debug off, remove the logger lines or disable debug logging and restart Home Assistant.

---

## Security

- API keys live **only** in the Home Assistant config entry (encrypted at rest by HA). They are **not** written to this repository.
- The integration does **not** log API keys at info level. Avoid setting global `homeassistant` or `aiohttp` trace logging in production unless you understand the risk.
- **Do not paste API keys in GitHub issues, forums, or chat.** Use redacted logs and describe errors in plain language.
- This is an **unofficial** community integration; review [ARCHITECTURE.md](ARCHITECTURE.md) for cloud dependency and limitations.
