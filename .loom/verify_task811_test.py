"""One-off verification for task 811 (not part of product test suite)."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import aiohttp
from aiohttp import web

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "norsup_smartpool"


def _load_api():
    import types

    pkg = types.ModuleType("norsup_smartpool")
    pkg.__path__ = [str(PKG)]  # type: ignore[attr-defined]
    sys.modules["norsup_smartpool"] = pkg

    for name in ("const", "api"):
        spec = importlib.util.spec_from_file_location(
            f"norsup_smartpool.{name}", PKG / f"{name}.py"
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[f"norsup_smartpool.{name}"] = mod
        spec.loader.exec_module(mod)
        setattr(pkg, name, mod)
    return pkg.api


_api = _load_api()
NorsupAuthError = _api.NorsupAuthError
async_validate_api_key = _api.async_validate_api_key

POOL_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


async def _run_api_tests() -> None:
    pool_id = "11111111-2222-3333-4444-555555555555"
    good_key = "secret-key"

    async def handler(request: web.Request) -> web.Response:
        auth = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-Api-Key", "")
        if auth == f"Bearer {good_key}" or api_key == good_key:
            return web.json_response({"online": True})
        return web.Response(status=401)

    app = web.Application()
    app.router.add_get(f"/api/live-status/{pool_id}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{port}"

    async with aiohttp.ClientSession() as session:
        payload = await async_validate_api_key(session, pool_id, good_key, base)
        assert payload == {"online": True}

        try:
            await async_validate_api_key(session, pool_id, "bad", base)
        except NorsupAuthError:
            pass
        else:
            raise AssertionError("expected NorsupAuthError for bad key")

    await runner.cleanup()


def _run_manifest_checks() -> None:
    manifest = json.loads(
        (ROOT / "custom_components" / "norsup_smartpool" / "manifest.json").read_text()
    )
    assert manifest["domain"] == "norsup_smartpool"
    assert manifest.get("config_flow") is True
    assert manifest.get("iot_class") == "cloud_polling"
    assert manifest.get("version")


def _run_pool_id_pattern() -> None:
    assert POOL_ID_PATTERN.match("11111111-2222-3333-4444-555555555555")
    assert not POOL_ID_PATTERN.match("not-a-uuid")


def main() -> None:
    _run_manifest_checks()
    _run_pool_id_pattern()
    asyncio.run(_run_api_tests())
    print("task 811 verification: OK")


if __name__ == "__main__":
    main()
