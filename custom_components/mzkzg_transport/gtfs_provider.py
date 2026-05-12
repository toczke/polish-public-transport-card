"""GTFS static data provider for MZK Wejherowo."""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

import aiohttp

from .const import MZK_GTFS_URL

_LOGGER = logging.getLogger(__name__)

GTFS_CACHE_DIR = Path("/config/custom_components/mzkzg_transport/.gtfs_cache")


class GtfsData:
    """Parsed GTFS static data."""

    def __init__(self) -> None:
        self.stops: dict[str, dict] = {}
        self.routes: dict[str, dict] = {}
        self.trips: dict[str, dict] = {}
        self.stop_times: dict[str, list[dict]] = {}  # stop_id -> list of stop_times
        self.calendar_dates: dict[str, set[str]] = {}  # service_id -> set of date strings
        self._loaded = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    def parse_zip(self, data: bytes) -> None:
        """Parse GTFS zip file contents."""
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            self._parse_stops(zf)
            self._parse_routes(zf)
            self._parse_trips(zf)
            self._parse_calendar_dates(zf)
            self._parse_stop_times(zf)
        self._loaded = True

    def _read_csv(self, zf: zipfile.ZipFile, name: str) -> list[dict]:
        with zf.open(name) as f:
            return list(csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")))

    def _parse_stops(self, zf: zipfile.ZipFile) -> None:
        for row in self._read_csv(zf, "stops.txt"):
            self.stops[row["stop_id"]] = {
                "name": row.get("stop_name", ""),
                "code": row.get("stop_code", ""),
            }

    def _parse_routes(self, zf: zipfile.ZipFile) -> None:
        for row in self._read_csv(zf, "routes.txt"):
            self.routes[row["route_id"]] = {
                "short_name": row.get("route_short_name", ""),
                "long_name": row.get("route_long_name", ""),
                "color": row.get("route_color", ""),
            }

    def _parse_trips(self, zf: zipfile.ZipFile) -> None:
        for row in self._read_csv(zf, "trips.txt"):
            self.trips[row["trip_id"]] = {
                "route_id": row["route_id"],
                "service_id": row["service_id"],
                "headsign": row.get("trip_headsign", ""),
            }

    def _parse_calendar_dates(self, zf: zipfile.ZipFile) -> None:
        for row in self._read_csv(zf, "calendar_dates.txt"):
            sid = row["service_id"]
            if row.get("exception_type") == "1":
                self.calendar_dates.setdefault(sid, set()).add(row["date"])

    def _parse_stop_times(self, zf: zipfile.ZipFile) -> None:
        for row in self._read_csv(zf, "stop_times.txt"):
            stop_id = row["stop_id"]
            self.stop_times.setdefault(stop_id, []).append({
                "trip_id": row["trip_id"],
                "departure_time": row.get("departure_time", row.get("arrival_time", "")),
                "stop_sequence": int(row.get("stop_sequence", 0)),
            })

    def get_departures(self, stop_id: str, now: datetime | None = None) -> list[dict]:
        """Get upcoming departures for a stop based on static schedule."""
        if not self._loaded:
            return []

        now = now or datetime.now()
        today_str = now.strftime("%Y%m%d")
        current_time = now.strftime("%H:%M:%S")

        # Active service IDs for today
        active_services = {
            sid for sid, dates in self.calendar_dates.items() if today_str in dates
        }

        stop_entries = self.stop_times.get(stop_id, [])
        departures = []

        for st in stop_entries:
            trip = self.trips.get(st["trip_id"])
            if not trip:
                continue
            if trip["service_id"] not in active_services:
                continue

            dep_time = st["departure_time"]
            # Handle times > 24:00:00 (next day service)
            h, m, s = map(int, dep_time.split(":"))
            if h >= 24:
                continue  # Skip next-day overflow for simplicity

            if dep_time < current_time:
                continue

            route = self.routes.get(trip["route_id"], {})
            dep_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)

            departures.append({
                "route": route.get("short_name", trip["route_id"]),
                "headsign": trip["headsign"],
                "estimated_time": dep_dt.isoformat(),
                "theoretical_time": dep_dt.isoformat(),
                "delay_seconds": 0,
                "realtime": False,
                "vehicle_type": "bus",
                "bike_allowed": None,
                "wheelchair_accessible": None,
                "air_conditioning": None,
                "provider": "mzk_wejherowo",
            })

        departures.sort(key=lambda x: x["estimated_time"])
        return departures


# Global singleton
_gtfs_data: GtfsData | None = None
_gtfs_last_update: datetime | None = None


async def get_gtfs_data(force_refresh: bool = False) -> GtfsData:
    """Get or refresh GTFS data (refreshes once per day, cached to disk)."""
    global _gtfs_data, _gtfs_last_update

    if (
        _gtfs_data
        and _gtfs_data.loaded
        and _gtfs_last_update
        and (datetime.now() - _gtfs_last_update) < timedelta(hours=24)
        and not force_refresh
    ):
        return _gtfs_data

    # Try disk cache first
    cache_file = GTFS_CACHE_DIR / "wejherowo.zip"
    data = None
    if not force_refresh and cache_file.exists():
        file_age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if file_age < 86400:  # 24h
            data = cache_file.read_bytes()
            _LOGGER.debug("Using cached GTFS from disk")

    if data is None:
        _LOGGER.info("Downloading MZK Wejherowo GTFS data...")
        async with aiohttp.ClientSession() as session:
            async with session.get(MZK_GTFS_URL, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                data = await resp.read()
        # Save to disk
        try:
            GTFS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(data)
        except OSError:
            _LOGGER.debug("Could not write GTFS cache to disk")

    gtfs = GtfsData()
    gtfs.parse_zip(data)
    _gtfs_data = gtfs
    _gtfs_last_update = datetime.now()
    _LOGGER.info("MZK Wejherowo GTFS loaded: %d stops, %d routes", len(gtfs.stops), len(gtfs.routes))
    return gtfs
