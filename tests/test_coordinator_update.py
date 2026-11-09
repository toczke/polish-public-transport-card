"""Coverage for coordinator update, sleep mode and provider dispatch."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from mzkzg_transport import (
    provider_gtfsrt,
    provider_kiedyprzyjedzie,
    provider_krakow,
    provider_lodz,
    provider_mzk,
    provider_plk,
    provider_time4bus,
    provider_zkm,
    provider_ztm,
)
from mzkzg_transport.const import (
    CONF_OFFLINE_ONLY,
    CONF_SLEEP_ENABLED,
    CONF_SLEEP_END,
    CONF_SLEEP_START,
    DOMAIN,
    PROVIDER_KRAKOW,
    PROVIDER_LODZ,
    PROVIDER_MZK,
    PROVIDER_PLK,
    PROVIDER_ZKM,
    PROVIDER_ZTM,
)
from mzkzg_transport.coordinator import PolishTransportCoordinator

FIXED_NOW = datetime(2026, 11, 9, 12, 0, 0)


def _coordinator(provider=PROVIDER_ZTM, options=None, data=None):
    hass = MagicMock()
    hass.data = {DOMAIN: {"_coordinators": {}}}
    hass.config.latitude = 54.35
    hass.config.longitude = 18.65
    coord = PolishTransportCoordinator(hass, "2230", provider, "Płocka 01")
    coord._options = options or {}
    coord.data = data
    return coord


def _departures():
    return {
        "stop_id": "2230",
        "stop_name": "Płocka 01",
        "provider": PROVIDER_ZTM,
        "departures": [
            {"route": "6", "headsign": "Jelitkowo", "theoretical_time": "2026-11-09T12:05:00+01:00"},
            {"route": "6", "headsign": "Jelitkowo", "theoretical_time": "2026-11-09T12:05:00+01:00", "realtime": True},
        ],
        "last_update": FIXED_NOW.isoformat(),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "module"),
    [
        (PROVIDER_ZTM, provider_ztm),
        (PROVIDER_MZK, provider_mzk),
        (PROVIDER_LODZ, provider_lodz),
        (PROVIDER_KRAKOW, provider_krakow),
        ("gtfsrt_lublin", provider_gtfsrt),
        (PROVIDER_PLK, provider_plk),
        ("time4bus_tczew", provider_time4bus),
        ("kiedyprzyjedzie_gryf", provider_kiedyprzyjedzie),
        (PROVIDER_ZKM, provider_zkm),
    ],
)
async def test_update_dispatches_to_provider_and_deduplicates(
    monkeypatch, provider, module
):
    calls = []

    async def fake_fetch(coord):
        calls.append(coord.provider)
        return _departures()

    monkeypatch.setattr(module, "fetch", fake_fetch)
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    coord = _coordinator(provider, {CONF_SLEEP_ENABLED: False})

    result = await coord._async_update_data()

    assert calls == [provider]
    assert len(result["departures"]) == 1
    assert result["departures"][0]["realtime"] is True


@pytest.mark.asyncio
async def test_sleep_window_returns_cached_data(monkeypatch):
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    coord = _coordinator(
        options={
            CONF_SLEEP_ENABLED: True,
            CONF_SLEEP_START: "11:00",
            CONF_SLEEP_END: "13:00",
        },
        data={"departures": [{"route": "cached"}]},
    )

    assert await coord._async_update_data() == {"departures": [{"route": "cached"}]}


@pytest.mark.asyncio
async def test_sleep_window_without_cache_returns_empty_marker(monkeypatch):
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    coord = _coordinator(
        options={
            CONF_SLEEP_ENABLED: True,
            CONF_SLEEP_START: "13:00",
            CONF_SLEEP_END: "12:30",
        }
    )

    result = await coord._async_update_data()

    assert result["sleep_mode"] is True
    assert result["departures"] == []
    assert result["last_update"] == FIXED_NOW.isoformat()


@pytest.mark.asyncio
async def test_invalid_sleep_time_falls_through_to_fetch(monkeypatch):
    calls = []

    async def fake_fetch(coord):
        calls.append(True)
        return _departures()

    monkeypatch.setattr(provider_ztm, "fetch", fake_fetch)
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    coord = _coordinator(
        options={
            CONF_SLEEP_ENABLED: True,
            CONF_SLEEP_START: "bad",
            CONF_SLEEP_END: "13:00",
        }
    )

    result = await coord._async_update_data()

    assert calls == [True]
    assert result["departures"]


@pytest.mark.asyncio
async def test_gtfs_coordinates_and_walking_distance_are_added(monkeypatch):
    async def fake_fetch(coord):
        return _departures()

    monkeypatch.setattr(provider_gtfsrt, "fetch", fake_fetch)
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    monkeypatch.setattr(
        "mzkzg_transport.walking.stop_walking_info",
        lambda *args: {"walking_distance_m": 120, "walking_time_min": 2},
    )
    coord = _coordinator("gtfsrt_lublin", {CONF_SLEEP_ENABLED: False})
    coord.hass.data[DOMAIN]["_gtfsrt_cache"] = {
        f"gtfsrt_lublin_{FIXED_NOW:%Y%m%d}": {
            "stops": {coord.stop_id: {"lat": 51.25, "lon": 22.57}}
        }
    }

    result = await coord._async_update_data()

    assert coord.stop_lat == 51.25
    assert coord.stop_lon == 22.57
    assert result["walking_distance_m"] == 120
    assert result["walking_time_min"] == 2


@pytest.mark.asyncio
async def test_walking_distance_uses_existing_coordinates(monkeypatch):
    async def fake_fetch(coord):
        return _departures()

    monkeypatch.setattr(provider_ztm, "fetch", fake_fetch)
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    monkeypatch.setattr(
        "mzkzg_transport.walking.stop_walking_info",
        lambda *args: {"walking_distance_m": 80, "walking_time_min": 1},
    )
    coord = _coordinator(PROVIDER_ZTM, {CONF_SLEEP_ENABLED: False})
    coord.stop_lat = 54.35
    coord.stop_lon = 18.65

    result = await coord._async_update_data()

    assert result["walking_distance_m"] == 80


@pytest.mark.asyncio
async def test_provider_error_is_wrapped_in_update_failed(monkeypatch):
    async def failing_fetch(coord):
        raise RuntimeError("feed down")

    monkeypatch.setattr(provider_ztm, "fetch", failing_fetch)
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    coord = _coordinator(PROVIDER_ZTM, {CONF_SLEEP_ENABLED: False})

    with pytest.raises(UpdateFailed, match="feed down"):
        await coord._async_update_data()


@pytest.mark.asyncio
async def test_offline_only_uses_snapshot_without_calling_provider(monkeypatch):
    fetch = AsyncMock()
    monkeypatch.setattr(provider_ztm, "fetch", fetch)
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    monkeypatch.setattr(
        "mzkzg_transport.coordinator.async_load_snapshot",
        AsyncMock(
            return_value={
                "provider": PROVIDER_ZTM,
                "stop_id": "2230",
                "stop_name": "Płocka 01",
                "saved_at": "2026-11-08T12:00:00",
                "departures": [
                    {"time": "2026-11-08T12:30:00", "route": "6", "headsign": "Jelitkowo"}
                ],
            }
        ),
    )
    coord = _coordinator(
        PROVIDER_ZTM,
        {CONF_SLEEP_ENABLED: False, CONF_OFFLINE_ONLY: True},
    )

    result = await coord._async_update_data()

    fetch.assert_not_awaited()
    assert result["offline"] is True
    assert result["departures"][0]["route"] == "6"
    assert result["departures"][0]["realtime"] is False


@pytest.mark.asyncio
async def test_offline_only_without_snapshot_returns_marker(monkeypatch):
    fetch = AsyncMock()
    monkeypatch.setattr(provider_ztm, "fetch", fetch)
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    monkeypatch.setattr(
        "mzkzg_transport.coordinator.async_load_snapshot", AsyncMock(return_value=None)
    )
    coord = _coordinator(
        PROVIDER_ZTM,
        {CONF_SLEEP_ENABLED: False, CONF_OFFLINE_ONLY: True},
    )

    result = await coord._async_update_data()

    fetch.assert_not_awaited()
    assert result["offline"] is True
    assert result["offline_missing"] is True
    assert result["departures"] == []


@pytest.mark.asyncio
async def test_fetch_failure_uses_offline_snapshot(monkeypatch):
    async def failing_fetch(coord):
        raise RuntimeError("offline")

    monkeypatch.setattr(provider_ztm, "fetch", failing_fetch)
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    monkeypatch.setattr(
        "mzkzg_transport.coordinator.async_load_snapshot",
        AsyncMock(
            return_value={
                "provider": PROVIDER_ZTM,
                "stop_id": "2230",
                "stop_name": "Płocka 01",
                "saved_at": "2026-11-08T12:00:00",
                "departures": [
                    {"time": "2026-11-08T13:00:00", "route": "3", "headsign": "Nowy Port"}
                ],
            }
        ),
    )
    coord = _coordinator(PROVIDER_ZTM, {CONF_SLEEP_ENABLED: False})

    result = await coord._async_update_data()

    assert result["offline"] is True
    assert result["departures"][0]["route"] == "3"


@pytest.mark.asyncio
async def test_successful_fetch_saves_offline_snapshot(monkeypatch):
    async def fake_fetch(coord):
        return _departures()

    save = AsyncMock(return_value=True)
    monkeypatch.setattr(provider_ztm, "fetch", fake_fetch)
    monkeypatch.setattr("homeassistant.util.dt.now", lambda: FIXED_NOW)
    monkeypatch.setattr("mzkzg_transport.coordinator.async_save_snapshot", save)
    coord = _coordinator(PROVIDER_ZTM, {CONF_SLEEP_ENABLED: False})

    await coord._async_update_data()

    save.assert_awaited_once()
    assert save.await_args.args[1] == PROVIDER_ZTM
    assert save.await_args.args[2] == "2230"
