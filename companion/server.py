"""Companion install guide API and static UI for the Norsup Smartpool HA integration."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
