"""Tests for the Kraków provider (zbiorkom.live api6-open)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mzkzg_transport.provider_krakow import _legacy_key, fetch

NOW = datetime(2026, 10, 5, 21, 50, 0, tzinfo=timezone(timedelta(hours=2)))
NOW_MS = int(NOW.timestamp() * 1000)
MIN = 60 * 1000

STOPS = {"stops": [
    ["bonarka-ska02-xruaf", "krakow", "Bonarka SKA", "02", [19.945, 50.029], [3], 35, "Podgórze SKA", [], []],
    ["czerwone-maki-p+r01-vrfpw", "krakow", "Czerwone Maki P+R", "01", [19.889, 50.018], [0], 133, "", [], []],
]}


def _dep(route, minutes, brigade=None, route_type=3, delay=0, realtime=True, cancelled=False, headsign="Mistrzejowice"):
    trip = {"route": {"id": route, "name": route, "agency": "default", "type": route_type, "color": "#296d00"},
            "headsign": headsign}
    if brigade is not None:
        trip["brigade"] = brigade
    return {"trip": trip, "scheduledDeparture": NOW_MS + minutes * MIN, "delay": delay,
            "isRealtime": realtime, "isCancelled": cancelled}


def _pos(vid, route, brigade="", upcoming=(), vtype="3", location=(19.95, 50.03)):
    return {"vehicle": {"id": vid, "type": vtype, "agency": "default", "model": "MAN Lion's City"},
            "routeName": route, "brigade": brigade, "location": list(location), "bearing": 90,
            "headsign": "X", "upcomingStops": [
                {"sequence": i, "name": name, "scheduledArrival": t, "scheduledDeparture": t}
                for i, (name, t) in enumerate(upcoming)]}


def _coord(stop_id, hass_data=None):
    coord = MagicMock()
    coord.provider = "zbiorkom_krakow"
    coord.stop_id = stop_id
    coord.stop_name = None
    coord.hass.data = hass_data if hass_data is not None else {"mzkzg_transport": {}}
    coord._get_session = AsyncMock(return_value=MagicMock())
    return coord


async def _run(coord, departures, positions, calls=None):
    async def fake_fetch(session, url, timeout=15, as_text=False):
        if calls is not None:
            calls.append(url)
        if url.endswith("/stops"):
            return STOPS
        if "/stops/" in url:
            return {"departures": departures}
        if "/positions/" in url:
            if isinstance(positions, Exception):
                raise positions
            return {"positions": positions}
        raise AssertionError(url)

    with patch("mzkzg_transport.provider_krakow.fetch_with_retry", side_effect=fake_fetch), \
            patch("mzkzg_transport.provider_krakow.dt_util") as mock_dt:
        mock_dt.now.return_value = NOW
        return await fetch(coord)


@pytest.mark.krakow
class TestStopResolution:
    def test_legacy_key_matches_pre_api6_slugs(self):
        assert _legacy_key("bonarka-ska02") == "bonarka-ska02"
        assert _legacy_key("czerwone-maki-p+r01") == "czerwone-maki-p-r01"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("stop_id", ["bonarka-ska02-xruaf", "bonarka-ska02", "bonarka-ska02-oldsfx"])
    async def test_api6_id_legacy_slug_and_changed_suffix_resolve(self, stop_id):
        calls = []
        result = await _run(_coord(stop_id), [_dep("178", 5)], [], calls)
        assert result["stop_name"] == "Bonarka SKA 02"
        assert result["stop_id"] == stop_id
        assert any(u.endswith("/stops/bonarka-ska02-xruaf?limit=20") for u in calls)

    @pytest.mark.asyncio
    async def test_legacy_p_and_r_slug_resolves_and_is_url_encoded(self):
        calls = []
        result = await _run(_coord("czerwone-maki-p-r01"), [], [], calls)
        assert result["stop_name"] == "Czerwone Maki P+R 01"
        assert any("/stops/czerwone-maki-p%2Br01-vrfpw?" in u for u in calls)

    @pytest.mark.asyncio
    async def test_unknown_stop_returns_empty(self):
        result = await _run(_coord("nieistniejacy01"), [_dep("178", 5)], [])
        assert result["departures"] == []

    @pytest.mark.asyncio
    async def test_stop_list_is_fetched_once_per_hass(self):
        hass_data = {"mzkzg_transport": {}}
        calls = []
        await _run(_coord("bonarka-ska02", hass_data), [], [], calls)
        await _run(_coord("czerwone-maki-p-r01", hass_data), [], [], calls)
        assert sum(u.endswith("/stops") for u in calls) == 1


@pytest.mark.krakow
class TestDepartures:
    @pytest.mark.asyncio
    async def test_departure_fields(self):
        deps = [
            _dep("178", 5, brigade="06", delay=90_000),
            _dep("12", 7, route_type=0, realtime=False, headsign="Os.Piastów"),
            _dep("178", 9, cancelled=True),
            _dep("178", -5),  # already gone
        ]
        result = await _run(_coord("bonarka-ska02"), deps, [])
        out = result["departures"]
        assert [d["route"] for d in out] == ["178", "12", "178"]
        bus, tram, cancelled = out
        assert bus["delay_seconds"] == 90 and bus["realtime"] is True
        assert datetime.fromisoformat(bus["estimated_time"]) - datetime.fromisoformat(bus["theoretical_time"]) == timedelta(seconds=90)
        assert tram["vehicle_type"] == "tram" and tram["realtime"] is False
        assert cancelled["cancelled"] is True
        assert all("_brigade" not in d and "_scheduled_ms" not in d for d in out)

    @pytest.mark.asyncio
    async def test_positions_failure_keeps_departures(self):
        result = await _run(_coord("bonarka-ska02"), [_dep("178", 5, brigade="06")], RuntimeError("down"))
        assert len(result["departures"]) == 1
        assert "vehicle_lat" not in result["departures"][0]


@pytest.mark.krakow
class TestVehicleMatching:
    @pytest.mark.asyncio
    async def test_brigade_match_only_on_next_pass_within_horizon(self):
        deps = [_dep("178", 5, brigade="06"), _dep("178", 45, brigade="06"), _dep("178", 300, brigade="01")]
        positions = [_pos("MM837", "178", "06", location=(19.9, 50.0)), _pos("MM860", "178", "01")]
        out = (await _run(_coord("bonarka-ska02"), deps, positions))["departures"]
        assert out[0]["vehicle_code"] == "MM837"
        assert (out[0]["vehicle_lng"], out[0]["vehicle_lat"]) == (19.9, 50.0)
        assert out[0]["vehicle_model"] == "MAN Lion's City"
        assert "vehicle_code" not in out[1]  # same vehicle, later trip
        assert "vehicle_code" not in out[2]  # beyond the matching horizon

    @pytest.mark.asyncio
    async def test_tram_matched_by_upcoming_stop_and_time(self):
        dep = _dep("12", 4, route_type=0, headsign="Os.Piastów")
        positions = [
            _pos("RG908", "12", vtype="0", upcoming=[("Czerwone Maki P+R", dep["scheduledDeparture"])]),
            _pos("RG907", "12", vtype="0", upcoming=[("Czerwone Maki P+R", dep["scheduledDeparture"] + 20 * MIN)]),
        ]
        out = (await _run(_coord("czerwone-maki-p-r01"), [dep], positions))["departures"]
        assert out[0]["vehicle_code"] == "RG908"

    @pytest.mark.asyncio
    async def test_ambiguous_brigade_is_not_matched(self):
        positions = [_pos("PR545", "125", "01C"), _pos("PR546", "125", "01C")]
        out = (await _run(_coord("bonarka-ska02"), [_dep("125", 5, brigade="01C")], positions))["departures"]
        assert "vehicle_code" not in out[0]
