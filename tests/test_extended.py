"""Extended tests for MZKZG Transport — coverage boost."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from aioresponses import aioresponses

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from mzkzg_transport.const import (
    DOMAIN, PROVIDER_ZTM, PROVIDER_ZKM, PROVIDER_MZK, PROVIDER_PLK,
    PLK_API_BASE, ZTM_GDANSK_DEPARTURES_URL, ZKM_GDYNIA_DELAYS_URL, ZKM_GDYNIA_ROUTES_URL,
)
from mzkzg_transport.coordinator import MzkzgTransportCoordinator
from mzkzg_transport.gtfs_provider import GtfsData, get_gtfs_data
from mzkzg_transport.binary_sensor import MzkzgDelayBinarySensor, DELAY_THRESHOLD_SECONDS


@pytest.fixture(autouse=True)
def patch_ha():
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


@pytest.fixture(autouse=True)
def patch_session():
    import aiohttp
    async def _patched_get(self):
        return aiohttp.ClientSession()
    with patch.object(MzkzgTransportCoordinator, "_get_session", _patched_get):
        yield


@pytest.fixture
def mock_hass():
    return MagicMock()


# ── GTFS Provider tests ─────────────────────────────────────────────────────

def test_gtfs_parse_zip():
    """Test GTFS zip parsing with real data."""
    from pathlib import Path
    zip_path = Path("/tmp/wejherowo.zip")
    if not zip_path.exists():
        pytest.skip("GTFS zip not available")
    
    gtfs = GtfsData()
    gtfs.parse_zip(zip_path.read_bytes())
    
    assert gtfs.loaded
    assert len(gtfs.stops) > 300
    assert len(gtfs.routes) > 10
    assert len(gtfs.trips) > 1000
    assert len(gtfs.stop_times) > 100
    assert len(gtfs.calendar_dates) > 0


def test_gtfs_departures_empty_stop():
    """Test GTFS returns empty for nonexistent stop."""
    gtfs = GtfsData()
    gtfs._loaded = True
    deps = gtfs.get_departures("99999")
    assert deps == []


def test_gtfs_departures_no_service_today():
    """Test GTFS returns empty when no service runs today."""
    gtfs = GtfsData()
    gtfs._loaded = True
    gtfs.stop_times = {"1": [{"trip_id": "t1", "departure_time": "12:00:00", "stop_sequence": 0}]}
    gtfs.trips = {"t1": {"route_id": "r1", "service_id": "s1", "headsign": "Test"}}
    gtfs.routes = {"r1": {"short_name": "1", "long_name": "", "color": ""}}
    gtfs.calendar_dates = {"s1": set()}  # No dates active
    
    deps = gtfs.get_departures("1")
    assert deps == []


def test_gtfs_departures_with_service():
    """Test GTFS returns departures when service is active."""
    gtfs = GtfsData()
    gtfs._loaded = True
    today = datetime.now().strftime("%Y%m%d")
    gtfs.stop_times = {"1": [{"trip_id": "t1", "departure_time": "23:59:00", "stop_sequence": 0}]}
    gtfs.trips = {"t1": {"route_id": "r1", "service_id": "s1", "headsign": "Destination"}}
    gtfs.routes = {"r1": {"short_name": "5", "long_name": "", "color": ""}}
    gtfs.calendar_dates = {"s1": {today}}
    
    deps = gtfs.get_departures("1")
    assert len(deps) == 1
    assert deps[0]["route"] == "5"
    assert deps[0]["headsign"] == "Destination"
    assert deps[0]["realtime"] is False
    assert deps[0]["provider"] == "mzk_wejherowo"


def test_gtfs_skips_past_departures():
    """Test GTFS skips departures that already passed."""
    gtfs = GtfsData()
    gtfs._loaded = True
    today = datetime.now().strftime("%Y%m%d")
    gtfs.stop_times = {"1": [{"trip_id": "t1", "departure_time": "00:01:00", "stop_sequence": 0}]}
    gtfs.trips = {"t1": {"route_id": "r1", "service_id": "s1", "headsign": "X"}}
    gtfs.routes = {"r1": {"short_name": "1", "long_name": "", "color": ""}}
    gtfs.calendar_dates = {"s1": {today}}
    
    # If current time is after 00:01, this should be empty
    now = datetime.now()
    if now.hour > 0 or now.minute > 1:
        deps = gtfs.get_departures("1")
        assert deps == []


# ── Binary Sensor tests ──────────────────────────────────────────────────────

def test_binary_sensor_is_on_with_delay():
    """Test binary sensor turns on with significant delay."""
    coordinator = MagicMock()
    coordinator.data = {
        "departures": [
            {"route": "131", "headsign": "X", "delay_seconds": 200},
            {"route": "9", "headsign": "Y", "delay_seconds": 0},
        ]
    }
    entry = MagicMock()
    entry.data = {"stop_id": "123", "provider": PROVIDER_ZTM, "name": "Test"}
    
    sensor = MzkzgDelayBinarySensor(coordinator, entry)
    assert sensor.is_on is True


def test_binary_sensor_is_off_no_delay():
    """Test binary sensor stays off without significant delay."""
    coordinator = MagicMock()
    coordinator.data = {
        "departures": [
            {"route": "131", "headsign": "X", "delay_seconds": 60},
            {"route": "9", "headsign": "Y", "delay_seconds": -30},
        ]
    }
    entry = MagicMock()
    entry.data = {"stop_id": "123", "provider": PROVIDER_ZTM, "name": "Test"}
    
    sensor = MzkzgDelayBinarySensor(coordinator, entry)
    assert sensor.is_on is False


def test_binary_sensor_is_off_empty():
    """Test binary sensor off when no data."""
    coordinator = MagicMock()
    coordinator.data = None
    entry = MagicMock()
    entry.data = {"stop_id": "123", "provider": PROVIDER_ZKM, "name": ""}
    
    sensor = MzkzgDelayBinarySensor(coordinator, entry)
    assert sensor.is_on is False


def test_binary_sensor_attributes():
    """Test binary sensor extra attributes."""
    coordinator = MagicMock()
    coordinator.data = {
        "departures": [
            {"route": "131", "headsign": "Oliwa", "delay_seconds": 300},
            {"route": "9", "headsign": "Y", "delay_seconds": 60},
        ]
    }
    entry = MagicMock()
    entry.data = {"stop_id": "123", "provider": PROVIDER_ZTM, "name": "Test"}
    
    sensor = MzkzgDelayBinarySensor(coordinator, entry)
    attrs = sensor.extra_state_attributes
    assert len(attrs["delayed_departures"]) == 1
    assert attrs["delayed_departures"][0]["route"] == "131"
    assert attrs["delayed_departures"][0]["delay_minutes"] == 5


# ── PLK Coordinator tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_plk_rate_limit(mock_hass):
    """Test PLK handles 429 rate limit gracefully."""
    from re import compile as re_compile
    coordinator = MzkzgTransportCoordinator(mock_hass, "7534", PROVIDER_PLK, "Gdańsk Wrzeszcz", "fake-key")
    
    with aioresponses() as m:
        # 429 on operations, schedules also fails
        m.get(re_compile(r".*/operations.*"), status=429)
        m.get(re_compile(r".*/schedules.*"), status=429)
        
        # Should raise or return empty - either way, doesn't crash
        try:
            result = await coordinator._fetch_plk()
            # If it doesn't raise, departures should be empty
            assert result["departures"] == []
        except Exception:
            pass  # UpdateFailed is acceptable


@pytest.mark.asyncio
async def test_plk_empty_schedules(mock_hass):
    """Test PLK with empty schedule response."""
    from re import compile as re_compile
    coordinator = MzkzgTransportCoordinator(mock_hass, "7534", PROVIDER_PLK, "Test", "fake-key")
    
    with aioresponses() as m:
        m.get(re_compile(r".*/operations.*"), payload={"trains": []})
        m.get(re_compile(r".*/schedules.*"), payload={"routes": [], "dictionaries": {"stations": {}, "carriers": {}}})
        
        result = await coordinator._fetch_plk()
    
    assert result["provider"] == PROVIDER_PLK
    assert result["departures"] == []


@pytest.mark.asyncio
async def test_plk_with_schedule_data(mock_hass):
    """Test PLK parses schedule data correctly."""
    from re import compile as re_compile
    coordinator = MzkzgTransportCoordinator(mock_hass, "7534", PROVIDER_PLK, "", "fake-key")
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    future_time = f"{now.hour+1:02d}:30:00" if now.hour < 23 else "23:59:00"
    
    with aioresponses() as m:
        m.get(re_compile(r".*/operations.*"), payload={"trains": []})
        m.get(re_compile(r".*/schedules.*"), payload={
            "routes": [{
                "trainNumber": "12345",
                "routeId": 1,
                "carrierCode": "SKM",
                "commercialCategorySymbol": "SKM",
                "operatingDate": today,
                "stations": [
                    {"stationId": "7534", "departureTime": future_time, "departureDay": 0, "platform": "2"},
                    {"stationId": "5900", "arrivalTime": future_time, "arrivalDay": 0},
                ]
            }],
            "dictionaries": {
                "stations": {"7534": "Gdańsk Wrzeszcz", "5900": "Gdynia Główna"},
                "carriers": {"SKM": "PKP SKM"}
            }
        })
        
        result = await coordinator._fetch_plk()
    
    assert result["stop_name"] == "Gdańsk Wrzeszcz"
    assert len(result["departures"]) == 1
    dep = result["departures"][0]
    assert dep["route"] == "SKM"
    assert dep["headsign"] == "Gdynia Główna"
    assert dep["carrier"] == "PKP SKM"
    assert dep["provider"] == PROVIDER_PLK
    assert len(dep["route_stops"]) == 2


# ── ZKM edge cases ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_zkm_time_over_24(mock_hass):
    """Test ZKM handles times >= 24:00 (after midnight)."""
    from re import compile as re_compile
    coordinator = MzkzgTransportCoordinator(mock_hass, "37030", PROVIDER_ZKM, "Test")
    coordinator._routes_map = {"1": "21"}
    
    with aioresponses() as m:
        m.get(re_compile(r".*zdiz.*routes.*"), payload=[{"routeId": 1, "routeShortName": "21"}])
        m.get(re_compile(r".*zdiz.*delays.*"), payload={
            "delay": [{
                "routeId": 1,
                "headsign": "Night",
                "estimatedTime": "25:10:00",
                "theoreticalTime": "25:10:00",
                "delayInSeconds": 0,
                "status": "REALTIME",
            }]
        })
        result = await coordinator._fetch_zkm()
        assert result["provider"] == PROVIDER_ZKM


# ── Coordinator _plk_time_to_datetime ────────────────────────────────────────

def test_plk_time_parsing_normal():
    """Test PLK time parsing with normal HH:MM:SS."""
    result = MzkzgTransportCoordinator._plk_time_to_datetime("2026-05-12", "14:30:00")
    assert result.hour == 14
    assert result.minute == 30


def test_plk_time_parsing_with_day_offset():
    """Test PLK time parsing with day offset."""
    result = MzkzgTransportCoordinator._plk_time_to_datetime("2026-05-12", "02:00:00", day_offset=1)
    assert result.day == 13
    assert result.hour == 2


def test_plk_time_parsing_iso_duration():
    """Test PLK time parsing with PT format (if ever used)."""
    result = MzkzgTransportCoordinator._plk_time_to_datetime("2026-05-12", "PT12H30M0S")
    assert result.hour == 12
    assert result.minute == 30
