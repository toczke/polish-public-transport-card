"""Tests for Time4BUS Tczew support."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from aioresponses import aioresponses

from mzkzg_transport.const import (
    PROVIDER_TCZEW,
    TIME4BUS_TCZEW_LIVE_DEPARTURES_URL,
    TIME4BUS_TCZEW_SCHEDULE_DEPARTURES_URL,
)
from mzkzg_transport.coordinator import MzkzgTransportCoordinator


@pytest.fixture(autouse=True)
def patch_ha_frame():
    """Patch HA frame helper."""
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


@pytest.fixture(autouse=True)
def patch_session():
    """Make coordinator._get_session return a fresh aiohttp.ClientSession."""

    async def _patched_get(self):
        return aiohttp.ClientSession()

    with patch.object(MzkzgTransportCoordinator, "_get_session", _patched_get):
        yield


@pytest.fixture
def mock_hass():
    """Create a minimal hass mock."""
    hass = MagicMock()
    hass.data = {"mzkzg_transport": {"_coordinators": {}}}
    return hass


@pytest.mark.asyncio
async def test_time4bus_tczew_live_departures(mock_hass):
    """Time4BUS live payload should parse into realtime departures."""
    now = datetime.now()
    coordinator = MzkzgTransportCoordinator(mock_hass, "10011", PROVIDER_TCZEW, "Al. Solidarności")

    live_payload = {
        "stops": [136],
        "departures": [
            {
                "stop": 136,
                "stopFullcode": "10011",
                "tid": 207214,
                "line": "3",
                "direction": "Czyżykowo",
                "lastStop": "Czyżykowo",
                "stopDurationS": 15,
                "leaveTime": int((now + timedelta(minutes=5)).timestamp() * 1000),
                "planTime": int((now + timedelta(minutes=4)).timestamp() * 1000),
                "isReal": True,
                "minutes": 5,
                "platform": "1",
                "track": None,
                "vehicleInfo": {
                    "name": "9405",
                    "lowFloor": True,
                    "airConditioning": True,
                },
            }
        ],
    }

    with aioresponses() as mocked:
        mocked.get(f"{TIME4BUS_TCZEW_LIVE_DEPARTURES_URL}/10011/departures", payload=live_payload)
        result = await coordinator._fetch_time4bus_tczew()

    assert result["provider"] == PROVIDER_TCZEW
    assert result["stop_id"] == "10011"
    assert result["stop_name"] == "Al. Solidarności"
    assert len(result["departures"]) == 1
    departure = result["departures"][0]
    assert departure["route"] == "3"
    assert departure["headsign"] == "Czyżykowo"
    assert departure["realtime"] is True
    assert departure["vehicle_code"] == "9405"
    assert departure["wheelchair_accessible"] is True
    assert departure["air_conditioning"] is True
    assert departure["platform"] == "1"
    assert departure["track"] is None


@pytest.mark.asyncio
async def test_time4bus_tczew_schedule_fallback(mock_hass):
    """If live departures are missing, the schedule fallback should be used."""
    coordinator = MzkzgTransportCoordinator(mock_hass, "10011", PROVIDER_TCZEW, "Al. Solidarności")
    today = datetime.now().strftime("%Y-%m-%d")

    schedule_payload = {
        "items": [
            {
                "arrivalTime": "04:37:00",
                "departureTime": "04:37:15",
                "lineId": 2,
                "lineName": "3",
                "directionName": "Czyżykowo",
                "platform": "1",
                "track": "2",
                "tripId": 207298,
            }
        ]
    }

    with aioresponses() as mocked:
        mocked.get(
            f"{TIME4BUS_TCZEW_LIVE_DEPARTURES_URL}/10011/departures",
            status=404,
        )
        mocked.get(
            f"{TIME4BUS_TCZEW_SCHEDULE_DEPARTURES_URL}/10011/departures?date={today}",
            payload=schedule_payload,
        )
        result = await coordinator._fetch_time4bus_tczew()

    assert result["provider"] == PROVIDER_TCZEW
    assert result["stop_id"] == "10011"
    assert len(result["departures"]) == 1
    departure = result["departures"][0]
    assert departure["route"] == "3"
    assert departure["headsign"] == "Czyżykowo"
    assert departure["realtime"] is False
    assert departure["delay_seconds"] == 0
    assert departure["platform"] == "1"
    assert departure["track"] == "2"
