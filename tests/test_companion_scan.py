"""Companion API scan endpoint."""

from companion.server import _probe_target_url


def test_probe_target_rejects_empty() -> None:
    result = _probe_target_url("")
    assert result["ok"] is False
    assert result["error"] == "empty_target"


def test_probe_target_normalizes_host() -> None:
    result = _probe_target_url("not-a-valid-host-%%%")
    assert result["ok"] is False
