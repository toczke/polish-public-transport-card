"""Time4BUS Tczew provider."""

from datetime import datetime, timedelta
import logging
import re

from homeassistant.util import dt as dt_util

from .const import TIME4BUS_TCZEW_LIVE_DEPARTURES_URL, TIME4BUS_TCZEW_SCHEDULE_DEPARTURES_URL
from .http_utils import fetch_with_retry

_LOGGER = logging.getLogger(__name__)


async def fetch(coord) -> dict:
    """Fetch departures from Time4BUS for Tczew with live fallback."""
    session = await coord._get_session()
    now = dt_util.now()
    live_url = f"{TIME4BUS_TCZEW_LIVE_DEPARTURES_URL}/{coord.stop_id}/departures"
    schedule_url = f"{TIME4BUS_TCZEW_SCHEDULE_DEPARTURES_URL}/{coord.stop_id}/departures?date={now:%Y-%m-%d}"

    live_data = None
    schedule_data = None
    departures = []

    try:
        live_data = await fetch_with_retry(session, live_url)
        departures = _parse_live(live_data, now, coord.provider)
    except Exception as err:
        _LOGGER.debug("Time4BUS live fetch failed for %s: %s", coord.stop_id, err)
        departures = []

    if not departures:
        try:
            schedule_data = await fetch_with_retry(session, schedule_url)
            departures = _parse_schedule(schedule_data, now, coord.provider)
        except Exception as err:
            _LOGGER.debug("Time4BUS schedule fetch failed for %s: %s", coord.stop_id, err)
            if not departures:
                raise

    if not coord.stop_name:
        coord.stop_name = _extract_stop_name(live_data, schedule_data) or f"Przystanek {coord.stop_id}"

    departures.sort(key=lambda x: x.get("estimated_time") or "")
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": coord.provider,
        "departures": departures,
        "last_update": now.isoformat(),
    }


def _extract_stop_name(live_data, schedule_data) -> str | None:
    """Extract a human-readable stop name from Time4BUS payloads."""
    for payload in (live_data, schedule_data):
        if isinstance(payload, dict):
            for key in ("stopName", "name", "station_name"):
                value = payload.get(key)
                if value:
                    return str(value)
    return None


def _parse_clock_time(value, reference_dt: datetime) -> datetime | None:
    """Parse Time4BUS clock times into absolute datetimes."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    clock_match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", text)
    if not clock_match:
        return None
    hour = int(clock_match.group(1))
    minute = int(clock_match.group(2))
    second = int(clock_match.group(3) or 0)
    day_add = 0
    if hour >= 24:
        hour -= 24
        day_add = 1
    dep_dt = reference_dt.replace(hour=hour, minute=minute, second=second, microsecond=0) + timedelta(days=day_add)
    if (dep_dt - reference_dt).total_seconds() < -3600:
        dep_dt += timedelta(days=1)
    return dep_dt


def _parse_live(data, reference_dt: datetime, provider: str) -> list[dict]:
    """Normalize live Time4BUS departures."""
    departures = []
    if not isinstance(data, dict):
        return departures

    for row in data.get("departures", []) or []:
        if not isinstance(row, dict):
            continue
        leave_time = row.get("leaveTime")
        plan_time = row.get("planTime")
        if leave_time is None:
            continue
        try:
            estimated_dt = datetime.fromtimestamp(float(leave_time) / 1000, tz=dt_util.DEFAULT_TIME_ZONE)
        except (TypeError, ValueError, OSError):
            continue
        if plan_time is not None:
            try:
                theoretical_dt = datetime.fromtimestamp(float(plan_time) / 1000, tz=dt_util.DEFAULT_TIME_ZONE)
            except (TypeError, ValueError, OSError):
                theoretical_dt = estimated_dt
        else:
            theoretical_dt = estimated_dt

        if estimated_dt < reference_dt - timedelta(minutes=1):
            continue

        delay_seconds = int(round((estimated_dt - theoretical_dt).total_seconds()))
        vehicle_info = row.get("vehicleInfo") or {}
        if not isinstance(vehicle_info, dict):
            vehicle_info = {}
        departures.append({
            "route": str(row.get("line") or row.get("lineName") or "?"),
            "headsign": str(row.get("direction") or row.get("lastStop") or "?"),
            "estimated_time": estimated_dt.isoformat(),
            "theoretical_time": theoretical_dt.isoformat(),
            "delay_seconds": delay_seconds,
            "realtime": bool(row.get("isReal")) or delay_seconds != 0,
            "vehicle_type": "bus",
            "bike_allowed": None,
            "wheelchair_accessible": bool(vehicle_info.get("lowFloor")) if vehicle_info else None,
            "air_conditioning": vehicle_info.get("airConditioning") if vehicle_info else None,
            "ticket_machine": bool(vehicle_info.get("ticketMachine")) if vehicle_info else None,
            "vehicle_code": vehicle_info.get("name") if vehicle_info else None,
            "platform": row.get("platform"),
            "track": row.get("track"),
            "trip_id": row.get("tid"),
            "provider": provider,
        })

    return departures


def _parse_schedule(data, reference_dt: datetime, provider: str) -> list[dict]:
    """Normalize fallback Time4BUS schedule departures."""
    departures = []
    if not isinstance(data, dict):
        return departures

    for row in data.get("items", []) or []:
        if not isinstance(row, dict):
            continue
        time_text = row.get("departureTime") or row.get("arrivalTime")
        estimated_dt = _parse_clock_time(time_text, reference_dt)
        if estimated_dt is None:
            continue
        if estimated_dt < reference_dt - timedelta(minutes=1):
            continue

        departures.append({
            "route": str(row.get("lineName") or row.get("lineLongName") or row.get("lineId") or "?"),
            "headsign": str(row.get("directionName") or "?"),
            "estimated_time": estimated_dt.isoformat(),
            "theoretical_time": estimated_dt.isoformat(),
            "delay_seconds": 0,
            "realtime": False,
            "vehicle_type": "bus",
            "bike_allowed": None,
            "wheelchair_accessible": None,
            "air_conditioning": None,
            "platform": row.get("platform"),
            "track": row.get("track"),
            "trip_id": row.get("tripId"),
            "provider": provider,
        })

    return departures
