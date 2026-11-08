"""Tests for departure deduplication in the coordinator."""

from mzkzg_transport.coordinator import PolishTransportCoordinator


def _dedup(deps):
    return PolishTransportCoordinator._deduplicate_prefer_rt(deps)


def test_prefix_headsigns_are_merged_into_one_departure():
    deps = [
        {
            "route": "3",
            "headsign": "Brzeźno",
            "theoretical_time": "2026-11-06T21:22:00+01:00",
            "estimated_time": "2026-11-06T21:22:00+01:00",
            "realtime": False,
            "trip_id": 102,
            "route_id_int": 3,
            "vehicle_code": "",
        },
        {
            "route": "3",
            "headsign": "Brzeźno Dom Zdrojowy",
            "theoretical_time": "2026-11-06T21:22:00+01:00",
            "estimated_time": "2026-11-06T21:22:00+01:00",
            "realtime": False,
        },
    ]
    result = _dedup(deps)
    assert len(result) == 1
    assert result[0]["headsign"] == "Brzeźno Dom Zdrojowy"
    assert result[0]["trip_id"] == 102
    assert result[0]["route_id_int"] == 3


def test_different_destinations_at_same_time_are_kept():
    deps = [
        {
            "route": "3",
            "headsign": "Brzeźno",
            "theoretical_time": "2026-11-06T21:22:00+01:00",
        },
        {
            "route": "3",
            "headsign": "Nowy Port",
            "theoretical_time": "2026-11-06T21:22:00+01:00",
        },
    ]
    assert len(_dedup(deps)) == 2


def test_realtime_row_wins_and_keeps_schedule_metadata():
    deps = [
        {
            "route": "6",
            "headsign": "Jelitkowo",
            "theoretical_time": "2026-11-06T21:22:00+01:00",
            "estimated_time": "2026-11-06T21:25:00+01:00",
            "realtime": True,
            "delay_seconds": 180,
            "vehicle_code": "1015",
        },
        {
            "route": "6",
            "headsign": "Jelitkowo",
            "theoretical_time": "2026-11-06T21:22:00+01:00",
            "estimated_time": "2026-11-06T21:22:00+01:00",
            "realtime": False,
            "trip_id": 777,
        },
    ]
    result = _dedup(deps)
    assert len(result) == 1
    assert result[0]["realtime"] is True
    assert result[0]["vehicle_code"] == "1015"
    assert result[0]["trip_id"] == 777
    assert result[0]["delay_seconds"] == 180


def test_empty_headsign_matches_any_headsign():
    deps = [
        {
            "route": "2",
            "headsign": "",
            "theoretical_time": "2026-11-06T08:30:00",
            "realtime": False,
        },
        {
            "route": "2",
            "headsign": "Jelitkowo",
            "theoretical_time": "2026-11-06T08:30:00",
            "realtime": True,
        },
    ]
    result = _dedup(deps)
    assert len(result) == 1
    assert result[0]["headsign"] == "Jelitkowo"
    assert result[0]["realtime"] is True
