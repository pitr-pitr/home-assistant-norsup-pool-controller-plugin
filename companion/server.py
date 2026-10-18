"""Companion install guide API and static UI for the Norsup Smartpool HA integration."""

from __future__ import annotations

import asyncio
import json
import ssl
from pathlib import Path
from urllib import error, request
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "custom_components/norsup_smartpool/manifest.json"
DIST = ROOT / "web/dist"
REPO = "https://github.com/pitr-pitr/home-assistant-norsup-pool-controller-plugin"

app = FastAPI(title="Norsup Smartpool companion", version="0.1.0")


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


DEFAULT_SCAN_TARGET = "https://api.smartpoolconnect.eu"


class ScanTargetRequest(BaseModel):
    target: str = Field(
        default=DEFAULT_SCAN_TARGET,
        description="Smart Pool Connect REST API base URL or host to probe",
    )


def _probe_target_url(target: str) -> dict[str, object]:
    """Reachability check for the REST API host (no credentials)."""
    raw = target.strip()
    if not raw:
        return {"ok": False, "error": "empty_target"}
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return {"ok": False, "error": "invalid_url", "target": raw}
    base = f"{parsed.scheme}://{parsed.netloc}"
    url = f"{base}/pool"
    context = ssl.create_default_context()
    req = request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=12, context=context) as resp:
            status = resp.status
    except error.HTTPError as exc:
        status = exc.code
    except error.URLError as exc:
        return {"ok": False, "error": "unreachable", "detail": str(exc.reason), "target": base}
    except TimeoutError:
        return {"ok": False, "error": "timeout", "target": base}
    # REST /pool without a key should reject auth, not disappear.
    reachable = status in (401, 403, 200)
    return {
        "ok": reachable,
        "target": base,
        "http_status": status,
        "hint": "reachable" if reachable else "unexpected_status",
    }


@app.post("/v1/scan")
async def scan_target(body: ScanTargetRequest) -> dict[str, object]:
    """Probe whether a Smart Pool Connect API host responds."""
    return await asyncio.to_thread(_probe_target_url, body.target)


@app.get("/v1/integration")
async def integration_info() -> dict:
    manifest = _manifest()
    return {
        "domain": manifest["domain"],
        "name": manifest["name"],
        "version": manifest["version"],
        "iot_class": manifest.get("iot_class"),
        "hacs": {
            "repository": REPO,
            "category": "integration",
            "path": f"custom_components/{manifest['domain']}/manifest.json",
        },
        "portal": "https://www.smartpoolconnect.eu",
        "docs": {
            "install": f"{REPO}/blob/main/INSTALL.md",
            "readme": f"{REPO}/blob/main/README.md",
        },
    }


@app.get("/", response_model=None)
async def spa_index():
    index = DIST / "index.html"
    if not index.is_file():
        return JSONResponse(
            {"error": "Companion UI not built. Run: cd web && npm ci && npm run build"},
            status_code=503,
        )
    return FileResponse(index)


if DIST.is_dir() and (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
