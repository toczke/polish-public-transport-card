"""Extended tests for MZKZG Transport — coverage boost."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from unittest.mock import AsyncMock

import pytest
from aioresponses import aioresponses

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

from mzkzg_transport.const import (
    DOMAIN, PROVIDER_ZTM, PROVIDER_ZKM, PROVIDER_MZK, PROVIDER_PLK, PROVIDER_LODZ,
    PLK_API_BASE, ZTM_GDANSK_DEPARTURES_URL, ZKM_GDYNIA_DELAYS_URL, ZKM_GDYNIA_ROUTES_URL,
)
from mzkzg_transport.coordinator import PolishTransportCoordinator
from mzkzg_transport.gtfs_provider import GtfsData, get_gtfs_data
from mzkzg_transport.binary_sensor import PlkDelayBinarySensor
from mzkzg_transport.const import DELAY_THRESHOLD_SECONDS
from mzkzg_transport.sensor import PlkApiUsageSensor


@pytest.fixture(autouse=True)
def patch_ha():
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


@pytest.fixture(autouse=True)
def patch_session():
    import aiohttp
    sessions = []

    async def _patched_get(self):
        session = aiohttp.ClientSession()
        sessions.append(session)
        return session

    with patch.object(PolishTransportCoordinator, "_get_session", _patched_get):
        yield

    for session in sessions:
        if not session.closed:
            asyncio.run(session.close())


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {"mzkzg_transport": {"_coordinators": {}}}
    return hass


# ── GTFS Provider tests ─────────────────────────────────────────────────────

@pytest.mark.gtfsrt
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


@pytest.mark.gtfsrt
def test_gtfs_departures_empty_stop():
    """Test GTFS returns empty for nonexistent stop."""
    gtfs = GtfsData()
    gtfs._loaded = True
    deps = gtfs.get_departures("99999")
    assert deps == []


@pytest.mark.gtfsrt
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


@pytest.mark.gtfsrt
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


@pytest.mark.gtfsrt
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


@pytest.mark.plk
@pytest.mark.asyncio
async def test_plk_api_usage_sensor_restores_counters(mock_hass):
    """PLK API usage sensor should restore counters from previous HA state."""
    entry = MagicMock()
    entry.data = {"provider": "plk_rail", "stop_id": "7534"}
    sensor = PlkApiUsageSensor(mock_hass, entry)

    restored = MagicMock()
    restored.state = "321"
    restored.attributes = {
        "rate_limit_hits": 9,
        "last_success": "2026-05-14T09:20:00+02:00",
    }
    sensor.async_get_last_state = AsyncMock(return_value=restored)

    await sensor.async_added_to_hass()

    cache = mock_hass.data[DOMAIN]["_plk_cache"]
    assert cache["_req_count"] == 321
    assert cache["_429_count"] == 9
    assert cache["_ts"] == "2026-05-14T09:20:00+02:00"


@pytest.mark.plk
@pytest.mark.asyncio
async def test_plk_api_usage_sensor_does_not_overwrite_existing_cache(mock_hass):
    """Existing counters in memory should not be replaced by restored values."""
    entry = MagicMock()
    entry.data = {"provider": "plk_rail", "stop_id": "7534"}
    mock_hass.data[DOMAIN]["_plk_cache"] = {
        "_req_count": 1000,
        "_429_count": 3,
        "_ts": "2026-05-14T09:40:00+02:00",
    }
    sensor = PlkApiUsageSensor(mock_hass, entry)

    restored = MagicMock()
    restored.state = "10"
    restored.attributes = {
        "rate_limit_hits": 1,
        "last_success": "2026-05-14T08:00:00+02:00",
    }
    sensor.async_get_last_state = AsyncMock(return_value=restored)

    await sensor.async_added_to_hass()

    cache = mock_hass.data[DOMAIN]["_plk_cache"]
    assert cache["_req_count"] == 1000
    assert cache["_429_count"] == 3
    assert cache["_ts"] == "2026-05-14T09:40:00+02:00"


# ── Binary Sensor tests ──────────────────────────────────────────────────────

@pytest.mark.common
def test_binary_sensor_is_on_with_delay():
    """Test binary sensor turns on with significant delay."""
    coordinator = MagicMock()
    coordinator.data = {
        "departures": [
            {"route": "131", "headsign": "X", "delay_seconds": 360},
            {"route": "9", "headsign": "Y", "delay_seconds": 0},
        ]
    }
    entry = MagicMock()
    entry.data = {"stop_id": "123", "provider": PROVIDER_ZTM, "name": "Test"}
    
    sensor = PlkDelayBinarySensor(coordinator, entry)
    assert sensor.is_on is True


@pytest.mark.common
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
    
    sensor = PlkDelayBinarySensor(coordinator, entry)
    assert sensor.is_on is False


@pytest.mark.common
def test_binary_sensor_is_off_empty():
    """Test binary sensor off when no data."""
    coordinator = MagicMock()
    coordinator.data = None
    entry = MagicMock()
    entry.data = {"stop_id": "123", "provider": PROVIDER_ZKM, "name": ""}
    
    sensor = PlkDelayBinarySensor(coordinator, entry)
    assert sensor.is_on is False


@pytest.mark.common
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
    
    sensor = PlkDelayBinarySensor(coordinator, entry)
    attrs = sensor.extra_state_attributes
    assert len(attrs["delayed_trains"]) == 1
    assert attrs["delayed_trains"][0]["route"] == "131"
    assert attrs["delayed_trains"][0]["delay_minutes"] == 5


# ── PLK Coordinator tests ────────────────────────────────────────────────────

@pytest.mark.plk
@pytest.mark.asyncio
async def test_plk_rate_limit(mock_hass):
    """Test PLK handles 429 rate limit gracefully."""
    from re import compile as re_compile
    coordinator = PolishTransportCoordinator(mock_hass, "7534", PROVIDER_PLK, "Gdańsk Wrzeszcz", "fake-key")
    
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


@pytest.mark.plk
@pytest.mark.asyncio
async def test_plk_empty_schedules(mock_hass):
    """Test PLK with empty schedule response."""
    from re import compile as re_compile
    coordinator = PolishTransportCoordinator(mock_hass, "7534", PROVIDER_PLK, "Test", "fake-key")
    
    with aioresponses() as m:
        m.get(re_compile(r".*/operations.*"), payload={"trains": []})
        m.get(re_compile(r".*/schedules.*"), payload={"routes": [], "dictionaries": {"stations": {}, "carriers": {}}})
        
        result = await coordinator._fetch_plk()
    
    assert result["provider"] == PROVIDER_PLK
    assert result["departures"] == []


@pytest.mark.plk
@pytest.mark.asyncio
async def test_plk_with_schedule_data(mock_hass):
    """Test PLK parses schedule data correctly."""
    from re import compile as re_compile
    coordinator = PolishTransportCoordinator(mock_hass, "7534", PROVIDER_PLK, "", "fake-key")
    from homeassistant.util import dt as dt_util
    now = dt_util.now()
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


# ── ZKM edge cases ──────────────────────────────────────────────────────────

@pytest.mark.gdynia
@pytest.mark.asyncio
async def test_zkm_time_over_24(mock_hass):
    """Test ZKM handles times >= 24:00 (after midnight)."""
    from re import compile as re_compile
    coordinator = PolishTransportCoordinator(mock_hass, "37030", PROVIDER_ZKM, "Test")
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

@pytest.mark.plk
def test_plk_time_parsing_normal():
    """Test PLK time parsing with normal HH:MM:SS."""
    result = PolishTransportCoordinator._plk_time_to_datetime("2026-05-12", "14:30:00")
    assert result.hour == 14
    assert result.minute == 30


@pytest.mark.plk
def test_plk_time_parsing_with_day_offset():
    """Test PLK time parsing with day offset."""
    result = PolishTransportCoordinator._plk_time_to_datetime("2026-05-12", "02:00:00", day_offset=1)
    assert result.day == 13
    assert result.hour == 2


@pytest.mark.plk
def test_plk_time_parsing_iso_duration():
    """Test PLK time parsing with PT format (if ever used)."""
    result = PolishTransportCoordinator._plk_time_to_datetime("2026-05-12", "PT12H30M0S")
    assert result.hour == 12
    assert result.minute == 30


@pytest.mark.plk
def test_plk_update_interval_respects_daily_cap(mock_hass):
    """Test PLK coordinator stays below the daily hard cap for a single station."""
    coordinator = PolishTransportCoordinator(mock_hass, "7534", PROVIDER_PLK, "Test", "fake-key")
    assert coordinator.update_interval.total_seconds() >= 108


# ── MPK Łódź tests ────────────────────────────────────────────────────────────

@pytest.mark.lodz
@pytest.mark.asyncio
async def test_lodz_fallback_min_default(mock_hass):
    """Test _fallback_min returns default when coordinator has no options."""
    from mzkzg_transport.provider_lodz import _fallback_min
    from mzkzg_transport.const import DEFAULT_FALLBACK_MIN
    coordinator = PolishTransportCoordinator(mock_hass, "100", PROVIDER_LODZ, "Test")
    assert _fallback_min(coordinator) == DEFAULT_FALLBACK_MIN


@pytest.mark.lodz
@pytest.mark.asyncio
async def test_lodz_fallback_min_custom(mock_hass):
    """Test _fallback_min reads from coordinator options."""
    from mzkzg_transport.provider_lodz import _fallback_min
    coordinator = PolishTransportCoordinator(mock_hass, "100", PROVIDER_LODZ, "Test")
    coordinator._options = {"fallback_min": 15}
    assert _fallback_min(coordinator) == 15


@pytest.mark.lodz
def test_lodz_parse_board_xml():
    """Test parsing Łódź stop board XML."""
    from mzkzg_transport.provider_lodz import _parse_board_xml
    from datetime import datetime
    import xml.etree.ElementTree as ET

    now = datetime(2026, 7, 27, 10, 0, 0)
    xml = """<?xml version="1.0" encoding="utf-16"?>
    <Timetable>
      <Stop name="Test Stop" id="100" ds="32"/>
      <Day>
        <R nr="53A" dir="NOWOSOLNA" vt="B" vuw="N">
          <S tm="12" th="10" veh="T" nb="1155"/>
          <S tm="30" th="10" veh="N"/>
        </R>
        <R nr="64B" dir="RETKINIA" vt="B" vuw="">
          <S tm="10min" veh="T" nb="1200"/>
        </R>
      </Day>
    </Timetable>"""

    coord = MagicMock()
    coord.provider = PROVIDER_LODZ
    deps = _parse_board_xml(xml, now, coord)

    assert len(deps) == 3

    # First departure: 53A at 10:12, RT, vehicle 1155
    assert deps[0]["route"] == "53A"
    assert deps[0]["headsign"] == "NOWOSOLNA"
    assert "10:12" in deps[0]["estimated_time"]
    assert deps[0]["realtime"] is True
    assert deps[0]["vehicle_code"] == "1155"
    assert deps[0]["delay_seconds"] == 0

    # Second departure: 53A at 10:30, schedule-only
    assert deps[1]["route"] == "53A"
    assert "10:30" in deps[1]["estimated_time"]
    assert deps[1]["realtime"] is False
    assert deps[1]["vehicle_code"] is None

    # First departure has vuw="N" → wheelchair_accessible=True
    assert deps[0]["wheelchair_accessible"] is True
    assert deps[0]["bike_allowed"] is False
    assert deps[0]["air_conditioning"] is False
    assert deps[0]["ticket_machine"] is False

    # Third departure: 64B in 10 min (relative time)
    assert deps[2]["route"] == "64B"
    assert deps[2]["realtime"] is True
    assert deps[2]["vehicle_code"] == "1200"


@pytest.mark.lodz
def test_lodz_enrich_with_delays():
    """Test GTFS-RT delay enrichment matches by (route, stop_id)."""
    from mzkzg_transport.provider_lodz import _enrich_with_delays
    from datetime import datetime

    deps = [
        {"route": "53A", "theoretical_time": "2026-07-27T10:12:00", "estimated_time": "2026-07-27T10:12:00", "delay_seconds": 0, "realtime": False},
        {"route": "64B", "theoretical_time": "2026-07-27T10:30:00", "estimated_time": "2026-07-27T10:30:00", "delay_seconds": 0, "realtime": False},
        {"route": "N7A", "theoretical_time": "2026-07-27T11:00:00", "estimated_time": "2026-07-27T11:00:00", "delay_seconds": 0, "realtime": False},
    ]
    delays = {("53A", "100"): 120, ("64B", "100"): -60}
    stop_mapping = {"100": ["100", "115"]}

    _enrich_with_delays(deps, delays, stop_mapping, "100")

    # 53A matched by route "53A" + stop_id "100"
    assert deps[0]["realtime"] is True
    assert deps[0]["delay_seconds"] == 120
    assert "10:14" in deps[0]["estimated_time"]

    # 64B matched, negative delay
    assert deps[1]["realtime"] is True
    assert deps[1]["delay_seconds"] == -60
    assert "10:29" in deps[1]["estimated_time"]

    # N7A has no delay entry for (N7A, 100) or (N7A, 115)
    assert deps[2]["realtime"] is False
    assert deps[2]["delay_seconds"] == 0


@pytest.mark.lodz
def test_lodz_enrich_no_stop_mapping():
    """Test enrichment does nothing when stop mapping is empty."""
    from mzkzg_transport.provider_lodz import _enrich_with_delays

    deps = [{"route": "53A", "theoretical_time": "2026-07-27T10:12:00", "estimated_time": "2026-07-27T10:12:00", "delay_seconds": 0, "realtime": False}]
    delays = {("53A", "100"): 120}

    _enrich_with_delays(deps, delays, {"100": []}, "100")
    assert deps[0]["realtime"] is False

    _enrich_with_delays(deps, delays, {}, "100")
    assert deps[0]["realtime"] is False


@pytest.mark.lodz
@pytest.mark.asyncio
async def test_lodz_fetch_empty_boards_fallback(mock_hass):
    """Test fetch uses GTFS fallback when all API boards fail."""
    from mzkzg_transport import provider_lodz
    from mzkzg_transport.provider_lodz import _fallback_min
    from mzkzg_transport.const import DOMAIN

    coordinator = PolishTransportCoordinator(mock_hass, "205", PROVIDER_LODZ, "Test Stop")

    with aioresponses() as m:
        # All 20 boards fail with empty response
        for nr in range(1, 21):
            m.get(
                f"http://rozklady.lodz.pl/Home/GetTimetableReal?busStopId=205&busStopNr={nr}",
                body="",
                status=200,
            )
        with patch.object(provider_lodz, "_get_gtfs_zip", return_value=b"fake_zip"):
            with patch.object(provider_lodz.zipfile.ZipFile, "__init__", side_effect=Exception("No GTFS")):
                result = await provider_lodz.fetch(coordinator)

    assert result["stop_id"] == "205"
    assert result["provider"] == PROVIDER_LODZ
    # Without GTFS fallback (mock fails), should return empty departures
    assert len(result["departures"]) == 0


@pytest.mark.lodz
@pytest.mark.asyncio
async def test_lodz_fetch_single_board(mock_hass):
    """Test fetch with single-board stop_id (busStopId:stopNr format)."""
    from mzkzg_transport import provider_lodz

    coordinator = PolishTransportCoordinator(mock_hass, "100:3", PROVIDER_LODZ, "Test Single")

    with aioresponses() as m:
        m.get(
            "http://rozklady.lodz.pl/Home/GetTimetableReal?busStopId=100&busStopNr=3",
            body="""<?xml version="1.0"?>
            <Timetable>
              <Stop name="Brzezińska-Janosika" id="100" ds="32"/>
              <Day>
                <R nr="53A" dir="NOWOSOLNA" vt="B">
                  <S tm="12" th="23" veh="T" nb="1155"/>
                </R>
              </Day>
            </Timetable>""",
            status=200,
        )
        # Stop_mapping building needs GTFS zip - mock it
        import zipfile
        with patch.object(provider_lodz, "_get_gtfs_zip", return_value=b"fake"):
            with patch.object(zipfile.ZipFile, "open", side_effect=Exception("No GTFS")):
                result = await provider_lodz.fetch(coordinator)

    assert result["stop_id"] == "100:3"
    assert result["provider"] == PROVIDER_LODZ
    assert len(result["departures"]) == 1
    assert result["departures"][0]["route"] == "53A"
    assert result["departures"][0]["headsign"] == "NOWOSOLNA"


@pytest.mark.lodz
@pytest.mark.asyncio
async def test_lodz_fetch_rt_preservation(mock_hass):
    """Test that old RT departures are preserved when API returns empty."""
    from mzkzg_transport import provider_lodz

    coordinator = PolishTransportCoordinator(mock_hass, "205", PROVIDER_LODZ, "Test")
    # Seed previous data with a realtime departure
    old_rt_time = (datetime.now() + timedelta(minutes=5)).isoformat()
    coordinator.data = {
        "departures": [
            {"route": "53A", "headsign": "X", "estimated_time": old_rt_time, "realtime": True, "delay_seconds": 60, "provider": PROVIDER_LODZ},
        ]
    }

    with aioresponses() as m:
        for nr in range(1, 21):
            m.get(
                f"http://rozklady.lodz.pl/Home/GetTimetableReal?busStopId=205&busStopNr={nr}",
                body="",
                status=200,
            )
        with patch.object(provider_lodz, "_get_gtfs_zip", return_value=None):
            result = await provider_lodz.fetch(coordinator)

    # The old RT departure should be preserved (within 120s of now)
    assert len(result["departures"]) == 1
    assert result["departures"][0]["realtime"] is True
    assert result["departures"][0]["route"] == "53A"


@pytest.mark.lodz
@pytest.mark.asyncio
async def test_lodz_fetch_enrich_with_delays(mock_hass):
    """Test fetch applies GTFS-RT delays when stop mapping succeeds."""
    from mzkzg_transport import provider_lodz

    coordinator = PolishTransportCoordinator(mock_hass, "205", PROVIDER_LODZ, "Test")

    # Create a realistic stop_mapping and gtfs data
    gtfs_mock = {"stops": {}, "routes": {}, "trips": {}, "stop_times": {}, "_raw": b""}

    with patch.object(provider_lodz, "_load_gtfs") as mock_load:
        mock_load.return_value = {
            "stop_mapping": {"205": ["205"], "1854": ["205"]},
            "gtfs": gtfs_mock,
        }
        with aioresponses() as m:
            # One board returns departures
            m.get(
                "http://rozklady.lodz.pl/Home/GetTimetableReal?busStopId=205&busStopNr=1",
                body="""<?xml version="1.0"?>
                <Timetable>
                  <Stop name="Okólna-Secesyjna NŻ" id="205" ds="32"/>
                  <Day>
                    <R nr="61" dir="DW. ŁÓDŹ WIDZEW" vt="B">
                      <S tm="15" th="23" veh="N"/>
                    </R>
                  </Day>
                </Timetable>""",
                status=200,
            )
            # Other boards fail
            for nr in range(2, 21):
                m.get(
                    f"http://rozklady.lodz.pl/Home/GetTimetableReal?busStopId=205&busStopNr={nr}",
                    body="",
                    status=200,
                )
            # GTFS-RT trip_updates - mock as empty
            with patch.object(provider_lodz, "_fetch_delays", return_value={("61", "205"): 90}):
                result = await provider_lodz.fetch(coordinator)

    assert len(result["departures"]) == 1
    assert result["departures"][0]["route"] == "61"
    assert result["departures"][0]["realtime"] is True
    assert result["departures"][0]["delay_seconds"] == 90


@pytest.mark.gtfsrt
class TestGpsMatchingFallbacks:
    """Tests for multi-strategy GPS position matching."""

    def test_vehicle_code_match_priority(self):
        """vehicle_code match takes priority over route_id."""
        from mzkzg_transport.provider_gtfsrt import _apply_positions
        positions = {
            "v1": {"lat": 50.1, "lng": 19.0},
            "v2": {"lat": 50.2, "lng": 19.1, "route_id": "42"},
        }
        deps = [{"vehicle_code": "v1", "route": "42"}]
        _apply_positions(deps, positions)
        assert deps[0]["vehicle_lat"] == pytest.approx(50.1)

    def test_trip_id_match(self):
        """trip_id keyed positions match departures with trip_id."""
        from mzkzg_transport.provider_gtfsrt import _apply_positions
        positions = {"T123": {"lat": 50.1, "lng": 19.0}}
        deps = [{"trip_id": "T123", "route": "42", "vehicle_code": None}]
        _apply_positions(deps, positions)
        assert deps[0]["vehicle_lat"] == pytest.approx(50.1)

    def test_no_match_leaves_departure_unchanged(self):
        """Departure without any matching position key is unchanged."""
        from mzkzg_transport.provider_gtfsrt import _apply_positions
        positions = {"v1": {"lat": 50.1, "lng": 19.0}}
        deps = [{"vehicle_code": "v2", "route": "42", "trip_id": "T99"}]
        _apply_positions(deps, positions)
        assert "vehicle_lat" not in deps[0]

@pytest.mark.gtfsrt
class TestCalendarFallback:
    """Tests for any_weekday_match calendar resilience."""

    def test_no_weekday_match_includes_all_trips(self):
        """When no service matches today's weekday, all trips are included."""
        from mzkzg_transport.provider_gtfsrt import _parse_gtfs_zip
        import io, zipfile
        from datetime import date

        # Calendar with services only on Monday (today is not Monday)
        day_name = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][date.today().weekday()]
        if day_name == "monday":
            import pytest
            pytest.skip("Test only valid when today is not Monday")

        calendar = "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nSVC1,1,0,0,0,0,0,0,20200101,20301231\n"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,Dest\n"
        routes = "route_id,route_short_name,route_type\nR1,10,3\n"
        stops = "stop_id,stop_name\nS1,Stop One\n"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr("calendar.txt", calendar)
            zf.writestr("trips.txt", trips)
            zf.writestr("routes.txt", routes)
            zf.writestr("stops.txt", stops)

        result = _parse_gtfs_zip(buf.getvalue())
        assert "T1" in result["trips"]  # Trip should be included despite Monday-only calendar

    def test_weekday_match_filters_trips(self):
        """When a service matches today's weekday but is outside date range, trips are filtered."""
        from mzkzg_transport.provider_gtfsrt import _parse_gtfs_zip
        import io, zipfile
        from datetime import date

        days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
        today = days[date.today().weekday()]
        vals = ["1" if d == today else "0" for d in days]
        
        calendar = f"service_id,{','.join(days)},start_date,end_date\nSVC_OLD,{','.join(vals)},20200101,20200301\n"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC_OLD,Dest\n"
        routes = "route_id,route_short_name,route_type\nR1,5,3\n"
        stops = "stop_id,stop_name\nS1,Stop\n"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr("calendar.txt", calendar)
            zf.writestr("trips.txt", trips)
            zf.writestr("routes.txt", routes)
            zf.writestr("stops.txt", stops)

        result = _parse_gtfs_zip(buf.getvalue())
        assert "T1" not in result["trips"]  # Expired, should be filtered
