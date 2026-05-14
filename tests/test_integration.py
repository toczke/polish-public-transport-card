"""Tests for MZKZG Transport integration."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from aioresponses import aioresponses

from mzkzg_transport.const import (
    DOMAIN,
    KIEDYPRZYJEDZIE_BASE_URLS,
    KIEDYPRZYJEDZIE_ALBATROS_URL,
    KIEDYPRZYJEDZIE_BYTOW_URL,
    KIEDYPRZYJEDZIE_CZLUCHOW_URL,
    KIEDYPRZYJEDZIE_GRYF_URL,
    KIEDYPRZYJEDZIE_MZK_MALBORK_URL,
    KIEDYPRZYJEDZIE_MZK_STAROGARD_URL,
    KIEDYPRZYJEDZIE_NORD_EXPRESS_URL,
    KIEDYPRZYJEDZIE_PKS_GDANSK_URL,
    KIEDYPRZYJEDZIE_PKS_GDYNIA_URL,
    KIEDYPRZYJEDZIE_PKS_SLUPSK_URL,
    KIEDYPRZYJEDZIE_PKS_STAROGARD_URL,
    PROVIDER_ALBATROS,
    PROVIDER_BYTOW,
    PROVIDER_CZLUCHOW,
    PROVIDER_GRYF,
    PROVIDER_MZK_MALBORK,
    PROVIDER_MZK_STAROGARD,
    PROVIDER_NORD_EXPRESS,
    PROVIDER_PKS_GDANSK,
    PROVIDER_PKS_GDYNIA,
    PROVIDER_PKS_SLUPSK,
    PROVIDER_PKS_STAROGARD,
    PROVIDER_ZKM,
    PROVIDER_ZTM,
    PROVIDER_TCZEW,
    TIME4BUS_TCZEW_LIVE_DEPARTURES_URL,
    TIME4BUS_TCZEW_SCHEDULE_DEPARTURES_URL,
    TIME4BUS_TCZEW_STOPS_URL,
    ZKM_GDYNIA_DELAYS_URL,
    ZKM_GDYNIA_ROUTES_URL,
    ZTM_GDANSK_DEPARTURES_URL,
)
from mzkzg_transport.coordinator import MzkzgTransportCoordinator


# ── Patch HA frame helper globally ───────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_ha_frame():
    """Patch HA frame helper."""
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


@pytest.fixture(autouse=True)
def patch_session():
    """Make coordinator._get_session return tracked sessions and close them after each test."""
    import aiohttp

    sessions = []

    async def _patched_get(self):
        session = aiohttp.ClientSession()
        sessions.append(session)
        return session

    with patch.object(MzkzgTransportCoordinator, "_get_session", _patched_get):
        yield

    for session in sessions:
        if not session.closed:
            asyncio.run(session.close())


@pytest.fixture
def mock_hass():
    """Create a minimal hass mock."""
    hass = MagicMock()
    hass.data = {"mzkzg_transport": {"_coordinators": {}}}
    return hass


# ── ZTM Gdańsk tests ────────────────────────────────────────────────────────

@pytest.fixture
def ztm_response():
    now = datetime.now()
    return {
        "departures": [
            {
                "routeShortName": "131",
                "headsign": "Oliwa PKP",
                "estimatedTime": (now + timedelta(minutes=3)).isoformat(),
                "theoreticalTime": (now + timedelta(minutes=2)).isoformat(),
                "delayInSeconds": 60,
                "status": "REALTIME",
                "wheelchairAccessible": True,
                "bikeAllowed": False,
            },
            {
                "routeShortName": "9",
                "headsign": "Jelitkowo",
                "estimatedTime": (now + timedelta(minutes=8)).isoformat(),
                "theoreticalTime": (now + timedelta(minutes=8)).isoformat(),
                "delayInSeconds": 0,
                "status": "REALTIME",
                "wheelchairAccessible": True,
                "bikeAllowed": True,
            },
            {
                "routeShortName": "N8",
                "headsign": "Wrzeszcz",
                "estimatedTime": (now - timedelta(minutes=5)).isoformat(),
                "theoreticalTime": (now - timedelta(minutes=5)).isoformat(),
                "delayInSeconds": 0,
                "status": "SCHEDULED",
            },
        ]
    }


@pytest.mark.asyncio
async def test_ztm_fetch_departures(mock_hass, ztm_response):
    """Test ZTM Gdańsk departure fetching and parsing."""
    coordinator = MzkzgTransportCoordinator(mock_hass, "1327", PROVIDER_ZTM, "Test Stop")

    with aioresponses() as m:
        m.get(f"{ZTM_GDANSK_DEPARTURES_URL}?stopId=1327", payload=ztm_response)
        result = await coordinator._fetch_ztm()

    assert result["provider"] == PROVIDER_ZTM
    assert result["stop_id"] == "1327"
    assert result["stop_name"] == "Test Stop"
    # Should filter out the departed one (N8, -5 min)
    assert len(result["departures"]) == 2
    assert result["departures"][0]["route"] == "131"
    assert result["departures"][0]["realtime"] is True
    assert result["departures"][0]["delay_seconds"] == 60
    assert result["departures"][0]["wheelchair_accessible"] is True
    assert result["departures"][0]["bike_allowed"] is False
    assert result["departures"][1]["route"] == "9"
    assert result["departures"][1]["bike_allowed"] is True
    assert result["departures"][0]["vehicle_type"] == "bus"
    assert result["departures"][1]["vehicle_type"] == "tram"



@pytest.mark.asyncio
async def test_ztm_vehicle_type():
    """Test vehicle type detection for ZTM."""
    assert MzkzgTransportCoordinator._ztm_vehicle_type("9") == "tram"
    assert MzkzgTransportCoordinator._ztm_vehicle_type("12") == "tram"
    assert MzkzgTransportCoordinator._ztm_vehicle_type("99") == "tram"
    assert MzkzgTransportCoordinator._ztm_vehicle_type("100") == "bus"
    assert MzkzgTransportCoordinator._ztm_vehicle_type("131") == "bus"
    assert MzkzgTransportCoordinator._ztm_vehicle_type("N8") == "bus"


# ── ZKM Gdynia tests ────────────────────────────────────────────────────────

@pytest.fixture
def zkm_routes_response():
    return [
        {"routeId": 1, "routeShortName": "21"},
        {"routeId": 2, "routeShortName": "22"},
        {"routeId": 3, "routeShortName": "181"},
    ]


@pytest.fixture
def zkm_delays_response():
    now = datetime.now()
    return {
        "delay": [
            {
                "routeId": 1,
                "headsign": "Dworzec Główny",
                "estimatedTime": (now + timedelta(minutes=5)).strftime("%H:%M:%S"),
                "theoreticalTime": (now + timedelta(minutes=4)).strftime("%H:%M:%S"),
                "delayInSeconds": 60,
                "status": "REALTIME",
            },
            {
                "routeId": 3,
                "headsign": "Obłuże",
                "estimatedTime": (now + timedelta(minutes=12)).strftime("%H:%M:%S"),
                "theoreticalTime": (now + timedelta(minutes=12)).strftime("%H:%M:%S"),
                "delayInSeconds": 0,
                "status": "REALTIME",
            },
        ]
    }


@pytest.mark.asyncio
async def test_zkm_fetch_departures(mock_hass, zkm_routes_response, zkm_delays_response):
    """Test ZKM Gdynia departure fetching and parsing."""
    coordinator = MzkzgTransportCoordinator(mock_hass, "38220", PROVIDER_ZKM, "Chylonia")

    with aioresponses() as m:
        m.get(ZKM_GDYNIA_ROUTES_URL, payload=zkm_routes_response)
        m.get(f"{ZKM_GDYNIA_DELAYS_URL}?stopId=38220", payload=zkm_delays_response)
        result = await coordinator._fetch_zkm()

    assert result["provider"] == PROVIDER_ZKM
    assert result["stop_id"] == "38220"
    assert len(result["departures"]) == 2
    assert result["departures"][0]["route"] == "21"
    assert result["departures"][0]["headsign"] == "Dworzec Główny"
    assert result["departures"][0]["realtime"] is True
    assert result["departures"][0]["vehicle_type"] == "trolleybus"
    assert result["departures"][1]["route"] == "181"
    assert result["departures"][1]["vehicle_type"] == "bus"



@pytest.mark.asyncio
async def test_zkm_vehicle_type():
    """Test vehicle type detection for ZKM."""
    assert MzkzgTransportCoordinator._zkm_vehicle_type("21") == "trolleybus"
    assert MzkzgTransportCoordinator._zkm_vehicle_type("25") == "trolleybus"
    assert MzkzgTransportCoordinator._zkm_vehicle_type("181") == "bus"
    assert MzkzgTransportCoordinator._zkm_vehicle_type("N21") == "bus"


# â”€â”€ kiedyPrzyjedzie.pl tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.fixture
def kiedyprzyjedzie_response():
    """Sample kiedyPrzyjedzie API response."""
    now = datetime.now()
    return {
        "timestamp": int(now.timestamp()),
        "rows": [
            {
                "time": "42 min",
                "static_time": "40 min",
                "time_diff": 2,
                "at_stop": False,
                "canceled": False,
                "is_estimated": True,
                "direction_id": 1635414000,
                "platform": "1",
                "deviation_id": None,
                "line_name": "854",
                "show_line_name": True,
                "vehicle_type": 0,
                "vehicle_attributes": ["ac", "bike_transport", "low_floor"],
                "trip_id": 38682560,
                "trip_execution_id": "854-9A:739749:3",
                "trip_index": 0,
                "passenger_load": None,
            },
            {
                "time": (now + timedelta(hours=2)).strftime("%H:%M"),
                "static_time": (now + timedelta(hours=2)).strftime("%H:%M"),
                "time_diff": 0,
                "at_stop": False,
                "canceled": False,
                "is_estimated": False,
                "direction_id": 1635414001,
                "platform": "1",
                "deviation_id": None,
                "line_name": "870",
                "show_line_name": True,
                "vehicle_type": 0,
                "vehicle_attributes": ["ac", "bike_transport"],
                "trip_id": 35966917,
                "trip_execution_id": "870-06SS:739749:1",
                "trip_index": 0,
                "passenger_load": None,
            },
        ],
        "directions": {
            "1635414000": "Buszkowy",
            "1635414001": "Krynica Morska, Dworzec",
        },
        "deviations": {},
        "designator": 1,
        "station_name": "GdaÅ„sk, Dworzec Autobusowy",
        "only_disembarking": False,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "base_url", "stop_id", "station_name"),
    [
        (PROVIDER_PKS_GDANSK, KIEDYPRZYJEDZIE_PKS_GDANSK_URL, "1564032:1635414", "GdaÅ„sk, Dworzec Autobusowy"),
        (PROVIDER_ALBATROS, KIEDYPRZYJEDZIE_ALBATROS_URL, "1979970:2052519", "GdaÅ„sk, Dworzec GÅ‚Ã³wny 20"),
    ],
)
async def test_kiedyprzyjedzie_fetch_departures(mock_hass, kiedyprzyjedzie_response, provider, base_url, stop_id, station_name):
    """Test kiedyPrzyjedzie departure fetching and parsing."""
    coordinator = MzkzgTransportCoordinator(mock_hass, stop_id, provider, "Test Stop")

    response = dict(kiedyprzyjedzie_response)
    response["station_name"] = station_name

    with aioresponses() as m:
        m.get(f"{base_url}/api/departures/{stop_id}", payload=response)
        result = await coordinator._fetch_kiedyprzyjedzie()

    assert result["provider"] == provider
    assert result["stop_id"] == stop_id
    # Configured stop name should take precedence over API station_name
    assert result["stop_name"] == "Test Stop"
    assert len(result["departures"]) == 2
    assert result["departures"][0]["route"] == "854"
    assert result["departures"][0]["headsign"] == "Buszkowy"
    assert result["departures"][0]["bike_allowed"] is True
    assert result["departures"][0]["wheelchair_accessible"] is True
    assert result["departures"][0]["air_conditioning"] is True
    assert result["departures"][0]["realtime"] is True
    assert result["departures"][0]["cancelled"] is False
    assert result["departures"][1]["route"] == "870"
    assert result["departures"][1]["realtime"] is False
    assert datetime.fromisoformat(result["departures"][0]["estimated_time"])


# ── Constant and import tests ────────────────────────────────────────────────

def test_const_values():
    """Test that constants are properly defined."""
    assert DOMAIN == "mzkzg_transport"
    assert "zdiz.gdynia.pl" in ZKM_GDYNIA_DELAYS_URL
    assert "multimediagdansk.pl" in ZTM_GDANSK_DEPARTURES_URL
    assert PROVIDER_TCZEW == "time4bus_tczew"
    assert TIME4BUS_TCZEW_STOPS_URL.endswith("/operators/tczew/stops")
    assert TIME4BUS_TCZEW_LIVE_DEPARTURES_URL.endswith("/live/schedules/tczew/stops")
    assert TIME4BUS_TCZEW_SCHEDULE_DEPARTURES_URL.endswith("/operators/tczew/stops")
    assert KIEDYPRZYJEDZIE_PKS_GDANSK_URL.endswith("pksgdansk.kiedyprzyjedzie.pl")
    assert KIEDYPRZYJEDZIE_ALBATROS_URL.endswith("albatros.kiedyprzyjedzie.pl")


def test_import_all_modules():
    """Test that all modules can be imported."""
    from mzkzg_transport import const
    from mzkzg_transport import coordinator
    from mzkzg_transport import config_flow
    from mzkzg_transport import sensor
    assert const.DOMAIN == "mzkzg_transport"


@pytest.mark.asyncio
async def test_ztm_empty_response(mock_hass):
    """Test handling of empty departures."""
    coordinator = MzkzgTransportCoordinator(mock_hass, "9999", PROVIDER_ZTM, "Empty")

    with aioresponses() as m:
        m.get(f"{ZTM_GDANSK_DEPARTURES_URL}?stopId=9999", payload={"departures": []})
        result = await coordinator._fetch_ztm()

    assert result["departures"] == []


@pytest.mark.asyncio
async def test_zkm_routes_caching(mock_hass, zkm_routes_response, zkm_delays_response):
    """Test that ZKM routes are cached after first load."""
    coordinator = MzkzgTransportCoordinator(mock_hass, "38220", PROVIDER_ZKM, "Test")

    with aioresponses() as m:
        m.get(ZKM_GDYNIA_ROUTES_URL, payload=zkm_routes_response)
        m.get(f"{ZKM_GDYNIA_DELAYS_URL}?stopId=38220", payload=zkm_delays_response)
        await coordinator._fetch_zkm()

    # Routes should be cached now
    assert coordinator._routes_map["1"] == "21"
    assert coordinator._routes_map["2"] == "22"
    assert coordinator._routes_map["3"] == "181"



@pytest.mark.asyncio
async def test_ztm_vehicle_code_and_fleet(mock_hass):
    """Test ZTM departure includes vehicle_code and fleet capabilities."""
    from re import compile as re_compile
    coordinator = MzkzgTransportCoordinator(mock_hass, "1327", PROVIDER_ZTM, "Test")

    fleet_response = {"results": [
        {"vehicleCode": "2742", "airConditioning": True, "wheelchairsRamp": True, "bikeHolders": 2, "usb": True, "ticketMachine": True}
    ]}

    with aioresponses() as m:
        m.get(re_compile(r".*departures.*"), payload={"departures": [
            {"routeShortName": "154", "headsign": "Orunia", "estimatedTime": "2099-12-31T23:00:00Z",
             "theoreticalTime": "2099-12-31T22:58:00Z", "delayInSeconds": 120, "status": "REALTIME", "vehicleCode": 2742}
        ]})
        m.get(re_compile(r".*baza-pojazdow.*"), payload=fleet_response)

        result = await coordinator._fetch_ztm()

    dep = result["departures"][0]
    assert dep["vehicle_code"] == "2742"
    assert dep["air_conditioning"] is True
    assert dep["wheelchair_accessible"] is True
    assert dep["bike_allowed"] is True
    assert dep["usb"] is True
    assert dep["ticket_machine"] is True
