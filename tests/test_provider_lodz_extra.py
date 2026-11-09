"""Additional unit coverage for MPK Łódź helpers."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from google.transit import gtfs_realtime_pb2

from mzkzg_transport import provider_lodz
from mzkzg_transport.provider_lodz import (
    _deduplicate_prefer_rt,
    _enrich_lodz_vehicle_positions,
    _fetch_delays,
    _fetch_stop_board,
    _get_gtfs_stop_departures,
)

NOW = datetime(2026, 11, 9, 12, 0, 0)


class FakeResponse:
    def __init__(self, raw=b"", status=200):
        self._raw = raw
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def read(self):
        return self._raw


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_deduplicate_prefers_realtime_and_empty_headsign():
    departures = [
        {"route": "6", "headsign": "Jelitkowo", "theoretical_time": "2026-11-09T12:30:00", "realtime": False},
        {"route": "6", "headsign": "Jelitkowo", "theoretical_time": "2026-11-09T12:30:00", "realtime": True},
        {"route": "7", "headsign": "Nowy Port", "theoretical_time": "2026-11-09T12:40:00", "realtime": False},
        {"route": "7", "headsign": "", "theoretical_time": "2026-11-09T12:40:00", "realtime": False},
    ]

    result = _deduplicate_prefer_rt(departures)

    assert len(result) == 2
    assert result[0]["realtime"] is True
    assert result[1]["headsign"] == "Nowy Port"


@pytest.mark.asyncio
async def test_fetch_stop_board_parses_name(monkeypatch):
    async def fake_fetch(session, url, **kwargs):
        return '<Timetable><Stop name="Płocka"><Day><R nr="6"/></Day></Stop></Timetable>'

    monkeypatch.setattr(provider_lodz, "fetch_with_retry", fake_fetch)

    text, name = await _fetch_stop_board(object(), "205", "4")

    assert "Płocka" in text
    assert name == "Płocka"


@pytest.mark.asyncio
async def test_fetch_stop_board_rejects_empty_and_broken_xml(monkeypatch):
    async def empty_fetch(session, url, **kwargs):
        return "   "

    monkeypatch.setattr(provider_lodz, "fetch_with_retry", empty_fetch)
    assert await _fetch_stop_board(object(), "1", "1") is None

    async def broken_fetch(session, url, **kwargs):
        return "<Stop"

    monkeypatch.setattr(provider_lodz, "fetch_with_retry", broken_fetch)
    assert await _fetch_stop_board(object(), "1", "1") is None


def test_get_gtfs_stop_departures_filters_past_and_far_future():
    gtfs = {
        "stop_times": {
            "100": [
                {"trip_id": "t1", "route_id": "r1", "departure_time": (12, 30, 0)},
                {"trip_id": "t2", "route_id": "r1", "departure_time": (11, 0, 0)},
                {"trip_id": "t3", "route_id": "r1", "departure_time": (20, 0, 0)},
            ]
        },
        "routes": {"r1": {"short_name": "6", "type": "tram"}},
        "trips": {"t1": {"headsign": "Jelitkowo"}},
    }

    result = _get_gtfs_stop_departures(
        gtfs, "100", NOW, SimpleNamespace(provider="mpk_lodz")
    )

    assert len(result) == 1
    assert result[0]["route"] == "6"
    assert result[0]["headsign"] == "Jelitkowo"
    assert result[0]["vehicle_type"] == "tram"
    assert result[0]["estimated_time"] == (NOW + timedelta(minutes=30)).isoformat()


@pytest.mark.asyncio
async def test_fetch_delays_reads_trip_updates():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "e1"
    entity.trip_update.trip.route_id = "6"
    stop = entity.trip_update.stop_time_update.add()
    stop.stop_id = "100"
    stop.departure.delay = 120

    session = FakeSession(FakeResponse(feed.SerializeToString()))

    delays = await _fetch_delays(session)

    assert delays == {("6", "100"): 120}


@pytest.mark.asyncio
async def test_fetch_delays_returns_empty_for_error_or_non_200():
    session = FakeSession(FakeResponse(b"", status=500))
    assert await _fetch_delays(session) == {}

    session = FakeSession(FakeResponse(b"not-a-protobuf"))
    assert await _fetch_delays(session) == {}


@pytest.mark.asyncio
async def test_enrich_lodz_vehicle_positions_matches_code():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "e1"
    entity.vehicle.vehicle.id = "depot/1234"
    entity.vehicle.position.latitude = 51.75
    entity.vehicle.position.longitude = 19.45
    entity.vehicle.position.bearing = 180
    entity.vehicle.position.speed = 10

    departures = [{"vehicle_code": "1234"}, {"vehicle_code": "9999"}]
    await _enrich_lodz_vehicle_positions(
        FakeSession(FakeResponse(feed.SerializeToString())), departures
    )

    assert departures[0]["vehicle_lat"] == pytest.approx(51.75)
    assert departures[0]["vehicle_lng"] == pytest.approx(19.45)
    assert departures[0]["vehicle_direction"] == 180
    assert departures[0]["vehicle_speed"] == 36
    assert "vehicle_lat" not in departures[1]


@pytest.mark.asyncio
async def test_enrich_lodz_vehicle_positions_skips_without_codes():
    departures = [{"vehicle_code": ""}]
    session = FakeSession(FakeResponse(b""))
    await _enrich_lodz_vehicle_positions(session, departures)

    assert session.calls == []
