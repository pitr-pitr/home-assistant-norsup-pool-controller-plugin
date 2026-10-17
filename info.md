# Norsup Smartpool

Home Assistant integration for **Norsup** pools using the **Smart Pool Connect** cloud API ([smartpoolconnect.eu](https://www.smartpoolconnect.eu)).

Poll water chemistry (pH, ORP), temperature, filter/pump state, and online status into Home Assistant. Sign in with the same email and password as the portal, or use an API key if Norsup issued one. Pool ID is optional — leave it empty to auto-discover pools on your account.

{% if not installed %}
## Installation

1. In HACS, add this repository as a **custom integration** repository (see [README](https://github.com/pitr-pitr/home-assistant-norsup-pool-controller-plugin/blob/main/README.md#hacs-recommended)).
2. Install **Norsup Smartpool** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration** and search for **Norsup Smartpool**.

Credentials and troubleshooting: [INSTALL.md](https://github.com/pitr-pitr/home-assistant-norsup-pool-controller-plugin/blob/main/INSTALL.md).
{% endif %}
