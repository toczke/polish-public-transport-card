"""Tests for provider_gtfsrt.py."""

import zipfile
from io import BytesIO
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mzkzg_transport.provider_gtfsrt import (
    _parse_gtfs_zip,
    _parse_stop_times_for,
    _get_rt_delays,
    _parse_rt_feed,
    fetch,
)


def _make_gtfs_zip(
    calendar=None,
    calendar_dates=None,
    stops=None,
    routes=None,
    trips=None,
    stop_times=None,
):
    """Create a minimal in-memory GTFS zip."""
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
    return buf.getvalue()


def _today_str():
    return date.today().strftime("%Y%m%d")


def _day_name():
    return ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][date.today().weekday()]


def _calendar_line(service_id, active_today=True):
    """Build a calendar.txt row active today."""
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    today_day = _day_name()
    vals = ["1" if (d == today_day and active_today) or (d != today_day) else "0" for d in days]
    start = "20240101"
    end = "20271231"
    return f"{service_id},{','.join(vals)},{start},{end}"


CALENDAR_HEADER = "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date"


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


