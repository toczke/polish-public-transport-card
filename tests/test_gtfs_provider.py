"""Tests for the MZK Wejherowo static GTFS parser."""

import io
import zipfile
from datetime import datetime

from mzkzg_transport.gtfs_provider import GtfsData


def _zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _gtfs_zip(stop_time: str = "09:10:00") -> bytes:
    return _zip(
        {
            "stops.txt": "stop_id,stop_name,stop_code\nS1,Rynek,101\nS2,Dworzec,102\n",
            "routes.txt": "route_id,route_short_name,route_long_name,route_color\n"
            "R1,10,Linia 10,FF0000\n",
            "trips.txt": "trip_id,route_id,service_id,trip_headsign\n"
            "T1,R1,SVC1,Centrum\n",
            "calendar_dates.txt": "service_id,date,exception_type\nSVC1,20260514,1\n",
            "stop_times.txt": "trip_id,stop_id,departure_time,stop_sequence\n"
            f"T1,S1,{stop_time},1\n"
            "T1,S2,09:30:00,2\n",
        }
    )


def test_parse_zip_populates_all_tables():
    gtfs = GtfsData()
    gtfs.parse_zip(_gtfs_zip())

    assert gtfs.loaded is True
    assert gtfs.stops["S1"]["name"] == "Rynek"
    assert gtfs.routes["R1"]["short_name"] == "10"
    assert gtfs.trips["T1"]["headsign"] == "Centrum"
    assert gtfs.stop_times["S1"][0]["departure_time"] == "09:10:00"
    assert "20260514" in gtfs.calendar_dates["SVC1"]


def test_get_departures_filters_past_rows_and_keeps_last_minute():
    gtfs = GtfsData()
    gtfs.parse_zip(_gtfs_zip())
    now = datetime(2026, 5, 14, 9, 5, 0)

    departures = gtfs.get_departures("S1", now=now)

    assert len(departures) == 1
    assert departures[0]["route"] == "10"
    assert departures[0]["headsign"] == "Centrum"
    assert departures[0]["estimated_time"] == "2026-05-14T09:10:00"
    assert departures[0]["realtime"] is False


def test_get_departures_handles_after_midnight_times():
    gtfs = GtfsData()
    gtfs.parse_zip(_gtfs_zip(stop_time="25:10:00"))
    now = datetime(2026, 5, 14, 9, 5, 0)

    departures = gtfs.get_departures("S1", now=now)

    assert len(departures) == 1
    assert departures[0]["estimated_time"] == "2026-05-15T01:10:00"


def test_get_departures_returns_empty_before_load():
    assert GtfsData().get_departures("S1") == []
