"""Tests for the merged hub sensor."""

from types import SimpleNamespace

import pytest

from mzkzg_transport.sensor import PolishAggregatedSensor


def _coordinator(stop_id, departures, provider="ztm_gdansk", walking=None, alerts=None, alerts_city=None):
    data = {
        "stop_id": stop_id,
        "stop_name": f"Stop {stop_id}",
        "provider": provider,
        "last_update": "2026-05-14T09:00:00+02:00",
        "departures": departures,
    }
    if walking is not None:
        data.update(walking)
    if alerts is not None:
        data["alerts"] = alerts
    if alerts_city is not None:
        data["alerts_city"] = alerts_city
    return SimpleNamespace(
        stop_id=stop_id,
        provider=provider,
        data=data,
        last_update_success=True,
        async_refresh=None,
    )


def _departure(route, time, realtime=False, headsign="Centrum"):
    return {
        "route": route,
        "headsign": headsign,
        "estimated_time": time,
        "realtime": realtime,
    }


def _sensor(coordinators):
    entry = SimpleNamespace(data={"provider": coordinators[0].provider}, entry_id="e1")
    return PolishAggregatedSensor(coordinators, entry)


def test_merged_departures_sorts_and_deduplicates():
    sensor = _sensor(
        [
            _coordinator(
                "1",
                [
                    _departure("10", "2026-05-14T09:10:00"),
                    _departure("10", "2026-05-14T09:10:00", realtime=True),
                ],
            ),
            _coordinator(
                "2",
                [_departure("6", "2026-05-14T09:05:00")],
            ),
        ]
    )

    departures = sensor._merged_departures()

    assert [d["route"] for d in departures] == ["6", "10"]
    assert departures[-1]["realtime"] is True


@pytest.mark.asyncio
async def test_merged_departures_is_cached_until_refresh():
    first = _coordinator("1", [_departure("10", "2026-05-14T09:10:00")])
    sensor = _sensor([first])

    assert sensor._merged_departures()[0]["route"] == "10"
    first.data["departures"] = [_departure("20", "2026-05-14T09:20:00")]
    assert sensor._merged_departures()[0]["route"] == "10"
    assert sensor._merged_cache[0]["route"] == "10"

    # A coordinator refresh clears the cache.
    first.async_refresh = _async_noop
    await sensor.async_update()
    assert sensor._merged_departures()[0]["route"] == "20"


async def _async_noop():
    return None


def test_attributes_use_first_stop_and_minimum_walking_distance():
    sensor = _sensor(
        [
            _coordinator(
                "1",
                [_departure("10", "2026-05-14T09:10:00")],
                walking={"walking_distance_m": 300, "walking_time_min": 4},
            ),
            _coordinator(
                "2",
                [_departure("6", "2026-05-14T09:05:00")],
                walking={"walking_distance_m": 120, "walking_time_min": 2},
            ),
        ]
    )

    attrs = sensor.extra_state_attributes

    assert attrs["stop_id"] == "1|2"
    assert attrs["stop_name"] == "Stop 1"
    assert attrs["walking_distance_m"] == 120
    assert attrs["walking_time_min"] == 2
    assert len(attrs["departures"]) == 2


def test_attributes_include_deduplicated_alerts():
    alert = {
        "id": "11936",
        "title": "Awaryjna zmiana trasy linii 195",
        "content": "Objazd",
        "lines": ["195"],
    }
    sensor = _sensor(
        [
            _coordinator("1", [], alerts=[alert]),
            _coordinator("2", [], alerts=[dict(alert)]),
            _coordinator("3", [], alerts=[{**alert, "id": "other", "title": "Inny"}]),
        ]
    )

    attrs = sensor.extra_state_attributes

    assert [item["id"] for item in attrs["alerts"]] == ["11936", "other"]


def test_attributes_include_deduplicated_city_alerts():
    matching = {
        "id": "11936",
        "title": "Awaryjna zmiana trasy linii 195",
        "content": "Objazd",
        "lines": ["195"],
    }
    other = {"id": "other", "title": "Inny komunikat", "content": "X", "lines": ["199"]}
    sensor = _sensor(
        [
            _coordinator("1", [], alerts=[matching], alerts_city=[matching, other]),
            _coordinator("2", [], alerts=[], alerts_city=[dict(other)]),
        ]
    )

    attrs = sensor.extra_state_attributes

    assert [item["id"] for item in attrs["alerts"]] == ["11936"]
    assert [item["id"] for item in attrs["alerts_city"]] == ["11936", "other"]


def test_native_value_is_first_departure_time():
    sensor = _sensor(
        [
            _coordinator(
                "1",
                [
                    _departure("10", "2026-05-14T09:10:00"),
                    _departure("6", "2026-05-14T09:05:00"),
                ],
            )
        ]
    )
    assert sensor.native_value == "2026-05-14T09:05:00"


def test_available_when_any_coordinator_succeeded():
    ok = _coordinator("1", [])
    failed = _coordinator("2", [])
    failed.last_update_success = False
    assert _sensor([ok, failed]).available is True
    assert _sensor([failed]).available is False
