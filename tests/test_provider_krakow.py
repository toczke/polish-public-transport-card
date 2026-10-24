"""Tests for the Kraków provider (zbiorkom.live api6-open)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import pytest

from mzkzg_transport.const import DOMAIN, PROVIDER_KRAKOW
from mzkzg_transport.provider_krakow import (
    DEFAULT_BBOX,
    STOPS_MISS_REFRESH,
    STOPS_RETRY_AFTER,
    STOPS_TTL,
    _legacy_key,
    fetch,
)

NOW = datetime(2026, 10, 5, 21, 50, 0, tzinfo=timezone(timedelta(hours=2)))
NOW_MS = int(NOW.timestamp() * 1000)
MIN = 60 * 1000

STOPS = {"stops": [
    ["bonarka-ska02-xruaf", "krakow", "Bonarka SKA", "02", [19.945, 50.029], [3], 35, "Podgórze SKA", [], []],
    ["czerwone-maki-p+r01-vrfpw", "krakow", "Czerwone Maki P+R", "01", [19.889, 50.018], [0], 133, "", [], []],
]}
NEW_STOP = ["nowy-przystanek01-abcde", "krakow", "Nowy Przystanek", "01", [19.9, 50.0], [3], 1, "", [], []]
# Ids the departures endpoint knows, whatever the stop list currently says
KNOWN = {row[0] for row in STOPS["stops"]} | {NEW_STOP[0]}


def _dep(route, minutes, brigade=None, route_type=3, delay=0, realtime=True, cancelled=False,
         headsign="Mistrzejowice", now_ms=NOW_MS):
    trip = {"route": {"id": route, "name": route, "agency": "default", "type": route_type, "color": "#296d00"},
            "headsign": headsign}
    if brigade is not None:
        trip["brigade"] = brigade
    return {"trip": trip, "scheduledDeparture": now_ms + minutes * MIN, "delay": delay,
            "isRealtime": realtime, "isCancelled": cancelled}


def _pos(vid, route, brigade="", upcoming=(), vtype="3", location=(19.95, 50.03), headsign="X"):
    return {"vehicle": {"id": vid, "type": vtype, "agency": "default", "model": "MAN Lion's City"},
            "routeName": route, "brigade": brigade, "location": list(location), "bearing": 90,
            "headsign": headsign, "upcomingStops": [
                {"sequence": i, "name": name, "scheduledArrival": t, "scheduledDeparture": t}
                for i, (name, t) in enumerate(upcoming)]}


def _coord(stop_id, hass_data=None):
    coord = MagicMock()
    coord.provider = "zbiorkom_krakow"
    coord.stop_id = stop_id
    coord.stop_name = None
    coord.hass.data = hass_data if hass_data is not None else {"mzkzg_transport": {}}
    coord._get_session = AsyncMock(return_value=MagicMock())
    coord.config_entry = None
    return coord


def _fake_fetch(departures=(), positions=(), calls=None, stops=STOPS):
    async def fake_fetch(session, url, timeout=15, as_text=False):
        if calls is not None:
            calls.append(url)
        if url.endswith("/stops"):
            if isinstance(stops, Exception):
                raise stops
            return stops
        if "/stops/" in url:
            if unquote(url.split("/stops/")[1].split("?")[0]) not in KNOWN:
                raise RuntimeError("404 STOP_NOT_FOUND")
            return {"departures": list(departures)}
        if "/positions/" in url:
            if isinstance(positions, Exception):
                raise positions
            return {"positions": list(positions)}
        raise AssertionError(url)
    return fake_fetch


async def _run(coord, departures=(), positions=(), calls=None, stops=STOPS, now=NOW, clock=None):
    """Run fetch() against a fake API; `clock` is a one-item list holding time.monotonic()."""
    fake_time = SimpleNamespace(monotonic=lambda: clock[0]) if clock is not None else None
    with patch("mzkzg_transport.provider_krakow.fetch_with_retry",
               side_effect=_fake_fetch(departures, positions, calls, stops)), \
            patch("mzkzg_transport.provider_krakow.dt_util") as mock_dt, \
            patch("mzkzg_transport.provider_krakow.time", fake_time or __import__("time")):
        mock_dt.now.return_value = now
        return await fetch(coord)


def _count(calls, suffix):
    return sum(u.endswith(suffix) for u in calls)


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
    async def test_unknown_stop_fails_the_update(self):
        calls = []
        with pytest.raises(RuntimeError, match="STOP_NOT_FOUND"):
            await _run(_coord("nieistniejacy01"), [_dep("178", 5)], [], calls)
        assert _count(calls, "/stops") == 1  # a fresh list isn't refetched for a miss

    @pytest.mark.asyncio
    async def test_stop_list_is_fetched_once_per_hass(self):
        hass_data = {"mzkzg_transport": {}}
        calls = []
        await _run(_coord("bonarka-ska02", hass_data), [], [], calls)
        await _run(_coord("czerwone-maki-p-r01", hass_data), [], [], calls)
        assert _count(calls, "/stops") == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("stops", [RuntimeError("down"), {"error": "INTERNAL"}, {"stops": []}])
    async def test_stop_list_unavailable_queries_configured_id_and_backs_off(self, stops):
        hass_data, calls, clock = {"mzkzg_transport": {}}, [], [1000.0]
        result = await _run(_coord("bonarka-ska02-xruaf", hass_data), [_dep("178", 5)], [], calls, stops, clock=clock)
        assert len(result["departures"]) == 1
        assert any(u.endswith("/stops/bonarka-ska02-xruaf?limit=20") for u in calls)

        clock[0] += 30
        await _run(_coord("czerwone-maki-p+r01-vrfpw", hass_data), [_dep("12", 5)], [], calls, stops, clock=clock)
        assert _count(calls, "/stops") == 1

        clock[0] += STOPS_RETRY_AFTER
        result = await _run(_coord("bonarka-ska02", hass_data), [_dep("178", 5)], [], calls, clock=clock)
        assert _count(calls, "/stops") == 2
        assert result["stop_name"] == "Bonarka SKA 02"

    @pytest.mark.asyncio
    async def test_stale_index_is_served_after_failed_refresh_without_retrying_every_poll(self):
        hass_data, calls, clock = {"mzkzg_transport": {}}, [], [1000.0]
        await _run(_coord("bonarka-ska02", hass_data), [], [], calls, clock=clock)
        clock[0] += STOPS_TTL + 1
        result = await _run(_coord("bonarka-ska02", hass_data), [_dep("178", 5)], [], calls,
                            RuntimeError("down"), clock=clock)
        assert result["stop_name"] == "Bonarka SKA 02" and len(result["departures"]) == 1
        clock[0] += 30
        await _run(_coord("bonarka-ska02", hass_data), [], [], calls, RuntimeError("down"), clock=clock)
        assert _count(calls, "/stops") == 2

    @pytest.mark.asyncio
    async def test_id_missing_from_cached_list(self):
        hass_data, calls, clock = {"mzkzg_transport": {}}, [], [1000.0]
        await _run(_coord("bonarka-ska02", hass_data), [], [], calls, clock=clock)
        with_new = {"stops": STOPS["stops"] + [NEW_STOP]}

        # Young list: asked for directly, no refresh
        clock[0] += 60
        result = await _run(_coord(NEW_STOP[0], hass_data), [_dep("178", 5)], [], calls, with_new, clock=clock)
        assert len(result["departures"]) == 1
        assert _count(calls, "/stops") == 1

        # Older list: refreshed, so the stop gets its name too
        clock[0] += STOPS_MISS_REFRESH
        result = await _run(_coord(NEW_STOP[0], hass_data), [_dep("178", 5)], [], calls, with_new, clock=clock)
        assert result["stop_name"] == "Nowy Przystanek 01"
        assert _count(calls, "/stops") == 2


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
        assert all(not k.startswith("_") for d in out for k in d)

    @pytest.mark.asyncio
    async def test_sorted_by_time_across_dst_fall_back(self):
        # 01:55 CEST on 2026-10-25: +45 min is 02:40+02:00, +75 min is 02:10+01:00
        now = datetime(2026, 10, 25, 1, 55, tzinfo=ZoneInfo("Europe/Warsaw"))
        now_ms = int(now.timestamp() * 1000)
        deps = [_dep("178", 75, now_ms=now_ms), _dep("179", 45, now_ms=now_ms),
                _dep("180", 50, delay=20 * MIN, now_ms=now_ms)]
        out = (await _run(_coord("bonarka-ska02"), deps, [], now=now))["departures"]
        # 180 is due 02:45+02:00, 20 min late: 02:05+01:00, between the other two
        assert [d["route"] for d in out] == ["179", "180", "178"]
        assert [d["estimated_time"][11:] for d in out] == ["02:40:00+02:00", "02:05:00+01:00", "02:10:00+01:00"]
        assert out[1]["theoretical_time"][11:] == "02:45:00+02:00"

    @pytest.mark.asyncio
    async def test_departed_filter_uses_real_time_in_repeated_hour(self):
        # 02:20+01:00 (second pass): 02:50+02:00 left 30 minutes ago, though its wall clock is later
        now = datetime(2026, 10, 25, 2, 20, fold=1, tzinfo=ZoneInfo("Europe/Warsaw"))
        now_ms = int(now.timestamp() * 1000)
        out = (await _run(_coord("bonarka-ska02"), [_dep("178", -30, now_ms=now_ms)], [], now=now))["departures"]
        assert out == []

    @pytest.mark.asyncio
    async def test_positions_failure_keeps_departures(self):
        result = await _run(_coord("bonarka-ska02"), [_dep("178", 5, brigade="06")], RuntimeError("down"))
        assert len(result["departures"]) == 1
        assert "vehicle_lat" not in result["departures"][0]

    @pytest.mark.asyncio
    async def test_positions_failure_is_not_retried_by_every_stop(self):
        hass_data, calls = {"mzkzg_transport": {}}, []
        for stop_id in ("bonarka-ska02", "czerwone-maki-p-r01", "bonarka-ska02"):
            await _run(_coord(stop_id, hass_data), [_dep("178", 5, brigade="06")], RuntimeError("down"), calls)
        assert sum("/positions/" in u for u in calls) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("deps", [[], [_dep("178", 300, brigade="06")]])
    async def test_positions_skipped_when_nothing_can_be_matched(self, deps):
        calls = []
        await _run(_coord("bonarka-ska02"), deps, [_pos("MM837", "178", "06")], calls)
        assert not any("/positions/" in u for u in calls)

    @pytest.mark.asyncio
    async def test_positions_box_covers_every_stop(self):
        calls = []
        await _run(_coord("bonarka-ska02"), [_dep("178", 5)], [], calls)
        assert any(u.endswith("/positions/19.869,49.998,19.965,50.049") for u in calls)

        calls = []
        await _run(_coord("bonarka-ska02-xruaf"), [_dep("178", 5)], [], calls, RuntimeError("down"))
        assert any(u.endswith(f"/positions/{DEFAULT_BBOX}") for u in calls)


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
    async def test_tram_matched_by_upcoming_stop_time_and_headsign(self):
        dep = _dep("12", 4, route_type=0, headsign="Os.Piastów")
        t = dep["scheduledDeparture"]
        positions = [
            _pos("RG908", "12", vtype="0", headsign="Os.Piastów", upcoming=[("Czerwone Maki P+R", t)]),
            _pos("RG907", "12", vtype="0", headsign="Os.Piastów", upcoming=[("Czerwone Maki P+R", t + 20 * MIN)]),
            # Same route and time at a same-named stop, other direction
            _pos("RG909", "12", vtype="0", headsign="Czerwone Maki P+R", upcoming=[("Czerwone Maki P+R", t)]),
        ]
        out = (await _run(_coord("czerwone-maki-p-r01"), [dep], positions))["departures"]
        assert out[0]["vehicle_code"] == "RG908"

    @pytest.mark.asyncio
    async def test_ambiguous_stop_time_is_not_matched(self):
        dep = _dep("12", 4, route_type=0, headsign="Os.Piastów")
        upcoming = [("Czerwone Maki P+R", dep["scheduledDeparture"])]
        positions = [_pos(vid, "12", vtype="0", headsign="Os.Piastów", upcoming=upcoming) for vid in ("RG908", "RG909")]
        out = (await _run(_coord("czerwone-maki-p-r01"), [dep], positions))["departures"]
        assert "vehicle_code" not in out[0]

    @pytest.mark.asyncio
    async def test_ambiguous_brigade_is_not_matched(self):
        positions = [_pos("PR545", "125", "01C"), _pos("PR546", "125", "01C")]
        out = (await _run(_coord("bonarka-ska02"), [_dep("125", 5, brigade="01C")], positions))["departures"]
        assert "vehicle_code" not in out[0]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad", [
        {"vehicle": "RF305", "routeName": "178", "brigade": "06", "location": [19.9, 50.0], "upcomingStops": [None]},
        {"vehicle": {}, "routeName": "178", "brigade": ["06"], "location": [19.9, 50.0]},  # unhashable brigade
        "junk",
        {"location": "19.9,50.0"},
    ])
    async def test_malformed_positions_keep_departures(self, bad):
        out = (await _run(_coord("bonarka-ska02"), [_dep("178", 5, brigade="06")], [bad]))["departures"]
        assert len(out) == 1 and "vehicle_code" not in out[0]


def _entry(stop_id):
    return SimpleNamespace(
        entry_id="e1",
        unique_id=f"{PROVIDER_KRAKOW}_{stop_id}",
        data={"provider": PROVIDER_KRAKOW, "stop_id": stop_id, "name": "Bonarka"},
    )


async def _run_with_entry(stop_id, stops=STOPS, existing_entity=None):
    """Run fetch() for a coordinator set up from a config entry, with mocked registries."""
    entry = _entry(stop_id)
    coord = _coord(stop_id)
    coord.config_entry = entry
    coord.hass.config_entries.async_entries.return_value = [entry]
    old_uid = f"{DOMAIN}_{PROVIDER_KRAKOW}_{stop_id}"
    ent_reg = MagicMock()
    ent_reg.async_get_entity_id.side_effect = lambda domain, platform, uid: "sensor.x" if uid == existing_entity else None
    registered = [SimpleNamespace(entity_id="sensor.bonarka_odjazdy", unique_id=old_uid),
                  SimpleNamespace(entity_id="binary_sensor.bonarka_opoznienie", unique_id=f"{old_uid}_delay"),
                  SimpleNamespace(entity_id="sensor.other", unique_id=f"{DOMAIN}_{PROVIDER_KRAKOW}_multi_e1")]
    dev_reg = MagicMock()
    devices = [SimpleNamespace(id="dev1", identifiers={(DOMAIN, f"{PROVIDER_KRAKOW}_{stop_id}")})]
    with patch("mzkzg_transport.provider_krakow.er.async_get", return_value=ent_reg), \
            patch("mzkzg_transport.provider_krakow.er.async_entries_for_config_entry", return_value=registered), \
            patch("mzkzg_transport.provider_krakow.dr.async_get", return_value=dev_reg), \
            patch("mzkzg_transport.provider_krakow.dr.async_entries_for_config_entry", return_value=devices):
        result = await _run(coord, [_dep("178", 5)], [], stops=stops)
    return result, coord, entry, ent_reg, dev_reg


@pytest.mark.krakow
class TestLegacyIdSwitch:
    @pytest.mark.asyncio
    async def test_legacy_id_is_switched_with_entities_and_device(self):
        result, coord, entry, ent_reg, dev_reg = await _run_with_entry("bonarka-ska02")
        new_uid = f"{DOMAIN}_{PROVIDER_KRAKOW}_bonarka-ska02-xruaf"
        assert ent_reg.async_update_entity.call_args_list == [
            ((("sensor.bonarka_odjazdy",), {"new_unique_id": new_uid})),
            ((("binary_sensor.bonarka_opoznienie",), {"new_unique_id": f"{new_uid}_delay"})),
        ]
        dev_reg.async_update_device.assert_called_once_with(
            "dev1", new_identifiers={(DOMAIN, f"{PROVIDER_KRAKOW}_bonarka-ska02-xruaf")})
        coord.hass.config_entries.async_update_entry.assert_called_once_with(
            entry, data={**entry.data, "stop_id": "bonarka-ska02-xruaf"},
            unique_id=f"{PROVIDER_KRAKOW}_bonarka-ska02-xruaf")
        assert coord.stop_id == "bonarka-ska02-xruaf"  # entities created after this refresh use it
        assert len(result["departures"]) == 1

    @pytest.mark.asyncio
    async def test_api6_id_is_not_switched(self):
        _, coord, _, ent_reg, _ = await _run_with_entry("bonarka-ska02-xruaf")
        ent_reg.async_update_entity.assert_not_called()
        coord.hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_legacy_id_waits_for_the_stop_list(self):
        # Without the list the old id can't be resolved (it 404s directly); switched on a later update
        with pytest.raises(RuntimeError, match="STOP_NOT_FOUND"):
            await _run_with_entry("bonarka-ska02", RuntimeError("down"))

    @pytest.mark.asyncio
    async def test_stop_already_added_again_under_api6_id_is_left_alone(self):
        result, coord, _, ent_reg, _ = await _run_with_entry(
            "bonarka-ska02", existing_entity=f"{DOMAIN}_{PROVIDER_KRAKOW}_bonarka-ska02-xruaf")
        ent_reg.async_update_entity.assert_not_called()
        coord.hass.config_entries.async_update_entry.assert_not_called()
        assert coord.stop_id == "bonarka-ska02" and len(result["departures"]) == 1

    @pytest.mark.asyncio
    async def test_failed_switch_keeps_departures(self):
        coord = _coord("bonarka-ska02")
        coord.config_entry = _entry("bonarka-ska02")
        with patch("mzkzg_transport.provider_krakow.er.async_get", side_effect=RuntimeError("registry")):
            result = await _run(coord, [_dep("178", 5)], [])
        assert coord.stop_id == "bonarka-ska02" and len(result["departures"]) == 1
