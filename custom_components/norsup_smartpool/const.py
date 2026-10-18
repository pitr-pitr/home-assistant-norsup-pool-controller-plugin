"""Constants for the Norsup Smartpool integration."""

DOMAIN = "norsup_smartpool"

CONF_API_KEY = "api_key"
CONF_POOL_ID = "pool_id"
CONF_BASE_URL = "base_url"
CONF_OAUTH_BASE_URL = "oauth_base_url"
CONF_AUTH_TYPE = "auth_type"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

AUTH_TYPE_API_KEY = "api_key"
AUTH_TYPE_PORTAL = "portal"

DEFAULT_OAUTH_BASE_URL = "https://oauth.smartpoolconnect.eu"
# When true in config entry options, exposes a disabled-by-default diagnostics sensor.
CONF_ENABLE_DIAGNOSTICS = "enable_diagnostics"

DEFAULT_BASE_URL = "https://www.smartpoolconnect.eu"
DEFAULT_API_BASE_URL = "https://api.smartpoolconnect.eu"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 15

CONF_API_BASE_URL = "api_base_url"

API_LIVE_STATUS = "/api/live-status/{pool_id}"
API_POOL_STATUS = "/api/pool-status/{pool_id}"
API_POOL_DATA = "/pool.data"
API_REST_POOLS = "/pool"
API_REST_POOL = "/pool/{pool_id}"
API_REST_V3_ANALOG = "/pool/{pool_id}/v3/analoge_data"
API_POOL_FILTER_DATA = "/pool/{pool_id}/filter.data"
