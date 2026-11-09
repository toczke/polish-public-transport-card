"""Tests for ZTM Gdańsk provider — dedup and GPS position enrichment."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from mzkzg_transport.const import DOMAIN
from mzkzg_transport.provider_ztm import (
    _deduplicate,
    _enrich_with_positions,
    _get_fleet,
    _get_vehicle_positions,
    _parse_api_departures,
    _vehicle_type,
)


def test_dedup_removes_exact_duplicates():
    deps = [
        {"route": "2", "headsign": "Jelitkowo", "theoretical_time": "2026-07-27T08:30:00", "realtime": True},
        {"route": "2", "headsign": "Jelitkowo", "theoretical_time": "2026-07-27T08:30:00", "realtime": False},
    ]
    result = _deduplicate(deps)
    assert len(result) == 1
    assert result[0]["realtime"] == True


def test_dedup_prefers_rt():
    deps = [
        {"route": "2", "headsign": "Jelitkowo", "theoretical_time": "2026-07-27T08:30:00", "realtime": False},
        {"route": "2", "headsign": "Jelitkowo", "theoretical_time": "2026-07-27T08:30:00", "realtime": True},
    ]
    result = _deduplicate(deps)
    assert len(result) == 1
    assert result[0]["realtime"] == True


def test_dedup_keeps_different_times():
    deps = [
        {"route": "2", "headsign": "Jelitkowo", "theoretical_time": "2026-07-27T08:30:00", "realtime": True},
        {"route": "2", "headsign": "Jelitkowo", "theoretical_time": "2026-07-27T08:35:00", "realtime": False},
    ]
    result = _deduplicate(deps)
    assert len(result) == 2


def test_dedup_matches_empty_headsign():
    """Schedule entry with empty headsign matches RT with same route+time."""
    deps = [
        {"route": "2", "headsign": "Jelitkowo", "theoretical_time": "2026-07-27T08:30:00", "realtime": True},
        {"route": "2", "headsign": "", "theoretical_time": "2026-07-27T08:30:00", "realtime": False},
    ]
    result = _deduplicate(deps)
    assert len(result) == 1


def test_dedup_keeps_different_routes():
    deps = [
        {"route": "2", "headsign": "Jelitkowo", "theoretical_time": "2026-07-27T08:30:00", "realtime": True},
        {"route": "5", "headsign": "Zaspa", "theoretical_time": "2026-07-27T08:30:00", "realtime": False},
    ]
    result = _deduplicate(deps)
    assert len(result) == 2


def test_enrich_with_positions_matches_by_vehicle_code():
    deps = [
        {"route": "2", "vehicle_code": "1234", "realtime": True},
        {"route": "5", "vehicle_code": "5678", "realtime": True},
        {"route": "2", "vehicle_code": "", "realtime": False},
    ]
    positions = {
        "1234": {"lat": 54.35, "lng": 18.65, "speed": 25, "direction": 180, "generated": "2026-07-27T08:30:00Z"},
        "5678": {"lat": 54.36, "lng": 18.66, "speed": 0, "direction": 0, "generated": "2026-07-27T08:30:00Z"},
    }
    _enrich_with_positions(deps, positions)
    assert deps[0].get("vehicle_lat") == 54.35
    assert deps[0].get("vehicle_lng") == 18.65
    assert deps[0].get("vehicle_speed") == 25
    assert deps[0].get("vehicle_direction") == 180
    assert deps[1].get("vehicle_lat") == 54.36
    assert deps[2].get("vehicle_lat") is None


def test_enrich_with_positions_ignores_missing_codes():
    deps = [{"route": "2", "vehicle_code": "9999", "realtime": True}]
    positions = {"1234": {"lat": 54.35, "lng": 18.65}}
    _enrich_with_positions(deps, positions)
    assert deps[0].get("vehicle_lat") is None


def test_enrich_with_positions_empty_inputs():
    deps = []
    positions = {"1234": {"lat": 54.35, "lng": 18.65}}
    _enrich_with_positions(deps, positions)
    assert deps == []

    deps2 = [{"route": "2", "vehicle_code": None, "realtime": False}]
    positions2 = {}
    _enrich_with_positions(deps2, positions2)
    assert deps2[0].get("vehicle_lat") is None


class _FakeResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._data


class _FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def get(self, url, **kwargs):
        self.calls += 1
        return self.response


def test_vehicle_type_uses_route_number():
    assert _vehicle_type("6") == "tram"
    assert _vehicle_type("120") == "bus"
    assert _vehicle_type(None) == "bus"
    assert _vehicle_type("N2") == "bus"


def test_parse_api_departures_reads_fleet_and_skips_past_rows():
    now = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    data = {
        "departures": [
            {
                "tripId": 1,
                "routeId": 6,
                "routeShortName": "6",
                "headsign": "Jelitkowo",
                "theoreticalTime": "2026-11-09T12:05:00Z",
                "estimatedTime": "2026-11-09T12:07:00Z",
                "delayInSeconds": 120,
                "status": "REALTIME",
                "vehicleCode": "1026",
            },
            {
                "tripId": 2,
                "routeId": 200,
                "routeShortName": "200",
                "theoreticalTime": "12:30",
                "estimatedTime": "12:32",
                "status": "SCHEDULED",
            },
            {
                "routeShortName": "9",
                "theoreticalTime": "2026-11-09T09:00:00Z",
                "estimatedTime": "2026-11-09T09:00:00Z",
            },
            {"routeShortName": "10"},
        ]
    }
    fleet = {
        "1026": {
            "vehicleCharacteristics": "Przegubowy",
            "bikeHolders": 2,
            "wheelchairsRamp": True,
            "airConditioning": True,
            "usb": True,
            "ticketMachine": True,
            "model": "Solaris",
            "brand": "Urbino",
            "productionYear": 2020,
            "length": 18,
            "floorHeight": "low",
            "driveType": "electric",
            "historicVehicle": False,
            "seats": 40,
            "standingPlaces": 100,
            "monitoring": True,
            "voiceAnnouncements": True,
            "aed": True,
        }
    }

    result = _parse_api_departures(data, fleet, now)

    assert len(result) == 2
    first = result[0]
    assert first["route"] == "6"
    assert first["headsign"] == "Jelitkowo"
    assert first["realtime"] is True
    assert first["bike_allowed"] is True
    assert first["wheelchair_accessible"] is True
    assert first["air_conditioning"] is True
    assert first["vehicle_type"] == "tram"
    assert first["articulated"] is True
    assert first["vehicle_model"] == "Solaris"
    assert result[1]["vehicle_type"] == "bus"


@pytest.mark.asyncio
async def test_get_fleet_caches_and_handles_errors():
    response = _FakeResponse({"results": [{"vehicleCode": "1", "model": "X"}, {"model": "no-code"}]})
    session = _FakeSession(response)
    coord = SimpleNamespace(hass=SimpleNamespace(data={DOMAIN: {}}))

    first = await _get_fleet(coord, session)
    second = await _get_fleet(coord, session)

    assert first == {"1": {"vehicleCode": "1", "model": "X"}}
    assert second == first
    assert session.calls == 1

    bad = _FakeSession(_FakeResponse({}, status=500))
    other = SimpleNamespace(hass=SimpleNamespace(data={DOMAIN: {}}))
    assert await _get_fleet(other, bad) == {}


@pytest.mark.asyncio
async def test_get_vehicle_positions_maps_codes_and_caches():
    response = _FakeResponse(
        {
            "vehicles": [
                {"vehicleCode": "1026", "lat": 54.1, "lon": 18.2, "speed": 20, "direction": 90},
                {"lat": 54.2, "lon": 18.3},
            ]
        }
    )
    session = _FakeSession(response)
    coord = SimpleNamespace(hass=SimpleNamespace(data={DOMAIN: {}}))

    first = await _get_vehicle_positions(coord, session)
    second = await _get_vehicle_positions(coord, session)

    assert first["1026"]["lat"] == 54.1
    assert first["1026"]["direction"] == 90
    assert "None" not in first
    assert second == first
    assert session.calls == 1
