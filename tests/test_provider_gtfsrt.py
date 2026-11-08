"""Tests for provider_gtfsrt.py."""

import zipfile
from io import BytesIO
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mzkzg_transport.provider_gtfsrt import (
    _get_rt_delays,
    fetch,
)
from mzkzg_transport.gtfsrt_gzm import (
    _calendar_covers,
    _get_gzm_gtfs_url,
    _peek_zip_member,
)
from mzkzg_transport.gtfsrt_parser import (
    _parse_gtfs_zip,
    _parse_stop_times_for,
    _read_csv,
    _parse_rt_feed,
    _parse_gtfsrt_positions,
)


def _make_gtfs_zip(
    calendar=None,
    calendar_dates=None,
    stops=None,
    routes=None,
    trips=None,
    stop_times=None,
    pad=0,
):
    """Create a minimal in-memory GTFS zip.

    ``pad`` appends an uncompressed filler member so the archive exceeds the tail window
    used by the range-request peek, exercising the sparse-reconstruction path.
    """
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if calendar is not None:
            zf.writestr("calendar.txt", calendar)
        if calendar_dates is not None:
            zf.writestr("calendar_dates.txt", calendar_dates)
        if stops is not None:
            zf.writestr("stops.txt", stops)
        if routes is not None:
            zf.writestr("routes.txt", routes)
        if trips is not None:
            zf.writestr("trips.txt", trips)
        if stop_times is not None:
            zf.writestr("stop_times.txt", stop_times)
        if pad:
            zf.writestr("shapes.txt", "x" * pad)
    return buf.getvalue()


def _today_str():
    return date.today().strftime("%Y%m%d")


def _day_name():
    return ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][date.today().weekday()]


def test_read_csv_streams_rows_from_zip():
    """Large GTFS members are not materialized as a list or decoded string."""
    data = _make_gtfs_zip(stops="stop_id,stop_name\nS1,First\nS2,Second")

    with zipfile.ZipFile(BytesIO(data)) as zf:
        header, rows = _read_csv(zf, "stops.txt")
        assert header == ["stop_id", "stop_name"]
        assert not isinstance(rows, list)
        assert list(rows) == [["S1", "First"], ["S2", "Second"]]


def _calendar_line(service_id, active_today=True):
    """Build a calendar.txt row active today."""
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    today_day = _day_name()
    vals = ["1" if (d == today_day and active_today) or (d != today_day) else "0" for d in days]
    start = "20240101"
    end = "20271231"
    return f"{service_id},{','.join(vals)},{start},{end}"


CALENDAR_HEADER = "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date"


def test_parse_gtfsrt_vehicle_positions_without_pb_url():
    """GTFS-RT position parsing works independently of a URL suffix, as required by GZM."""
    from google.transit import gtfs_realtime_pb2

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "vehicle-GZM-42"
    entity.vehicle.vehicle.id = "operator/GZM-42"
    entity.vehicle.position.latitude = 50.2649
    entity.vehicle.position.longitude = 19.0238
    entity.vehicle.position.bearing = 90
    entity.vehicle.position.speed = 12.5

    positions = _parse_gtfsrt_positions(feed.SerializeToString())

    assert positions == {
        "GZM-42": {
            "lat": pytest.approx(50.2649),
            "lng": pytest.approx(19.0238),
            "bearing": pytest.approx(90),
            "speed": pytest.approx(12.5),
        }
    }


@pytest.mark.gtfsrt
class TestParseGtfsZip:
    """Tests for _parse_gtfs_zip."""

    def test_calendar_filtering_active_service(self):
        """Only trips with active services are included."""
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}\n{_calendar_line('SVC2', False)}"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,Dest1\nT2,R1,SVC2,Dest2"
        routes = "route_id,route_short_name,route_type\nR1,10,3"
        stops = "stop_id,stop_name\nS1,Stop One"

        data = _make_gtfs_zip(calendar=calendar, trips=trips, routes=routes, stops=stops)
        result = _parse_gtfs_zip(data)

        assert "T1" in result["trips"]
        assert "T2" not in result["trips"]

    def test_calendar_filtering_date_range(self):
        """Service outside date range is excluded."""
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        today_day = _day_name()
        vals = ["1" if d == today_day else "0" for d in days]
        # Expired service
        calendar = f"{CALENDAR_HEADER}\nSVC_OLD,{','.join(vals)},20200101,20200301"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC_OLD,Dest"
        routes = "route_id,route_short_name,route_type\nR1,5,3"
        stops = "stop_id,stop_name\nS1,Stop"

        data = _make_gtfs_zip(calendar=calendar, trips=trips, routes=routes, stops=stops)
        result = _parse_gtfs_zip(data)

        assert "T1" not in result["trips"]

    def test_calendar_dates_exception_add(self):
        """calendar_dates exception_type=1 adds a service."""
        # No calendar.txt, only calendar_dates adding SVC1 today
        calendar_dates = f"service_id,date,exception_type\nSVC1,{_today_str()},1"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,Dest"
        routes = "route_id,route_short_name,route_type\nR1,7,3"
        stops = "stop_id,stop_name\nS1,Stop"

        data = _make_gtfs_zip(calendar_dates=calendar_dates, trips=trips, routes=routes, stops=stops)
        result = _parse_gtfs_zip(data)

        assert "T1" in result["trips"]

    def test_calendar_dates_only_filters_out_other_service_days(self):
        """A feed with only calendar_dates must still hide trips from other days.

        zbiorkom.live api6 exports have no calendar.txt. Without the fallback to
        active_services, every trip from every service day leaked into the card
        (issues #32 and #33).
        """
        tomorrow_str = (date.today() + timedelta(days=1)).strftime("%Y%m%d")
        calendar_dates = (
            "service_id,date,exception_type\n"
            f"SVC1,{_today_str()},1\n"
            f"SVC2,{tomorrow_str},1"
        )
        trips = (
            "trip_id,route_id,service_id,trip_headsign\n"
            "T1,R1,SVC1,Today\n"
            "T2,R1,SVC2,Tomorrow"
        )
        routes = "route_id,route_short_name,route_type\nR1,7,3"
        stops = "stop_id,stop_name\nS1,Stop"

        data = _make_gtfs_zip(
            calendar_dates=calendar_dates, trips=trips, routes=routes, stops=stops
        )
        result = _parse_gtfs_zip(data)

        assert "T1" in result["trips"]
        assert "T2" not in result["trips"]

    def test_calendar_dates_exception_remove(self):
        """calendar_dates exception_type=2 removes a service."""
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}"
        calendar_dates = f"service_id,date,exception_type\nSVC1,{_today_str()},2"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,Dest"
        routes = "route_id,route_short_name,route_type\nR1,7,3"
        stops = "stop_id,stop_name\nS1,Stop"

        data = _make_gtfs_zip(calendar=calendar, calendar_dates=calendar_dates, trips=trips, routes=routes, stops=stops)
        result = _parse_gtfs_zip(data)

        assert "T1" not in result["trips"]

    def test_route_type_tram(self):
        """route_type=0 maps to tram."""
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}"
        routes = "route_id,route_short_name,route_type\nR1,1,0\nR2,50,3"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,X"
        stops = "stop_id,stop_name\nS1,Stop"

        data = _make_gtfs_zip(calendar=calendar, routes=routes, trips=trips, stops=stops)
        result = _parse_gtfs_zip(data)

        assert result["routes"]["R1"]["type"] == "tram"
        assert result["routes"]["R2"]["type"] == "bus"


@pytest.mark.gtfsrt
class TestParseStopTimesFor:
    """Tests for _parse_stop_times_for."""

    def _build_gtfs(self, stop_times_txt):
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}"
        stops = "stop_id,stop_name\nS1,Stop One\nS2,Stop Two\nS3,Final Stop"
        routes = "route_id,route_short_name,route_type\nR1,10,3"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,"

        data = _make_gtfs_zip(
            calendar=calendar, stops=stops, routes=routes, trips=trips, stop_times=stop_times_txt
        )
        return _parse_gtfs_zip(data)

    def test_basic_stop_times_parsing(self):
        """Parses departure times for the requested stop."""
        st = "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\nT1,S1,08:30:00,1,\nT1,S2,08:35:00,2,\nT1,S3,08:40:00,3,"
        gtfs = self._build_gtfs(st)
        _parse_stop_times_for(gtfs, "S1")

        entries = gtfs["stop_times"]["S1"]
        assert len(entries) == 1
        assert entries[0]["departure_time"] == (8, 30, 0)
        assert entries[0]["trip_id"] == "T1"
        assert entries[0]["route_id"] == "R1"

    def test_headsign_from_stop_headsign(self):
        """stop_headsign takes priority."""
        st = "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\nT1,S1,09:00:00,1,Custom Headsign\nT1,S3,09:10:00,3,"
        gtfs = self._build_gtfs(st)
        _parse_stop_times_for(gtfs, "S1")

        assert gtfs["stop_times"]["S1"][0]["headsign"] == "Custom Headsign"

    def test_headsign_derived_from_last_stop(self):
        """When no headsign available, derives from last stop name."""
        st = "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\nT1,S1,09:00:00,1,\nT1,S2,09:05:00,2,\nT1,S3,09:10:00,3,"
        gtfs = self._build_gtfs(st)
        _parse_stop_times_for(gtfs, "S1")

        assert gtfs["stop_times"]["S1"][0]["headsign"] == "Final Stop"

    def test_time_over_24h(self):
        """Times like 25:30:00 (next day) are parsed correctly."""
        st = "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\nT1,S1,25:30:00,1,Dest"
        gtfs = self._build_gtfs(st)
        _parse_stop_times_for(gtfs, "S1")

        assert gtfs["stop_times"]["S1"][0]["departure_time"] == (25, 30, 0)

    def test_skips_trips_not_in_active(self):
        """Stop times for inactive trips are skipped."""
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}"
        stops = "stop_id,stop_name\nS1,Stop"
        routes = "route_id,route_short_name,route_type\nR1,10,3"
        # T2 has inactive service — won't be in trips dict
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,Dest\nT2,R1,SVC_INACTIVE,Dest2"
        st = "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\nT1,S1,08:00:00,1,\nT2,S1,08:05:00,1,"

        data = _make_gtfs_zip(calendar=calendar, stops=stops, routes=routes, trips=trips, stop_times=st)
        gtfs = _parse_gtfs_zip(data)
        _parse_stop_times_for(gtfs, "S1")

        assert len(gtfs["stop_times"]["S1"]) == 1
        assert gtfs["stop_times"]["S1"][0]["trip_id"] == "T1"


@pytest.mark.gtfsrt
class TestGetRtDelays:
    """Tests for _get_rt_delays with mocked network."""

    def test_parses_trip_updates(self):
        """Parses protobuf feed into delay dict keyed by trip+stop."""
        mock_stu = MagicMock()
        mock_stu.stop_id = "S1"
        mock_stu.stop_sequence = 3
        mock_stu.HasField = lambda f: f == "departure"
        mock_stu.departure.delay = 120

        mock_vehicle = MagicMock()
        mock_vehicle.id = "V42"
        mock_vehicle.label = ""

        mock_trip_update = MagicMock()
        mock_trip_update.trip.trip_id = "TRIP1"
        mock_trip_update.HasField = lambda f: f == "vehicle"
        mock_trip_update.vehicle = mock_vehicle
        mock_trip_update.stop_time_update = [mock_stu]

        mock_entity = MagicMock()
        mock_entity.HasField = lambda f: f == "trip_update"
        mock_entity.trip_update = mock_trip_update

        mock_feed = MagicMock()
        mock_feed.entity = [mock_entity]

        result = _parse_rt_feed(mock_feed)

        assert result["TRIP1_S1"] == (120, "V42")
        assert result["TRIP1_seq3"] == (120, "V42")
        assert result["TRIP1"] == (120, "V42")
        assert not any(key.startswith("route_") for key in result)

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_error(self):
        """Returns empty dict on non-200 response."""
        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)

        with patch.dict("sys.modules", {"google.transit": MagicMock(), "google.transit.gtfs_realtime_pb2": MagicMock()}):
            result = await _get_rt_delays(mock_session, "http://fake/rt.pb")

        assert result == {}

    def test_fallback_to_arrival_delay(self):
        """Uses arrival delay when departure not present."""
        mock_stu = MagicMock()
        mock_stu.stop_id = "S2"
        mock_stu.stop_sequence = 0
        mock_stu.HasField = lambda f: f == "arrival"
        mock_stu.arrival.delay = 60

        mock_vehicle = MagicMock()
        mock_vehicle.id = ""
        mock_vehicle.label = "BUS99"

        mock_trip_update = MagicMock()
        mock_trip_update.trip.trip_id = "TRIP2"
        mock_trip_update.HasField = lambda f: f == "vehicle"
        mock_trip_update.vehicle = mock_vehicle
        mock_trip_update.stop_time_update = [mock_stu]

        mock_entity = MagicMock()
        mock_entity.HasField = lambda f: f == "trip_update"
        mock_entity.trip_update = mock_trip_update

        mock_feed = MagicMock()
        mock_feed.entity = [mock_entity]

        result = _parse_rt_feed(mock_feed)

        assert result["TRIP2_S2"] == (60, "BUS99")


@pytest.mark.gtfsrt
class TestFetchDeduplication:
    """Tests for deduplication and vehicle enrichment in fetch()."""

    @pytest.mark.asyncio
    async def test_deduplication_same_route_headsign_time(self):
        """Duplicate departures (same route+headsign+estimated minute) are deduped."""
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}"
        stops = "stop_id,stop_name\nS1,My Stop\nS2,End"
        routes = "route_id,route_short_name,route_type\nR1,10,3"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,End\nT2,R1,SVC1,End"
        # Both trips depart at same time from S1
        st = "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\nT1,S1,23:55:00,1,End\nT2,S1,23:55:00,1,End\nT1,S2,23:59:00,2,\nT2,S2,23:59:00,2,"

        data = _make_gtfs_zip(calendar=calendar, stops=stops, routes=routes, trips=trips, stop_times=st)

        coord = MagicMock()
        coord.provider = "gtfsrt_poznan"
        coord.stop_id = "S1"
        coord.stop_name = "My Stop"
        coord.hass.data = {"mzkzg_transport": {}}
        coord.hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        coord._get_session = AsyncMock()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=data)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        coord._get_session = AsyncMock(return_value=mock_session)

        with patch("mzkzg_transport.provider_gtfsrt._get_rt_delays", new_callable=AsyncMock, return_value={}):
            with patch("mzkzg_transport.provider_gtfsrt.dt_util") as mock_dt:
                from datetime import datetime, timezone, timedelta as td
                # Set "now" to 23:50 so 23:55 departures are in the future
                fake_now = datetime(date.today().year, date.today().month, date.today().day, 23, 50, 0, tzinfo=timezone(td(hours=2)))
                mock_dt.now.return_value = fake_now
                result = await fetch(coord)

        # Should be deduped to 1 (today) + possible tomorrow schedule
        assert result["departures"][0]["route"] == "10"
        today_deps = [d for d in result["departures"] if d.get("provider") != "schedule"]
        assert len(today_deps) == 1

    @pytest.mark.asyncio
    async def test_vehicle_capabilities_enrichment(self):
        """Vehicle capabilities from CSV are added to departures."""
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}"
        stops = "stop_id,stop_name\nS1,Stop\nS2,End"
        routes = "route_id,route_short_name,route_type\nR1,5,3"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,End"
        st = "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\nT1,S1,23:55:00,1,End\nT1,S2,23:59:00,2,"

        data = _make_gtfs_zip(calendar=calendar, stops=stops, routes=routes, trips=trips, stop_times=st)

        coord = MagicMock()
        coord.provider = "gtfsrt_poznan"
        coord.stop_id = "S1"
        coord.stop_name = "Stop"
        coord.hass.data = {"mzkzg_transport": {}}
        coord.hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        coord._get_session = AsyncMock()

        mock_resp_gtfs = AsyncMock()
        mock_resp_gtfs.status = 200
        mock_resp_gtfs.read = AsyncMock(return_value=data)
        mock_resp_gtfs.__aenter__ = AsyncMock(return_value=mock_resp_gtfs)
        mock_resp_gtfs.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp_gtfs)
        coord._get_session = AsyncMock(return_value=mock_session)

        # RT delays return a vehicle code
        rt_delays = {"T1_S1": (30, "V100")}

        # Vehicle dict
        veh_dict = {"V100": {"ramp": True, "air_conditioner": True, "place_for_transp_bicycles": False, "ticket_machine": True, "usb_charger": False}}

        with patch("mzkzg_transport.provider_gtfsrt._get_rt_delays", new_callable=AsyncMock, return_value=rt_delays):
            with patch("mzkzg_transport.provider_gtfsrt._get_vehicle_dict", new_callable=AsyncMock, return_value=veh_dict):
                with patch("mzkzg_transport.provider_gtfsrt.dt_util") as mock_dt:
                    from datetime import datetime, timezone, timedelta as td
                    fake_now = datetime(date.today().year, date.today().month, date.today().day, 23, 50, 0, tzinfo=timezone(td(hours=2)))
                    mock_dt.now.return_value = fake_now
                    result = await fetch(coord)

        dep = result["departures"][0]
        assert dep["realtime"] is True
        assert dep["vehicle_code"] == "V100"
        assert dep["wheelchair_accessible"] is True
        assert dep["air_conditioning"] is True
        assert dep["bike_allowed"] is False

    @pytest.mark.asyncio
    async def test_rt_delay_matching_priority(self):
        """RT delay matches by stop_id first, then stop_sequence, then trip_id."""
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}"
        stops = "stop_id,stop_name\nS1,Stop\nS2,End"
        routes = "route_id,route_short_name,route_type\nR1,5,3"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,End\nT2,R1,SVC1,End\nT3,R1,SVC1,End"
        st = (
            "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\n"
            "T1,S1,23:55:00,1,End\n"
            "T2,S1,23:56:00,1,End\n"
            "T3,S1,23:57:00,1,End\n"
            "T1,S2,23:59:00,2,\n"
            "T2,S2,23:59:00,2,\n"
            "T3,S2,23:59:00,2,"
        )

        data = _make_gtfs_zip(calendar=calendar, stops=stops, routes=routes, trips=trips, stop_times=st)

        coord = MagicMock()
        coord.provider = "gtfsrt_poznan"
        coord.stop_id = "S1"
        coord.stop_name = "Stop"
        coord.hass.data = {"mzkzg_transport": {}}
        coord.hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        coord._get_session = AsyncMock()

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=data)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        coord._get_session = AsyncMock(return_value=mock_session)

        # T1 has stop_id match, T2 has seq match, T3 has trip-only match
        rt_delays = {
            "T1_S1": (60, "V1"),       # stop_id match
            "T2_seq1": (90, "V2"),     # stop_sequence match
            "T3": (120, "V3"),          # trip_id fallback
        }

        with patch("mzkzg_transport.provider_gtfsrt._get_rt_delays", new_callable=AsyncMock, return_value=rt_delays):
            with patch("mzkzg_transport.provider_gtfsrt.dt_util") as mock_dt:
                from datetime import datetime, timezone, timedelta as td
                fake_now = datetime(date.today().year, date.today().month, date.today().day, 23, 50, 0, tzinfo=timezone(td(hours=2)))
                mock_dt.now.return_value = fake_now
                result = await fetch(coord)

        deps = {d["delay_seconds"]: d for d in result["departures"]}
        assert 60 in deps   # T1 matched by stop_id
        assert 90 in deps   # T2 matched by stop_sequence
        assert 120 in deps  # T3 matched by trip_id fallback


    @pytest.mark.asyncio
    async def test_route_fallback_does_not_copy_delay_to_later_trips(self):
        """Route-level keys are ignored so later trips keep their schedule (#52)."""
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}"
        stops = "stop_id,stop_name\nS1,Stop\nS2,End"
        routes = "route_id,route_short_name,route_type\nR1,156,3"
        trips = (
            "trip_id,route_id,service_id,trip_headsign\n"
            "T1,R1,SVC1,End\nT2,R1,SVC1,End\nT3,R1,SVC1,End"
        )
        st = (
            "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\n"
            "T1,S1,19:09:00,1,End\n"
            "T2,S1,19:29:00,1,End\n"
            "T3,S1,19:49:00,1,End\n"
            "T1,S2,19:40:00,2,\n"
            "T2,S2,20:00:00,2,\n"
            "T3,S2,20:20:00,2,"
        )
        data = _make_gtfs_zip(calendar=calendar, stops=stops, routes=routes, trips=trips, stop_times=st)

        coord = MagicMock()
        coord.provider = "gtfsrt_poznan"
        coord.stop_id = "S1"
        coord.stop_name = "Stop"
        coord.config_entry = None
        coord.hass = MagicMock()
        coord.hass.data = {"mzkzg_transport": {"_gtfsrt_cache": {}, "_gtfsrt_locks": {}}}
        coord.hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        session = AsyncMock()
        coord._get_session = AsyncMock(return_value=session)

        rt_delays = {
            "T1_S1": (120, "1480"),
            # A legacy route-level key must never leak to T2/T3.
            "route_R1_S1": (999, "BAD"),
            "route_R1": (999, "BAD"),
        }
        with patch("mzkzg_transport.provider_gtfsrt._get_rt_delays", new_callable=AsyncMock, return_value=rt_delays):
            with patch("mzkzg_transport.provider_gtfsrt._download_zip", new_callable=AsyncMock, return_value=data):
                with patch("mzkzg_transport.provider_gtfsrt.dt_util") as mock_dt:
                    fake_now = datetime(date.today().year, date.today().month, date.today().day, 19, 0, 0, tzinfo=timezone(timedelta(hours=2)))
                    mock_dt.now.return_value = fake_now
                    result = await fetch(coord)

        deps = {d["trip_id"]: d for d in result["departures"] if d.get("trip_id")}
        assert deps["T1"]["delay_seconds"] == 120
        assert deps["T1"]["realtime"] is True
        assert deps["T1"]["vehicle_code"] == "1480"
        for trip_id in ("T2", "T3"):
            assert deps[trip_id]["delay_seconds"] == 0
            assert deps[trip_id]["realtime"] is False
            assert deps[trip_id]["vehicle_code"] is None

    @pytest.mark.asyncio
    async def test_negative_delay_at_first_stop_is_clamped(self):
        """A bus waiting at the terminus shows the scheduled time, not a huge negative delay."""
        calendar = f"{CALENDAR_HEADER}\n{_calendar_line('SVC1', True)}"
        stops = "stop_id,stop_name\nS1,Stop\nS2,End"
        routes = "route_id,route_short_name,route_type\nR1,156,3"
        trips = "trip_id,route_id,service_id,trip_headsign\nT1,R1,SVC1,End"
        st = "trip_id,stop_id,departure_time,stop_sequence,stop_headsign\nT1,S1,19:09:00,1,End\nT1,S2,19:40:00,2,"
        data = _make_gtfs_zip(calendar=calendar, stops=stops, routes=routes, trips=trips, stop_times=st)

        coord = MagicMock()
        coord.provider = "gtfsrt_poznan"
        coord.stop_id = "S1"
        coord.stop_name = "Stop"
        coord.config_entry = None
        coord.hass = MagicMock()
        coord.hass.data = {"mzkzg_transport": {"_gtfsrt_cache": {}, "_gtfsrt_locks": {}}}
        coord.hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
        session = AsyncMock()
        coord._get_session = AsyncMock(return_value=session)

        with patch("mzkzg_transport.provider_gtfsrt._get_rt_delays", new_callable=AsyncMock, return_value={"T1_S1": (-1020, "1480")}):
            with patch("mzkzg_transport.provider_gtfsrt._download_zip", new_callable=AsyncMock, return_value=data):
                with patch("mzkzg_transport.provider_gtfsrt.dt_util") as mock_dt:
                    fake_now = datetime(date.today().year, date.today().month, date.today().day, 19, 0, 0, tzinfo=timezone(timedelta(hours=2)))
                    mock_dt.now.return_value = fake_now
                    result = await fetch(coord)

        dep = result["departures"][0]
        assert dep["delay_seconds"] == 0
        assert dep["realtime"] is True
        assert dep["estimated_time"] == dep["theoretical_time"]


CKAN_URL_PREFIX = "https://otwartedane.metropoliagzm.pl/api/3/action/package_show"


class _RangeResponse:
    """Async-context response backing _FakeCkanSession."""

    def __init__(self, session, url, headers):
        self._session = session
        self._url = url
        self._headers = headers or {}
        self.status = 404
        self._body = b""

        if url.startswith(CKAN_URL_PREFIX):
            self.status = 200
            self._json = session.ckan
            return

        blob = session.files.get(url)
        if blob is None:
            return

        rng = self._headers.get("Range")
        if rng and session.supports_ranges:
            start, end = rng.removeprefix("bytes=").split("-")
            start, end = int(start), int(end)
            self._body = blob[start:end + 1]
            self.status = 206
        else:
            # Server ignoring Range: hands back the entire archive.
            self._body = blob
            self.status = 200
        session.bytes_served += len(self._body)

    async def read(self):
        return self._body

    async def json(self):
        return self._json

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeCkanSession:
    """Serves a CKAN package_show payload plus range-readable zip archives."""

    def __init__(self, ckan, files, supports_ranges=True):
        self.ckan = ckan
        self.files = files
        self.supports_ranges = supports_ranges
        self.bytes_served = 0

    def get(self, url, headers=None, **kwargs):
        return _RangeResponse(self, url, headers)


def _calendar_for(service_id, start, end):
    """calendar.txt whose service runs every weekday within [start, end]."""
    return f"{CALENDAR_HEADER}\n{service_id},1,1,1,1,1,1,1,{start},{end}"


def _resource(name, url, size, last_modified):
    return {
        "name": name,
        "url": url,
        "size": size,
        "format": "ZIP",
        "last_modified": last_modified,
    }


@pytest.mark.gtfsrt
class TestGzmGtfsUrl:
    """GZM publishes one archive per service day — pick the one covering today (issue #13)."""

    def _build(self, supports_ranges=True):
        today = date.today()
        future = today + timedelta(days=6)

        # Archive listed first, but its calendar only covers a future week.
        other = _make_gtfs_zip(
            calendar=_calendar_for("8", future.strftime("%Y%m%d"), (future + timedelta(days=1)).strftime("%Y%m%d")),
            pad=200_000,
        )
        # Archive covering today, listed later and published earlier.
        todays = _make_gtfs_zip(
            calendar=_calendar_for("8", _today_str(), _today_str()),
            pad=200_000,
        )

        files = {"http://gzm/other.zip": other, "http://gzm/today.zip": todays}
        ckan = {
            "result": {
                "resources": [
                    {"name": "Specyfikacja.pdf", "url": "http://gzm/spec.pdf", "format": "PDF", "size": 10},
                    _resource("schedule_ZTM_other.zip", "http://gzm/other.zip", len(other), "2026-07-14T16:15:02"),
                    _resource("schedule_ZTM_today.zip", "http://gzm/today.zip", len(todays), "2026-07-14T09:00:00"),
                ]
            }
        }
        return _FakeCkanSession(ckan, files, supports_ranges), files

    @pytest.mark.asyncio
    async def test_picks_archive_covering_target_date(self):
        """Regression #13: the first-listed archive covers a different day, so it must be skipped."""
        session, _ = self._build()

        url = await _get_gzm_gtfs_url(session, "pkg-id", date.today())

        assert url == "http://gzm/today.zip"

    @pytest.mark.asyncio
    async def test_defaults_to_today(self):
        """Omitting target_date resolves to today (the config flow calls it this way)."""
        session, _ = self._build()

        url = await _get_gzm_gtfs_url(session, "pkg-id")

        assert url == "http://gzm/today.zip"

    @pytest.mark.asyncio
    async def test_does_not_download_whole_archives(self):
        """Selection peeks calendar.txt by range instead of pulling every 10 MB archive."""
        session, files = self._build()

        await _get_gzm_gtfs_url(session, "pkg-id", date.today())

        assert session.bytes_served < sum(len(b) for b in files.values())

    @pytest.mark.asyncio
    async def test_falls_back_when_no_archive_covers_date(self):
        """With no matching archive, fall back to the most recently published one."""
        session, _ = self._build()

        url = await _get_gzm_gtfs_url(session, "pkg-id", date.today() + timedelta(days=90))

        assert url == "http://gzm/other.zip"

    @pytest.mark.asyncio
    async def test_works_when_server_ignores_range(self):
        """Servers that ignore Range return the full archive — selection must still work."""
        session, _ = self._build(supports_ranges=False)

        url = await _get_gzm_gtfs_url(session, "pkg-id", date.today())

        assert url == "http://gzm/today.zip"


@pytest.mark.gtfsrt
class TestPeekZipMember:
    """Tests for the range-request zip reader."""

    @pytest.mark.asyncio
    async def test_reads_member_from_large_archive(self):
        """Reads a member sitting outside the tail window without fetching the whole file."""
        calendar = _calendar_for("SVC1", "20240101", "20271231")
        blob = _make_gtfs_zip(calendar=calendar, pad=200_000)
        session = _FakeCkanSession({}, {"http://gzm/a.zip": blob})

        text = await _peek_zip_member(session, "http://gzm/a.zip", len(blob), "calendar.txt")

        assert text.strip() == calendar
        assert session.bytes_served < len(blob)

    @pytest.mark.asyncio
    async def test_missing_member_raises_keyerror(self):
        """A missing member surfaces as KeyError so the caller can skip the candidate."""
        blob = _make_gtfs_zip(stops="stop_id,stop_name\nS1,Stop", pad=200_000)
        session = _FakeCkanSession({}, {"http://gzm/a.zip": blob})

        with pytest.raises(KeyError):
            await _peek_zip_member(session, "http://gzm/a.zip", len(blob), "calendar.txt")


@pytest.mark.gtfsrt
class TestCalendarCovers:
    """Tests for _calendar_covers."""

    def test_true_when_service_runs_on_date(self):
        cal = _calendar_for("8", "20260714", "20260715")
        assert _calendar_covers(cal, date(2026, 7, 14)) is True

    def test_false_outside_date_range(self):
        cal = _calendar_for("8", "20260720", "20260721")
        assert _calendar_covers(cal, date(2026, 7, 14)) is False

    def test_false_when_weekday_not_served(self):
        # 2026-07-14 is a Tuesday; this service runs Mondays only.
        cal = f"{CALENDAR_HEADER}\n8,1,0,0,0,0,0,0,20260101,20261231"
        assert _calendar_covers(cal, date(2026, 7, 14)) is False




@pytest.mark.gtfsrt
def test_apply_positions_route_id_fallback():
    """_apply_positions matches by route_id when vehicle_code is missing (Wrocław-like)."""
    from mzkzg_transport.provider_gtfsrt import _apply_positions

    positions = {
        "bus1": {"lat": 51.1, "lng": 17.0, "route_id": "A"},
        "bus2": {"lat": 51.2, "lng": 17.1, "route_id": "B"},
    }
    deps = [
        {"route": "A", "vehicle_code": ""},   # no vehicle_code → fallback by route
        {"route": "B", "vehicle_code": "bus2"},  # direct match by code
    ]
    _apply_positions(deps, positions)

    assert deps[0]["vehicle_lat"] == pytest.approx(51.1)
    assert deps[0]["vehicle_lng"] == pytest.approx(17.0)
    assert deps[1]["vehicle_lat"] == pytest.approx(51.2)

@pytest.mark.gtfsrt
def test_apply_positions_multiple_vehicles_same_route():
    """Round-robin distributes positions when multiple vehicles share a route."""
    from mzkzg_transport.provider_gtfsrt import _apply_positions

    positions = {
        "v1": {"lat": 51.1, "lng": 17.0, "route_id": "A"},
        "v2": {"lat": 51.2, "lng": 17.1, "route_id": "A"},
    }
    deps = [
        {"route": "A", "vehicle_code": ""},
        {"route": "A", "vehicle_code": ""},
        {"route": "A", "vehicle_code": ""},
    ]
    _apply_positions(deps, positions)
    # One position per vehicle: the third trip must not reuse a bus marker.
    assert deps[0]["vehicle_lat"] == pytest.approx(51.1)
    assert deps[1]["vehicle_lat"] == pytest.approx(51.2)
    assert "vehicle_lat" not in deps[2]

@pytest.mark.gtfsrt
def test_parse_gtfsrt_positions_includes_route_id():
    """_parse_gtfsrt_positions stores route_id from trip.route_id."""
    from google.transit import gtfs_realtime_pb2
    from mzkzg_transport.gtfsrt_parser import _parse_gtfsrt_positions

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "v1"
    entity.vehicle.vehicle.id = "bus42"
    entity.vehicle.trip.route_id = "42A"
    entity.vehicle.position.latitude = 50.1
    entity.vehicle.position.longitude = 19.5

    positions = _parse_gtfsrt_positions(feed.SerializeToString())
    assert "bus42" in positions
    assert positions["bus42"]["route_id"] == "42A"
    assert positions["bus42"]["lat"] == pytest.approx(50.1)


@pytest.mark.gtfsrt
class TestSpeedNormalization:
    """vehicle_speed is always km/h regardless of source unit."""

    def test_gtfsrt_speed_ms_to_kmh(self):
        """_apply_positions converts protobuf m/s → km/h."""
        from mzkzg_transport.provider_gtfsrt import _apply_positions

        positions = {"v1": {"lat": 50.0, "lng": 19.0, "speed": 10.0}}  # 10 m/s
        deps = [{"vehicle_code": "v1"}]
        _apply_positions(deps, positions)
        assert deps[0]["vehicle_speed"] == 36  # 10*3.6 = 36 km/h

    def test_gtfsrt_speed_zero(self):
        """speed=0 is preserved as 0."""
        from mzkzg_transport.provider_gtfsrt import _apply_positions

        positions = {"v1": {"lat": 50.0, "lng": 19.0, "speed": 0.0}}
        deps = [{"vehicle_code": "v1"}]
        _apply_positions(deps, positions)
        assert deps[0]["vehicle_speed"] == 0


@pytest.mark.gtfsrt
class TestApplyPositionsRoundRobin:
    """One vehicle position per route departure."""

    def test_one_position_per_departure(self):
        from mzkzg_transport.provider_gtfsrt import _apply_positions

        positions = {
            "v1": {"lat": 50.1, "lng": 19.0, "route_id": "42"},
            "v2": {"lat": 50.2, "lng": 19.1, "route_id": "42"},
        }
        deps = [
            {"route": "42", "vehicle_code": "", "estimated_time": "2026-05-14T10:00:00"},
            {"route": "42", "vehicle_code": "", "estimated_time": "2026-05-14T10:20:00"},
            {"route": "42", "vehicle_code": "", "estimated_time": "2026-05-14T10:40:00"},
            {"route": "42", "vehicle_code": "", "estimated_time": "2026-05-14T11:00:00"},
        ]
        _apply_positions(deps, positions)
        # Two vehicles cover only the next two trips; later trips stay clean.
        assert deps[0]["vehicle_lat"] == pytest.approx(50.1)
        assert deps[1]["vehicle_lat"] == pytest.approx(50.2)
        assert "vehicle_lat" not in deps[2]
        assert "vehicle_lat" not in deps[3]

    def test_vehicle_code_has_priority_over_route_id(self):
        from mzkzg_transport.provider_gtfsrt import _apply_positions

        positions = {
            "busX": {"lat": 50.1, "lng": 19.0},
            "busY": {"lat": 50.2, "lng": 19.1, "route_id": "42"},
        }
        deps = [
            {"route": "42", "vehicle_code": "busX"},
            {"route": "42", "vehicle_code": ""},
        ]
        _apply_positions(deps, positions)
        assert deps[0]["vehicle_lat"] == pytest.approx(50.1)  # direct match wins
        assert deps[1]["vehicle_lat"] == pytest.approx(50.2)  # fallback


@pytest.mark.gtfsrt
class TestParseGtfsrtPositionsRouteId:
    """Tests for route_id extraction in _parse_gtfsrt_positions."""

    def test_route_id_extracted_when_trip_present(self):
        from google.transit import gtfs_realtime_pb2
        from mzkzg_transport.gtfsrt_parser import _parse_gtfsrt_positions

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        e = feed.entity.add()
        e.id = "v1"
        e.vehicle.vehicle.id = "bus1"
        e.vehicle.trip.route_id = "123A"
        e.vehicle.position.latitude = 50.1
        e.vehicle.position.longitude = 19.5

        positions = _parse_gtfsrt_positions(feed.SerializeToString())
        assert positions["bus1"]["route_id"] == "123A"

    def test_route_id_absent_when_no_trip(self):
        from google.transit import gtfs_realtime_pb2
        from mzkzg_transport.gtfsrt_parser import _parse_gtfsrt_positions

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        e = feed.entity.add()
        e.id = "v2"
        e.vehicle.vehicle.id = "bus2"
        e.vehicle.position.latitude = 50.1
        e.vehicle.position.longitude = 19.5

        positions = _parse_gtfsrt_positions(feed.SerializeToString())
        assert "route_id" not in positions["bus2"]

    def test_vehicle_id_strips_operator_prefix(self):
        from google.transit import gtfs_realtime_pb2
        from mzkzg_transport.gtfsrt_parser import _parse_gtfsrt_positions

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "2.0"
        e = feed.entity.add()
        e.id = "v3"
        e.vehicle.vehicle.id = "operator/GZM-42"
        e.vehicle.position.latitude = 50.1
        e.vehicle.position.longitude = 19.5

        positions = _parse_gtfsrt_positions(feed.SerializeToString())
        assert "GZM-42" in positions
