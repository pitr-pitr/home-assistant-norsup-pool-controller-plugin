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

Norsup’s public manuals describe the **owner portal** (login, pool claim, MAC address). They do **not** always document a separate “API key” page for third-party apps. This integration expects a **secret string** that Smart Pool Connect accepts on authenticated API calls (typically as `Authorization: Bearer …` or `X-Api-Key`).

1. **Sign in** to [Smart Pool Connect](https://www.smartpoolconnect.eu) with your pool owner account (legacy “Smart Pool Control” accounts use the same credentials on the OAuth host after the 2025 portal migration).
2. **Claim your pool** if you have not already: follow Norsup’s in-portal steps using the **MAC address** shown on your NorsupOne display. This links the controller to your account.
3. **Obtain the API key:**
   - If your portal has **Settings**, **Integrations**, **API**, or **Developer** section with an API key or access token, create or copy that value. That is what you paste into Home Assistant as **API key**.
   - If you do not see an API key option, check Norsup support or your installer for whether **personal access tokens** are available for Smart Pool Connect. Until Norsup publishes official third-party API documentation, some accounts may only have portal session login; this integration validates using bearer-style headers against the live-status API—use whatever long-lived token Norsup provides for API access.
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
3. Enter:
   - **API key** — from the section above.
   - **Pool ID (UUID)** — from the portal URL.
   - **API base URL** — leave default `https://www.smartpoolconnect.eu` unless Norsup instructed a different host.
4. Submit. The integration calls the cloud **live-status** endpoint to verify the key and pool ID before saving.

After setup, entities appear under a single device (water temperature, pH, ORP, pump status, cloud connectivity, and related sensors). Optional diagnostics are available in the integration **Options** (requires reload).

To **rotate the API key**, open the integration → **Configure** → update the key; the new value is validated before it replaces the stored secret.

---

## Troubleshooting

### Invalid API key or pool ID

Symptoms: Config flow error *Invalid API key or pool ID*, or entities stay unavailable after setup.

Checks:

1. **Pool ID** matches the UUID in the portal URL exactly (including hyphens).
2. **API key** has no leading or trailing spaces; re-copy from the portal.
3. The pool is **claimed** to your account and visible in the portal.
4. Your Norsup account can open the pool in a browser while you test (confirms cloud access).
5. Re-enter credentials via **Configure** on the integration (options flow).

If the key was revoked or expired in the portal, generate a new one and update Home Assistant.

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
