"""Lovelace Pool Health card assets."""

from pathlib import Path

CARD_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "norsup_smartpool"
    / "www"
    / "pool-health-card.js"
)


def test_pool_health_card_bundled() -> None:
    """Card script ships with the integration for Lovelace."""
    assert CARD_PATH.is_file()
    text = CARD_PATH.read_text(encoding="utf-8")
    assert "norsup-pool-health-card" in text
    assert "window.customCards" in text
