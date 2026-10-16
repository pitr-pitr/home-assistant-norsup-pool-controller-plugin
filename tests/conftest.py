"""Pytest configuration for Norsup Smartpool tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest_plugins = ("pytest_homeassistant_custom_component",)


# Importing `norsup_smartpool` as a top-level package breaks HA's custom_components
# loader; tests must use `custom_components.norsup_smartpool` (see pytest.ini pythonpath).

