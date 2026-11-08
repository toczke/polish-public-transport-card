"""Tests for the MZK Wejherowo static GTFS provider."""

from types import SimpleNamespace

import pytest

from mzkzg_transport import provider_mzk


@pytest.mark.asyncio
async def test_fetch_uses_stop_name_from_gtfs(monkeypatch):
    class FakeGtfs:
        stops = {"1234": {"name": "Wejherowo Dworzec"}}

        def get_departures(self, stop_id, now):
            assert stop_id == "1234"
            return [{"route": "1", "estimated_time": now.isoformat()}]

    async def fake_get_gtfs(coord):
        return FakeGtfs()

    monkeypatch.setattr("mzkzg_transport.gtfs_provider.get_gtfs_data", fake_get_gtfs)
    coord = SimpleNamespace(stop_id="1234", stop_name="")

    result = await provider_mzk.fetch(coord)

    assert coord.stop_name == "Wejherowo Dworzec"
    assert result["provider"] == "mzk_wejherowo"
    assert result["stop_name"] == "Wejherowo Dworzec"
    assert result["departures"][0]["route"] == "1"


@pytest.mark.asyncio
async def test_fetch_keeps_custom_stop_name(monkeypatch):
    class FakeGtfs:
        stops = {}

        def get_departures(self, stop_id, now):
            return []

    async def fake_get_gtfs(coord):
        return FakeGtfs()

    monkeypatch.setattr("mzkzg_transport.gtfs_provider.get_gtfs_data", fake_get_gtfs)
    coord = SimpleNamespace(stop_id="999", stop_name="Mój przystanek")

    result = await provider_mzk.fetch(coord)

    assert result["stop_name"] == "Mój przystanek"
    assert result["departures"] == []
