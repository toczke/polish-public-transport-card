"""Additional unit coverage for GTFS-RT helpers."""

import json
from types import SimpleNamespace

import pytest

from mzkzg_transport.const import DOMAIN
from mzkzg_transport.provider_gtfsrt import (
    _apply_position,
    _configured_stop_ids,
    _enrich_with_gps_positions,
    _get_vehicle_dict,
)


class FakeResponse:
    def __init__(self, *, json_data=None, text="", status=200):
        self._json = json_data
        self._text = text
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._json

    async def text(self):
        return self._text


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return FakeResponse(**self.responses.pop(0))


def test_configured_stop_ids_prefers_hub_stops():
    coord = SimpleNamespace(
        config_entry=SimpleNamespace(
            data={"stops": [{"stop_id": "1"}, {"id": "2"}, {"stop_id": ""}]}
        ),
        stop_id="9",
    )
    assert _configured_stop_ids(coord) == ["1", "2"]


def test_configured_stop_ids_falls_back_to_entry_then_coordinator():
    assert _configured_stop_ids(
        SimpleNamespace(
            config_entry=SimpleNamespace(data={"stop_id": "5"}), stop_id="9"
        )
    ) == ["5"]
    assert _configured_stop_ids(
        SimpleNamespace(config_entry=None, stop_id="9")
    ) == ["9"]


def test_apply_position_rejects_null_island_and_copies_values():
    departure = {}
    assert _apply_position(departure, {"lat": 0, "lng": 0}) is False
    assert departure == {}

    assert _apply_position(
        departure, {"lat": 54.1, "lng": 18.2, "bearing": 90, "speed": 10}
    ) is True
    assert departure == {
        "vehicle_lat": 54.1,
        "vehicle_lng": 18.2,
        "vehicle_direction": 90,
        "vehicle_speed": 36,
    }


@pytest.mark.asyncio
async def test_get_vehicle_dict_parses_json_and_caches():
    session = FakeSession(
        [
            {
                "text": json.dumps(
                    {
                        "1": {"num": "1026", "low": 2, "type": "Solaris"},
                        "2": {"num": "??", "low": 0},
                        "3": {"num": "", "low": 0},
                    }
                )
            }
        ]
    )
    coord = SimpleNamespace(
        provider="gtfsrt_lublin", hass=SimpleNamespace(data={DOMAIN: {}})
    )
    city_cfg = {"vehicles_url": "https://example.test/vehicles.json", "vehicles_format": "json"}

    first = await _get_vehicle_dict(coord, session, city_cfg)
    second = await _get_vehicle_dict(coord, session, city_cfg)

    assert first == {
        "1026": {"hf_lf_le": True, "ramp": True, "vehicle_model": "Solaris"}
    }
    assert second == first
    assert session.calls == ["https://example.test/vehicles.json"]


@pytest.mark.asyncio
async def test_get_vehicle_dict_returns_empty_on_error():
    session = FakeSession([{"text": "", "status": 500}])
    coord = SimpleNamespace(
        provider="gtfsrt_lublin", hass=SimpleNamespace(data={DOMAIN: {}})
    )

    assert await _get_vehicle_dict(
        coord, session, {"vehicles_url": "https://example.test/v", "vehicles_format": "json"}
    ) == {}


@pytest.mark.asyncio
async def test_enrich_with_gps_positions_json_api_and_cache():
    session = FakeSession(
        [
            {
                "json_data": {
                    "data": [
                        {
                            "vehicle": {"number": "1026"},
                            "position": {
                                "latitude": 54.1,
                                "longitude": 18.2,
                                "bearing": 90,
                                "velocity": 10,
                            },
                        },
                        {
                            "vehicle": {"number": "bad"},
                            "position": {},
                        },
                    ]
                }
            }
        ]
    )
    coord = SimpleNamespace(
        provider="gtfsrt_szczecin", hass=SimpleNamespace(data={DOMAIN: {}})
    )
    city_cfg = {"positions_url": "https://example.test/api/v2/vehicles?format=json"}
    departures = [{"vehicle_code": "1026"}]

    await _enrich_with_gps_positions(coord, session, city_cfg, departures)
    assert departures[0]["vehicle_lat"] == pytest.approx(54.1)
    assert departures[0]["vehicle_lng"] == pytest.approx(18.2)
    assert departures[0]["vehicle_direction"] == 90
    assert departures[0]["vehicle_speed"] == 36

    cached = [{"vehicle_code": "1026"}]
    await _enrich_with_gps_positions(coord, session, city_cfg, cached)
    assert cached[0]["vehicle_lat"] == pytest.approx(54.1)
    assert session.calls == ["https://example.test/api/v2/vehicles?format=json"]


@pytest.mark.asyncio
async def test_enrich_with_gps_positions_noops_without_url_or_departures():
    session = FakeSession([])
    coord = SimpleNamespace(
        provider="gtfsrt_szczecin", hass=SimpleNamespace(data={DOMAIN: {}})
    )

    await _enrich_with_gps_positions(coord, session, {}, [{"vehicle_code": "1"}])
    await _enrich_with_gps_positions(
        coord, session, {"positions_url": "https://example.test"}, []
    )

    assert session.calls == []
