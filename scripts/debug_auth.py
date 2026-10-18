#!/usr/bin/env python3
"""Test Smart Pool Connect credentials outside Home Assistant.

Uses the same ``async_validate_api_key`` logic as the HA config flow. Exit 0 on
success; exit 1 on auth failure (same as HA ``invalid_auth``); exit 2 on other errors.

Environment variables (or CLI flags):
  NORSUP_API_KEY   SPC REST API key (spc_…; required for API key mode)
  NORSUP_POOL_ID   Optional pool UUID (auto-discovered when omitted)
  NORSUP_BASE_URL  Optional portal host; default https://www.smartpoolconnect.eu
  NORSUP_API_BASE_URL  Optional REST host; default https://api.smartpoolconnect.eu

Examples (from repository root):

  python -m pip install -r requirements-dev.txt
  export NORSUP_POOL_ID='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
  export NORSUP_API_KEY='your-secret'
  python scripts/debug_auth.py

  python scripts/debug_auth.py --verbose

  # macOS python.org builds may lack CA certs; local debug only:
  python scripts/debug_auth.py --insecure

  # After auth succeeds, fetch every endpoint and save JSON (default: norsup_api_dump.json):
  python scripts/debug_auth.py --insecure --output /tmp/norsup_dump.json

  # Auth check only (no extra API calls or JSON file):
  python scripts/debug_auth.py --auth-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import aiohttp

_REPO_ROOT = Path(__file__).resolve().parents[1]
_COMPONENTS = _REPO_ROOT / "custom_components"
if str(_COMPONENTS) not in sys.path:
    sys.path.insert(0, str(_COMPONENTS))

from norsup_smartpool.api import (  # noqa: E402
    NorsupApiClient,
    NorsupAuthError,
    NorsupConnectionError,
    NorsupPortalLoginError,
    NorsupTransientError,
    async_discover_pools,
    async_list_pools_for_api_key,
    async_portal_login,
)
from norsup_smartpool.const import (  # noqa: E402
    API_LIVE_STATUS,
    API_REST_POOLS,
    AUTH_TYPE_PORTAL,
    DEFAULT_API_BASE_URL,
    DEFAULT_BASE_URL,
    DEFAULT_OAUTH_BASE_URL,
)

DEFAULT_DUMP_FILE = "norsup_api_dump.json"

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _mask_pool_id(pool_id: str) -> str:
    if len(pool_id) <= 12:
        return pool_id[:4] + "…"
    return f"{pool_id[:8]}…{pool_id[-4:]}"


def _snippet(text: str, limit: int = 200) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _rest_pools_url(api_base_url: str) -> str:
    return f"{api_base_url.rstrip('/')}{API_REST_POOLS}"


def _live_status_url(base_url: str, pool_id: str) -> str:
    path = API_LIVE_STATUS.format(pool_id=pool_id)
    return f"{base_url.rstrip('/')}{path}"


async def _probe_auth_modes(
    session: aiohttp.ClientSession,
    pool_id: str,
    api_key: str,
    base_url: str,
    api_base_url: str,
) -> None:
    rest_url = _rest_pools_url(api_base_url)
    print(f"GET {rest_url}")
    try:
        timeout = aiohttp.ClientTimeout(total=25)
        async with session.get(
            rest_url,
            headers={"X-API-Key": api_key},
            timeout=timeout,
        ) as resp:
            body = await resp.text()
            print(f"  X-API-Key (REST /pool): HTTP {resp.status} — {_snippet(body)}")
    except aiohttp.ClientError as err:
        print(f"  X-API-Key (REST /pool): connection error — {err}")

    if pool_id:
        url = _live_status_url(base_url, pool_id)
        print(f"GET {url} (portal live-status — usually needs OAuth session, not API key)")
        variants = (
            ("Authorization: Bearer", {"Authorization": f"Bearer {api_key}"}),
            ("X-Api-Key", {"X-Api-Key": api_key}),
        )
        for label, headers in variants:
            try:
                timeout = aiohttp.ClientTimeout(total=25)
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    body = await resp.text()
                    print(f"  {label}: HTTP {resp.status} — {_snippet(body)}")
            except aiohttp.ClientError as err:
                print(f"  {label}: connection error — {err}")


def _client_session(insecure: bool) -> aiohttp.ClientSession:
    if insecure:
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))
    return aiohttp.ClientSession()


def _emit_api_snapshot(snapshot: dict[str, Any], output_path: Path) -> None:
    """Print and persist the full API debug snapshot."""
    text = json.dumps(snapshot, indent=2, sort_keys=True, default=str)
    print()
    print("Full API snapshot (all endpoint payloads):")
    print(text)
    output_path.write_text(f"{text}\n", encoding="utf-8")
    print()
    print(f"Wrote API snapshot to {output_path.resolve()}")


async def _dump_api_snapshot(
    client: NorsupApiClient,
    output_path: Path,
) -> None:
    snapshot = await client.async_collect_debug_snapshot()
    _emit_api_snapshot(snapshot, output_path)


def _warn_api_key_shape(api_key: str) -> None:
    if _UUID_RE.match(api_key):
        print(
            "  NOTE: This value looks like a pool UUID, not an SPC API key (spc_…)."
        )
    elif not api_key.startswith("spc_"):
        print(
            "  NOTE: SPC REST API keys usually start with spc_. "
            "If auth fails, confirm you copied the API key from the portal, not the pool URL."
        )


async def _run_portal(
    pool_id: str,
    email: str,
    password: str,
    base_url: str,
    *,
    insecure: bool,
    auth_only: bool,
    output_path: Path,
) -> int:
    print("Norsup Smartpool — portal login check")
    print(f"  base_url: {base_url}")
    print(f"  email:    {email}")
    print(f"  pool_id:  {_mask_pool_id(pool_id) if pool_id else '(auto-discover)'}")
    if insecure:
        print("  WARNING: TLS verification disabled (--insecure) — local debug only.")

    async with _client_session(insecure) as session:
        try:
            await async_portal_login(
                session,
                email,
                password,
                base_url=base_url,
                oauth_base_url=DEFAULT_OAUTH_BASE_URL,
            )
        except NorsupPortalLoginError as exc:
            print("FAIL: portal login rejected.")
            print(f"  detail: {exc}")
            return 1

        if not pool_id:
            pools = await async_discover_pools(session, base_url)
            if not pools:
                print("FAIL: logged in but no pools found on this account.")
                return 1
            print("  pools on account:")
            for pool in pools:
                print(f"    - {pool.name}: {pool.pool_id}")
            if len(pools) == 1:
                pool_id = pools[0].pool_id
                print(f"  using sole pool: {_mask_pool_id(pool_id)}")
            else:
                print("  pass --pool-id to choose one pool for live-status validation.")
                return 0

        client = NorsupApiClient(
            session,
            pool_id,
            api_key=None,
            base_url=base_url,
            username=email,
            password=password,
            oauth_base_url=DEFAULT_OAUTH_BASE_URL,
            auth_type=AUTH_TYPE_PORTAL,
        )
        try:
            payload = await client.async_validate_api_key()
        except NorsupAuthError as exc:
            print("FAIL: live-status rejected after portal login.")
            print(f"  detail: {exc}")
            return 1
        except NorsupConnectionError as exc:
            print("FAIL: could not reach Smart Pool Connect.")
            print(f"  detail: {exc}")
            return 2

        print("OK: portal session + live-status succeeded.")
        if isinstance(payload, dict) and payload:
            print("  response keys:", ", ".join(sorted(payload.keys())))
        if not auth_only:
            await _dump_api_snapshot(client, output_path)
    return 0


async def _run(
    pool_id: str,
    api_key: str,
    base_url: str,
    api_base_url: str,
    *,
    verbose: bool,
    insecure: bool,
    auth_only: bool,
    output_path: Path,
) -> int:
    print("Norsup Smartpool — local API key check (REST)")
    print(f"  api_base_url: {api_base_url}")
    print(f"  base_url:     {base_url}")
    print(
        f"  pool_id:      {_mask_pool_id(pool_id) if pool_id else '(auto-discover)'}",
    )
    print(f"  api_key:      len={len(api_key)} (value not printed)")
    _warn_api_key_shape(api_key)
    if insecure:
        print("  WARNING: TLS verification disabled (--insecure) — local debug only.")

    async with _client_session(insecure) as session:
        if verbose:
            print()
            print("Verbose: probing REST /pool and (if pool id set) portal live-status:")
            await _probe_auth_modes(
                session, pool_id, api_key, base_url, api_base_url
            )
            print()

        if not pool_id:
            try:
                pools = await async_list_pools_for_api_key(
                    session, api_key, api_base_url=api_base_url
                )
            except NorsupAuthError as exc:
                print("FAIL: API key rejected on REST /pool.")
                print(f"  detail: {exc}")
                return 1
            except NorsupConnectionError as exc:
                print("FAIL: could not reach Smart Pool Connect REST API.")
                print(f"  detail: {exc}")
                return 2
            if not pools:
                print("FAIL: API key accepted but no pools returned.")
                return 1
            print("  pools for this API key:")
            for pid, name in pools:
                print(f"    - {name}: {pid}")
            if len(pools) == 1:
                pool_id = pools[0][0]
                print(f"  using sole pool: {_mask_pool_id(pool_id)}")
            else:
                print("  pass --pool-id to validate a specific pool.")
                return 0

        client = NorsupApiClient(
            session,
            pool_id,
            api_key,
            base_url,
            api_base_url=api_base_url,
        )
        try:
            payload = await client.async_validate_api_key()
        except NorsupAuthError as exc:
            print("FAIL: authentication rejected (Home Assistant would show invalid_auth).")
            print(f"  detail: {exc}")
            print(
                "  hint: API keys use https://api.smartpoolconnect.eu with X-API-Key. "
                "For email/password use: python scripts/debug_auth.py --portal …"
            )
            return 1
        except NorsupConnectionError as exc:
            print("FAIL: could not reach Smart Pool Connect.")
            print(f"  detail: {exc}")
            return 2
        except NorsupTransientError as exc:
            print("FAIL: cloud API temporarily unavailable.")
            print(f"  detail: {exc}")
            return 2

        print("OK: SPC API key accepted (REST /pool).")
        if isinstance(payload, dict) and payload:
            print("  response keys:", ", ".join(sorted(payload.keys())))
        if not auth_only:
            await _dump_api_snapshot(client, output_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Norsup Smart Pool Connect API credentials locally."
    )
    parser.add_argument(
        "--pool-id",
        default=os.environ.get("NORSUP_POOL_ID", "").strip(),
        help="Pool UUID (or set NORSUP_POOL_ID)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("NORSUP_API_KEY", "").strip(),
        help="API key / bearer token (or set NORSUP_API_KEY)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("NORSUP_BASE_URL", DEFAULT_BASE_URL).strip(),
        help=f"Portal host (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("NORSUP_API_BASE_URL", DEFAULT_API_BASE_URL).strip(),
        help=f"REST API host (default: {DEFAULT_API_BASE_URL})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print HTTP status for Bearer and X-Api-Key before the combined check",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification (local debug only; not used by Home Assistant)",
    )
    parser.add_argument(
        "--portal",
        action="store_true",
        help="Use Smart Pool Connect email/password (portal session) instead of API key",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("NORSUP_EMAIL", "").strip(),
        help="Portal email (or set NORSUP_EMAIL)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("NORSUP_PASSWORD", "").strip(),
        help="Portal password (or set NORSUP_PASSWORD)",
    )
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="Validate credentials only; skip full API dump and JSON file",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_DUMP_FILE,
        metavar="FILE",
        help=(
            f"Write full API snapshot JSON here after success "
            f"(default: {DEFAULT_DUMP_FILE})"
        ),
    )
    args = parser.parse_args(argv)
    output_path = Path(args.output).expanduser()

    if args.portal:
        if not args.email or not args.password:
            parser.error(
                "portal mode requires --email and --password (or NORSUP_EMAIL / NORSUP_PASSWORD)"
            )
        return asyncio.run(
            _run_portal(
                args.pool_id,
                args.email,
                args.password,
                args.base_url,
                insecure=args.insecure,
                auth_only=args.auth_only,
                output_path=output_path,
            )
        )

    if not args.api_key:
        parser.error("missing API key — set NORSUP_API_KEY or pass --api-key")

    return asyncio.run(
        _run(
            args.pool_id,
            args.api_key,
            args.base_url,
            args.api_base_url,
            verbose=args.verbose,
            insecure=args.insecure,
            auth_only=args.auth_only,
            output_path=output_path,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
