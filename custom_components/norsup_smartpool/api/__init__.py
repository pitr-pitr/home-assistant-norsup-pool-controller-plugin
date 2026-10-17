"""Smart Pool Connect HTTP client package."""

from .client import (
    NorsupApiClient,
    NorsupAuthError,
    NorsupConnectionError,
    NorsupTransientError,
    async_list_pools_for_api_key,
    async_validate_api_key,
    async_validate_portal_credentials,
)
from .models import NorsupPoolData
from .oauth_session import (
    DiscoveredPool,
    NorsupPortalLoginError,
    async_discover_pools,
    async_portal_login,
    parse_pools_from_pool_data,
)

__all__ = [
    "DiscoveredPool",
    "NorsupApiClient",
    "NorsupAuthError",
    "NorsupConnectionError",
    "NorsupPoolData",
    "NorsupPortalLoginError",
    "NorsupTransientError",
    "async_discover_pools",
    "async_list_pools_for_api_key",
    "async_portal_login",
    "async_validate_api_key",
    "async_validate_portal_credentials",
    "parse_pools_from_pool_data",
]
