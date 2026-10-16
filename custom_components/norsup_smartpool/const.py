"""Constants for the Norsup Smartpool integration."""

DOMAIN = "norsup_smartpool"

CONF_API_KEY = "api_key"
CONF_POOL_ID = "pool_id"
CONF_BASE_URL = "base_url"
CONF_SCAN_INTERVAL = "scan_interval"
# When true in config entry options, exposes a disabled-by-default diagnostics sensor.
CONF_ENABLE_DIAGNOSTICS = "enable_diagnostics"

DEFAULT_BASE_URL = "https://www.smartpoolconnect.eu"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 15

API_LIVE_STATUS = "/api/live-status/{pool_id}"
API_POOL_STATUS = "/api/pool-status/{pool_id}"
API_POOL_DATA = "/pool.data"
