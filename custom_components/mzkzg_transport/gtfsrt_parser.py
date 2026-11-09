import csv
import codecs
from array import array
import re
import unicodedata
import zipfile
import logging
from io import BytesIO, TextIOWrapper
from datetime import date as dt_date, timedelta

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


def _normalize_stop_text(value: object) -> str:
    """Case- and accent-insensitive stop text."""
    text = str(value or "").replace("ł", "l").replace("Ł", "L")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _stop_base_name(name: str) -> str:
    """Strip a trailing platform number and the on-demand marker (NŻ)."""
    text = _normalize_stop_text(name)
    text = re.sub(r"\s+nz$", "", text)
    return re.sub(r"\s+\d{1,2}$", "", text)


def _platform_suffix(name: str) -> str | None:
    match = re.search(r"(?:^|\s)(\d{1,2})$", _normalize_stop_text(name))
    if not match:
        return None
    return match.group(1).lstrip("0") or "0"


def resolve_stop_id(stops: dict, old_id: str, old_name: str) -> str | None:
    """Resolve a stale stop ID after an operator changes GTFS stop identifiers.

    Providers occasionally replace numeric IDs with slugs (Lublin did this on
    2026-11-04). Match by the base stop name first, then use the platform suffix
    from the old name or the last digit of the old numeric ID to disambiguate
    platforms such as "Majdanek - pomnik 01" and "... 02".
    """
    old_id = str(old_id or "")
    if old_id in stops:
        return old_id

    base = _stop_base_name(old_name)
    if not base:
        return None

    candidates = [
        (str(stop_id), info)
        for stop_id, info in stops.items()
        if _stop_base_name(info.get("name", "")) == base
    ]
    if len(candidates) == 1:
        return candidates[0][0]
    if not candidates:
        return None

    # Some zbiorkom feeds keep the old numeric stop code inside the new slug
    # (for example "urzad-miasta1141-mhwf5"). That is the strongest signal.
    if old_id.isdigit():
        embedded = [
            stop_id
            for stop_id, _info in candidates
            if re.search(rf"(?<!\d){re.escape(old_id)}(?!\d)", stop_id)
        ]
        if len(embedded) == 1:
            return embedded[0]

    wanted = _platform_suffix(old_name)
    if not wanted:
        match = re.search(r"(\d)$", old_id)
        wanted = match.group(1) if match else None
    if wanted:
        for stop_id, info in candidates:
            if _platform_suffix(info.get("name", "")) == wanted:
                return stop_id
    return None


def _read_csv(zf, filename):
    """Open a GTFS CSV file and stream its rows from the zip."""
    if filename not in zf.namelist():
        return None, iter(())

    raw = zf.open(filename)
    text = TextIOWrapper(raw, encoding="utf-8-sig", newline="")
    reader = csv.reader(text)
    try:
        header = next(reader)
    except (StopIteration, UnicodeDecodeError):
        text.close()
        return None, iter(())

    def rows():
        try:
            yield from reader
        finally:
            text.close()

    return header, rows()


def _parse_gtfs_zip(data: bytes) -> dict:
    """Parse relevant GTFS files from zip."""
    from datetime import date as dt_date

    stops = {}
    routes = {}
    trips = {}
    stop_times = {}  # stop_id -> list of {trip_id, route_id, departure_time, headsign}
    raw_zip = data
    today = dt_util.now().date()
    today_str = today.strftime("%Y%m%d")
    day_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][today.weekday()]

    with zipfile.ZipFile(BytesIO(data)) as zf:
        # calendar.txt — active services
        active_services = set()
        has_calendar = False
        any_weekday_match = False
        header, rows = _read_csv(zf, "calendar.txt")
        if header:
            has_calendar = True
            sid_idx = header.index("service_id")
            day_idx = header.index(day_name) if day_name in header else -1
            start_idx = header.index("start_date") if "start_date" in header else -1
            end_idx = header.index("end_date") if "end_date" in header else -1
            for parts in rows:
                if len(parts) <= sid_idx:
                    continue
                svc = parts[sid_idx]
                active = day_idx >= 0 and len(parts) > day_idx and parts[day_idx] == "1"
                if active:
                    any_weekday_match = True
                if active and start_idx >= 0 and end_idx >= 0 and len(parts) > max(start_idx, end_idx):
                    if parts[start_idx] > today_str or parts[end_idx] < today_str:
                        active = False
                if active:
                    active_services.add(svc)

        # calendar_dates.txt — exceptions
        header, rows = _read_csv(zf, "calendar_dates.txt")
        if header:
            has_calendar = True
            sid_idx = header.index("service_id")
            date_idx = header.index("date")
            etype_idx = header.index("exception_type")
            for parts in rows:
                if len(parts) <= max(sid_idx, date_idx, etype_idx):
                    continue
                if parts[date_idx] != today_str:
                    continue
                svc = parts[sid_idx]
                if parts[etype_idx] == "1":
                    active_services.add(svc)
                elif parts[etype_idx] == "2":
                    active_services.discard(svc)

        # stops.txt
        header, rows = _read_csv(zf, "stops.txt")
        if header:
            id_idx = header.index("stop_id")
            name_idx = header.index("stop_name")
            lat_idx = header.index("stop_lat") if "stop_lat" in header else -1
            lon_idx = header.index("stop_lon") if "stop_lon" in header else -1
            for parts in rows:
                if len(parts) > max(id_idx, name_idx):
                    stop_entry = {"name": parts[name_idx]}
                    if lat_idx >= 0 and lon_idx >= 0 and len(parts) > max(lat_idx, lon_idx):
                        try:
                            stop_entry["lat"] = float(parts[lat_idx])
                            stop_entry["lon"] = float(parts[lon_idx])
                        except (ValueError, IndexError):
                            pass
                    stops[parts[id_idx]] = stop_entry

        # routes.txt
        header, rows = _read_csv(zf, "routes.txt")
        if header:
            id_idx = header.index("route_id")
            sn_idx = header.index("route_short_name") if "route_short_name" in header else -1
            rt_idx = header.index("route_type") if "route_type" in header else -1
            rc_idx = header.index("route_color") if "route_color" in header else -1
            for parts in rows:
                if len(parts) > id_idx:
                    rid = parts[id_idx]
                    short = parts[sn_idx] if sn_idx >= 0 and len(parts) > sn_idx else rid
                    rtype = "tram" if rt_idx >= 0 and len(parts) > rt_idx and parts[rt_idx] == "0" else "bus"
                    route_dict = {"short_name": short, "type": rtype}
                    if rc_idx >= 0 and len(parts) > rc_idx and parts[rc_idx]:
                        route_dict["color"] = f"#{parts[rc_idx]}"
                    routes[rid] = route_dict

        # trips.txt
        header, rows = _read_csv(zf, "trips.txt")
        if header:
            tid_idx = header.index("trip_id")
            rid_idx = header.index("route_id")
            hs_idx = header.index("trip_headsign") if "trip_headsign" in header else -1
            svc_idx = header.index("service_id") if "service_id" in header else -1
            wc_idx = header.index("wheelchair_accessible") if "wheelchair_accessible" in header else -1
            bike_idx = header.index("bikes_allowed") if "bikes_allowed" in header else -1
            # calendar_dates-only feeds have no weekday column; the exception
            # rows still tell us which services run today (#32/#33).
            filter_by_service = has_calendar and (any_weekday_match or bool(active_services))
            for parts in rows:
                if len(parts) > max(tid_idx, rid_idx):
                    tid = parts[tid_idx]
                    if filter_by_service and svc_idx >= 0 and len(parts) > svc_idx:
                        if parts[svc_idx] not in active_services:
                            continue
                    rid = parts[rid_idx]
                    hs = parts[hs_idx] if hs_idx >= 0 and len(parts) > hs_idx else ""
                    trip = {"route_id": rid, "headsign": hs}
                    if wc_idx >= 0 and len(parts) > wc_idx and parts[wc_idx] == "1":
                        trip["wheelchair"] = True
                    if bike_idx >= 0 and len(parts) > bike_idx and parts[bike_idx] == "1":
                        trip["bike"] = True
                    trips[tid] = trip

        # Store raw zip for on-demand stop_times parsing
        raw_zip = data

    return {"stops": stops, "routes": routes, "trips": trips, "stop_times": stop_times, "_raw": raw_zip}


def _gtfs_seconds(value: str) -> int | None:
    """Return a GTFS time ("25:10:00" is allowed) in seconds from the service day start."""
    try:
        h, m, s = (int(x) for x in value.split(":"))
    except ValueError:
        return None
    return h * 3600 + m * 60 + s


def _trip_times(seqs, times):
    """A trip's stops as one compact array of pairs: stop_sequence, seconds, stop_sequence, ...

    Stops without a time are left out. One array per scheduled row keeps the cost low.
    """
    values = []
    for seq, text in zip(seqs, times):
        secs = _gtfs_seconds(text)
        if secs is not None:
            values += (seq, secs)
    return array("i", values)


def _parse_stop_times_for(gtfs, stop_id):
    """Parse stop_times from cached raw zip for a specific stop."""
    raw = gtfs.get("_raw")
    if not raw:
        return
    trips = gtfs["trips"]
    stops = gtfs["stops"]
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        header, reader = _read_csv(zf, "stop_times.txt")
        if not header:
            return
        tid_idx = header.index("trip_id")
        sid_idx = header.index("stop_id")
        dep_idx = header.index("departure_time")
        hs_idx = header.index("stop_headsign") if "stop_headsign" in header else -1
        seq_idx = header.index("stop_sequence") if "stop_sequence" in header else -1

        # First pass: collect our stop's entries + track last stop per trip (for headsign)
        our_entries = []
        last_seq_per_trip = {}  # trip_id -> (max_seq, stop_id)
        need_headsign = set()
        # The current trip's stops so far. A realtime feed may send only an absolute time
        # at the stop the vehicle is at; the delay is that time minus the schedule there.
        # Rows of a trip are expected together, in order. Times are parsed only when kept.
        run_trip, run_seqs, run_times = None, [], []

        for parts in reader:
            if len(parts) <= max(tid_idx, sid_idx, dep_idx):
                continue
            tid = parts[tid_idx]
            if tid not in trips:
                continue
            sid = parts[sid_idx]
            seq = int(parts[seq_idx]) if seq_idx >= 0 and len(parts) > seq_idx and parts[seq_idx].isdigit() else 0
            if tid != run_trip:
                run_trip, run_seqs, run_times = tid, [], []
            run_seqs.append(seq)
            run_times.append(parts[dep_idx])

            if sid == stop_id:
                dep_str = parts[dep_idx]
                try:
                    h, m, s = [int(x) for x in dep_str.split(":")]
                except (ValueError, IndexError):
                    continue
                hs = ""
                if hs_idx >= 0 and len(parts) > hs_idx:
                    hs = parts[hs_idx]
                hs = hs or trips[tid].get("headsign", "")
                our_entries.append({"trip_id": tid, "route_id": trips[tid].get("route_id", ""), "departure_time": (h, m, s), "headsign": hs, "stop_sequence": str(seq), "trip_times": _trip_times(run_seqs, run_times)})
                if not hs:
                    need_headsign.add(tid)

            # Track last stop for trips needing headsign
            if tid in need_headsign or (sid == stop_id and not trips[tid].get("headsign")):
                prev = last_seq_per_trip.get(tid, (-1, ""))
                if seq > prev[0]:
                    last_seq_per_trip[tid] = (seq, sid)

        # Fill in headsigns from last stop name
        if need_headsign and last_seq_per_trip:
            for entry in our_entries:
                if not entry["headsign"] and entry["trip_id"] in last_seq_per_trip:
                    last_sid = last_seq_per_trip[entry["trip_id"]][1]
                    entry["headsign"] = stops.get(last_sid, {}).get("name", "")

        gtfs["stop_times"][stop_id] = our_entries

    # Also parse from secondary (tram) zip if present
    if gtfs.get("_raw_tram"):
        _parse_stop_times_from_raw(gtfs, stop_id, gtfs["_raw_tram"])


def _parse_stop_times_from_raw(gtfs, stop_id, raw_data):
    """Parse stop_times from a raw GTFS zip and append to gtfs['stop_times'][stop_id]."""
    trips = gtfs["trips"]
    stops = gtfs["stops"]
    with zipfile.ZipFile(BytesIO(raw_data)) as zf:
        header, reader = _read_csv(zf, "stop_times.txt")
        if not header:
            return
        tid_idx = header.index("trip_id")
        sid_idx = header.index("stop_id")
        dep_idx = header.index("departure_time")
        hs_idx = header.index("stop_headsign") if "stop_headsign" in header else -1
        seq_idx = header.index("stop_sequence") if "stop_sequence" in header else -1

        our_entries = []
        last_seq_per_trip = {}
        need_headsign = set()
        # The current trip's stops so far. A realtime feed may send only an absolute time
        # at the stop the vehicle is at; the delay is that time minus the schedule there.
        # Rows of a trip are expected together, in order. Times are parsed only when kept.
        run_trip, run_seqs, run_times = None, [], []

        for parts in reader:
            if len(parts) <= max(tid_idx, sid_idx, dep_idx):
                continue
            tid = parts[tid_idx]
            if tid not in trips:
                continue
            sid = parts[sid_idx]
            seq = int(parts[seq_idx]) if seq_idx >= 0 and len(parts) > seq_idx and parts[seq_idx].isdigit() else 0
            if tid != run_trip:
                run_trip, run_seqs, run_times = tid, [], []
            run_seqs.append(seq)
            run_times.append(parts[dep_idx])

            if sid == stop_id:
                dep_str = parts[dep_idx]
                try:
                    h, m, s = [int(x) for x in dep_str.split(":")]
                except (ValueError, IndexError):
                    continue
                hs = ""
                if hs_idx >= 0 and len(parts) > hs_idx:
                    hs = parts[hs_idx]
                hs = hs or trips[tid].get("headsign", "")
                our_entries.append({"trip_id": tid, "route_id": trips[tid].get("route_id", ""), "departure_time": (h, m, s), "headsign": hs, "stop_sequence": str(seq), "trip_times": _trip_times(run_seqs, run_times)})
                if not hs:
                    need_headsign.add(tid)

            if tid in need_headsign or (sid == stop_id and not trips[tid].get("headsign")):
                prev = last_seq_per_trip.get(tid, (-1, ""))
                if seq > prev[0]:
                    last_seq_per_trip[tid] = (seq, sid)

        if need_headsign and last_seq_per_trip:
            for entry in our_entries:
                if not entry["headsign"] and entry["trip_id"] in last_seq_per_trip:
                    last_sid = last_seq_per_trip[entry["trip_id"]][1]
                    entry["headsign"] = stops.get(last_sid, {}).get("name", "")

        gtfs["stop_times"].setdefault(stop_id, []).extend(our_entries)


def _parse_gtfsrt_positions(raw):
    """Parse a GTFS-RT VehiclePositions payload into positions keyed by vehicle ID."""
    from google.transit import gtfs_realtime_pb2

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(raw)
    positions = {}
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        vehicle = entity.vehicle
        vehicle_id = vehicle.vehicle.id or vehicle.vehicle.label or ""
        vehicle_id = vehicle_id.split("/")[-1] if "/" in vehicle_id else vehicle_id
        if not vehicle_id or not vehicle.HasField("position"):
            continue
        entry = {
            "lat": vehicle.position.latitude,
            "lng": vehicle.position.longitude,
        }
        try:
            entry["bearing"] = vehicle.position.bearing if vehicle.position.HasField("bearing") else None
        except (ValueError, AttributeError):
            pass
        try:
            entry["speed"] = vehicle.position.speed if vehicle.position.HasField("speed") else None
        except (ValueError, AttributeError):
            pass
        if vehicle.HasField("trip") and vehicle.trip.route_id:
            entry["route_id"] = vehicle.trip.route_id
        positions[vehicle_id] = entry
    return positions


def _scheduled_seconds(stu, entry, stop_id):
    """Scheduled seconds from the service day start at the update's stop, or None.

    ``entry`` is this stop's stop_times entry for the update's trip.
    """
    if stu.HasField("stop_sequence"):
        times = entry.get("trip_times", ())
        seqs = times[0::2]
        if stu.stop_sequence in seqs:
            return times[2 * seqs.index(stu.stop_sequence) + 1]
        return None
    if stu.stop_id and stu.stop_id == stop_id:
        h, m, s = entry["departure_time"]
        return h * 3600 + m * 60 + s
    return None


def _stop_time_delay(stu, entry, stop_id, day_start):
    """Return the delay of a StopTimeUpdate in seconds, or None when it is unknown."""
    events = []
    if stu.HasField("departure"):
        events.append(stu.departure)
    if stu.HasField("arrival"):
        events.append(stu.arrival)
    for event in events:
        if event.HasField("delay") or event.HasField("time"):
            break
    else:
        return 0
    if event.HasField("delay"):
        return event.delay
    if entry is None or day_start is None or not event.HasField("time"):
        return None
    scheduled = _scheduled_seconds(stu, entry, stop_id)
    if scheduled is None:
        return None
    return int(event.time - (day_start + timedelta(seconds=scheduled)).timestamp())


def _parse_rt_feed(feed, trip_entries=None, stop_id=None, day_start=None) -> dict:
    """Parse a GTFS-RT FeedMessage into {key: (delay, vehicle_label)}.

    Only trip-specific keys are emitted. A route-level fallback would copy one
    trip's delay and vehicle to every other trip on the same route, which is
    especially visible in Poznań where many later trips share one bus.

    Some feeds (api6-open on zbiorkom.live, mkuran.pl) send only an absolute
    ``time``, no ``delay``. It is compared with the schedule of this stop's
    stop_times entries (``trip_entries``: trip_id -> entry, times counted from
    ``day_start``): at the update's stop_sequence, or at this stop when the update
    has only ``stop_id``. An update without a delay that cannot be compared, or
    that is for another day's run, is skipped instead of shown as on time.
    """
    trip_entries = trip_entries or {}
    today = f"{day_start:%Y%m%d}" if day_start else ""
    delays = {}
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        trip = entity.trip_update.trip
        trip_id = trip.trip_id
        # Trip ids repeat every day, and a vehicle's next trips can be tomorrow's runs.
        if trip.start_date and trip.start_date != today:
            continue
        entry = trip_entries.get(trip_id)
        vehicle_label = ""
        if entity.trip_update.HasField("vehicle"):
            v = entity.trip_update.vehicle
            vid = v.id or v.label or ""
            vehicle_label = vid.split("/")[-1] if "/" in vid else vid
        for stu in entity.trip_update.stop_time_update:
            delay = _stop_time_delay(stu, entry, stop_id, day_start)
            if delay is None:
                continue
            if stu.stop_id:
                delays[f"{trip_id}_{stu.stop_id}"] = (delay, vehicle_label)
            if stu.stop_sequence:
                delays[f"{trip_id}_seq{stu.stop_sequence}"] = (delay, vehicle_label)
            delays[trip_id] = (delay, vehicle_label)
    return delays


def _get_tomorrow_departures(gtfs, stop_id, tomorrow, now):
    """Get scheduled departures for tomorrow from raw GTFS zip."""
    return _get_tomorrow_departures_many(gtfs, [stop_id], tomorrow, now).get(
        str(stop_id), []
    )


def _get_tomorrow_departures_many(gtfs, stop_ids, tomorrow, now):
    """Get tomorrow's departures for several stops in a single zip pass."""
    date_key = tomorrow.strftime("%Y%m%d")
    wanted = [str(stop_id) for stop_id in stop_ids]
    result: dict[str, list] = {}
    missing: list[str] = []
    for stop_id in wanted:
        cache_key = f"tomorrow_{stop_id}_{date_key}"
        cached = gtfs.get(cache_key)
        if cached is None:
            missing.append(stop_id)
        else:
            result[stop_id] = cached
    if not missing:
        return result

    raw = gtfs.get("_raw")
    if not raw:
        for stop_id in missing:
            result[stop_id] = []
        return result

    tomorrow_str = date_key
    day_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][tomorrow.weekday()]

    # Parse calendar for tomorrow's active services
    active_services = set()
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        header, rows = _read_csv(zf, "calendar.txt")
        if header:
            sid_idx = header.index("service_id")
            day_idx = header.index(day_name) if day_name in header else -1
            start_idx = header.index("start_date") if "start_date" in header else -1
            end_idx = header.index("end_date") if "end_date" in header else -1
            for parts in rows:
                if len(parts) <= sid_idx:
                    continue
                active = day_idx >= 0 and len(parts) > day_idx and parts[day_idx] == "1"
                if active and start_idx >= 0 and end_idx >= 0 and len(parts) > max(start_idx, end_idx):
                    if parts[start_idx] > tomorrow_str or parts[end_idx] < tomorrow_str:
                        active = False
                if active:
                    active_services.add(parts[sid_idx])

        header, rows = _read_csv(zf, "calendar_dates.txt")
        if header:
            sid_idx = header.index("service_id")
            date_idx = header.index("date")
            etype_idx = header.index("exception_type")
            for parts in rows:
                if len(parts) <= max(sid_idx, date_idx, etype_idx):
                    continue
                if parts[date_idx] != tomorrow_str:
                    continue
                if parts[etype_idx] == "1":
                    active_services.add(parts[sid_idx])
                elif parts[etype_idx] == "2":
                    active_services.discard(parts[sid_idx])

    if not active_services:
        for stop_id in missing:
            gtfs[f"tomorrow_{stop_id}_{date_key}"] = []
            result[stop_id] = []
        return result

    tomorrow_trips = {}
    stop_times: dict[str, list] = {stop_id: [] for stop_id in missing}
    missing_set = set(missing)
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        header, rows = _read_csv(zf, "trips.txt")
        if header:
            tid_idx = header.index("trip_id")
            rid_idx = header.index("route_id")
            svc_idx = header.index("service_id")
            hs_idx = header.index("trip_headsign") if "trip_headsign" in header else -1
            for parts in rows:
                if len(parts) <= max(tid_idx, rid_idx, svc_idx):
                    continue
                if parts[svc_idx] not in active_services:
                    continue
                tomorrow_trips[parts[tid_idx]] = {
                    "route_id": parts[rid_idx],
                    "headsign": parts[hs_idx] if hs_idx >= 0 and len(parts) > hs_idx else "",
                }

        header, rows = _read_csv(zf, "stop_times.txt")
        if header:
            tid_idx = header.index("trip_id")
            sid_idx = header.index("stop_id")
            time_column = "departure_time" if "departure_time" in header else "arrival_time"
            time_idx = header.index(time_column)
            hs_idx = header.index("stop_headsign") if "stop_headsign" in header else -1
            for parts in rows:
                if len(parts) <= max(tid_idx, sid_idx, time_idx) or parts[sid_idx] not in missing_set:
                    continue
                trip_id = parts[tid_idx]
                trip = tomorrow_trips.get(trip_id)
                if not trip:
                    continue
                try:
                    h, m, s = map(int, parts[time_idx].split(":"))
                except (TypeError, ValueError):
                    continue
                stop_times[parts[sid_idx]].append({
                    "trip_id": trip_id,
                    "route_id": trip["route_id"],
                    "departure_time": (h, m, s),
                    "headsign": parts[hs_idx] if hs_idx >= 0 and len(parts) > hs_idx else "",
                })

    for stop_id, rows in stop_times.items():
        departures = []
        for st in rows:
            trip_id = st["trip_id"]
            trip = tomorrow_trips[trip_id]

            route_id = st["route_id"]
            route_name = gtfs["routes"].get(route_id, {}).get("short_name", route_id)
            headsign = st.get("headsign") or trip.get("headsign", "")

            h, m, s = st["departure_time"]
            dep_dt = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h, minutes=m, seconds=s)

            if dep_dt < now:
                continue

            departures.append({
                "route": route_name,
                "headsign": headsign,
                "estimated_time": dep_dt.isoformat(),
                "theoretical_time": dep_dt.isoformat(),
                "delay_seconds": 0,
                "realtime": False,
                "vehicle_type": gtfs["routes"].get(route_id, {}).get("type", "bus"),
                "route_color": gtfs["routes"].get(route_id, {}).get("color"),
                "provider": "schedule",
            })

        departures.sort(key=lambda x: x.get("estimated_time") or "")
        result[stop_id] = departures[:15]
        gtfs[f"tomorrow_{stop_id}_{date_key}"] = result[stop_id]

    return result


def _release_gtfs_raw(gtfs, stop_ids, now):
    """Drop the raw GTFS archive once every configured stop has been parsed.

    The zip is kept only to lazily extract stop_times for stops that have not
    been requested yet. Once the whole hub has been parsed it costs tens of MB
    per provider, so precompute tomorrow's small fallback lists and release it.
    """
    if not gtfs.get("_raw"):
        return
    if any(str(stop_id) not in gtfs["stop_times"] for stop_id in stop_ids):
        return
    tomorrow = now + timedelta(days=1)
    tomorrow_prefix = f"{tomorrow:%Y%m%d}_"
    rows_by_stop = _get_tomorrow_departures_many(gtfs, stop_ids, tomorrow, now)
    tomorrow_cache = gtfs.setdefault("_tomorrow_departures", {})
    for stop_id, rows in rows_by_stop.items():
        tomorrow_cache[f"{tomorrow_prefix}{stop_id}"] = rows
    gtfs.pop("_raw", None)
    gtfs.pop("_raw_tram", None)


# Bytes pulled from the end of a remote zip — enough for the central directory
# of a GTFS feed (~20 members), which is what zipfile needs to locate a member.
_ZIP_TAIL_BYTES = 65536

