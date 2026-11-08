"""Tests for provider stop-list loaders."""

from datetime import date
from types import SimpleNamespace

import pytest

from mzkzg_transport import config_flow_stops
from mzkzg_transport.config_flow_stops import (
    _load_kiedyprzyjedzie_stops,
    _load_stops,
    _load_ztm_stops,
)
from mzkzg_transport.const import (
    KIEDYPRZYJEDZIE_BASE_URLS,
    PROVIDER_KRAKOW,
    PROVIDER_LODZ,
    PROVIDER_MZK,
    PROVIDER_PLK,
    PROVIDER_ZKM,
    PROVIDER_ZTM,
    TIME4BUS_PROVIDERS,
)


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    async def json(self):
        return self._data


class FakeGet:
    def __init__(self, data):
        self._data = data

    async def __aenter__(self):
        return FakeResponse(self._data)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, data):
        self.data = data
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return FakeGet(self.data)


def _install_session(monkeypatch, data):
    session = FakeSession(data)
    monkeypatch.setattr(config_flow_stops, "async_get_clientsession", lambda hass: session)
    return session


@pytest.mark.asyncio
async def test_load_ztm_stops_filters_non_passenger_and_sorts(monkeypatch):
    today = date.today().strftime("%Y-%m-%d")
    session = _install_session(
        monkeypatch,
        {
            today: {
                "stops": [
                    {"stopId": 2, "stopName": "Rynek", "subName": "02"},
                    {"stopId": 1, "stopName": "Dworzec", "stopCode": "01"},
                    {"stopId": 3, "stopName": "Zajezdnia", "nonpassenger": True},
                ]
            }
        },
    )

    stops = await _load_ztm_stops(SimpleNamespace(hass=SimpleNamespace()))

    assert stops == [
        {"id": 1, "name": "Dworzec 01"},
        {"id": 2, "name": "Rynek 02"},
    ]
    assert len(session.urls) == 1


@pytest.mark.asyncio
async def test_load_ztm_stops_falls_back_to_first_day_key(monkeypatch):
    _install_session(
        monkeypatch,
        {"2020-01-01": {"stops": [{"stopId": 7, "stopName": "Stary"}]}},
    )

    stops = await _load_ztm_stops(SimpleNamespace(hass=SimpleNamespace()))

    assert stops == [{"id": 7, "name": "Stary"}]


@pytest.mark.asyncio
async def test_load_kiedyprzyjedzie_stops_parses_tuples(monkeypatch):
    provider = next(iter(KIEDYPRZYJEDZIE_BASE_URLS))
    _install_session(
        monkeypatch,
        {
            "stops": [
                ["1", "code", "Rynek"],
                ["2", "code", "Dworzec"],
                ["bad"],
                "not-a-list",
            ]
        },
    )

    stops = await _load_kiedyprzyjedzie_stops(
        SimpleNamespace(hass=SimpleNamespace()), provider
    )

    assert stops == [
        {"id": "2", "name": "Dworzec"},
        {"id": "1", "name": "Rynek"},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "loader"),
    [
        (PROVIDER_ZTM, "_load_ztm_stops"),
        (PROVIDER_ZKM, "_load_zkm_stops"),
        (PROVIDER_MZK, "_load_mzk_stops"),
        (PROVIDER_PLK, "_load_plk_stations"),
        (PROVIDER_KRAKOW, "_load_krakow_stops"),
    ],
)
async def test_load_stops_dispatches_simple_providers(monkeypatch, provider, loader):
    called = []

    async def fake_loader(self):
        called.append(loader)
        return [{"id": "1", "name": "Stop"}]

    monkeypatch.setattr(config_flow_stops, loader, fake_loader)

    result = await _load_stops(SimpleNamespace(hass=SimpleNamespace()), provider)

    assert called == [loader]
    assert result == [{"id": "1", "name": "Stop"}]


@pytest.mark.asyncio
async def test_load_stops_dispatches_provider_specific_loaders(monkeypatch):
    called = []

    async def fake_loader(self, provider):
        called.append((self, provider))
        return []

    monkeypatch.setattr(config_flow_stops, "_load_time4bus_stops", fake_loader)
    monkeypatch.setattr(config_flow_stops, "_load_kiedyprzyjedzie_stops", fake_loader)
    monkeypatch.setattr(config_flow_stops, "_load_gtfsrt_stops", fake_loader)

    ctx = SimpleNamespace(hass=SimpleNamespace())
    time4bus = next(iter(TIME4BUS_PROVIDERS))
    kiedy = next(iter(KIEDYPRZYJEDZIE_BASE_URLS))

    await _load_stops(ctx, time4bus)
    await _load_stops(ctx, kiedy)
    await _load_stops(ctx, "gtfsrt_lublin")
    await _load_stops(ctx, PROVIDER_LODZ)

    assert (ctx, time4bus) in called
    assert (ctx, kiedy) in called
    assert (ctx, PROVIDER_LODZ) in called


@pytest.mark.asyncio
async def test_load_stops_logs_and_returns_empty_on_error(monkeypatch):
    async def failing_loader(self):
        raise RuntimeError("network down")

    monkeypatch.setattr(config_flow_stops, "_load_ztm_stops", failing_loader)

    assert await _load_stops(SimpleNamespace(hass=SimpleNamespace()), PROVIDER_ZTM) == []


@pytest.mark.asyncio
async def test_load_stops_returns_empty_for_unknown_provider():
    assert await _load_stops(SimpleNamespace(hass=SimpleNamespace()), "unknown") == []
