"""Persistent offline schedule snapshots shared by every provider."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SNAPSHOT_VERSION = 1
MAX_SNAPSHOT_DEPARTURES = 100
_SAFE_RE = re.compile(r"[^A-Za-z0-9_.+-]+")
_KEEP_FIELDS = (
    "route",
    "headsign",
    "vehicle_type",
    "route_color",
    "platform",
    "bike_allowed",
    "wheelchair_accessible",
    "air_conditioning",
    "ticket_machine",
    "usb",
)


def _slug(value: object) -> str:
    text = _SAFE_RE.sub("_", str(value or "")).strip("_")
    return text[:80] or "unknown"


def _snapshot_path(hass, provider: str, stop_id: object) -> Path:
    return Path(
        hass.config.path(".storage", DOMAIN, "offline")
    ) / f"{_slug(provider)}__{_slug(stop_id)}.json"


def _parse_time(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = dt_util.as_local(parsed).replace(tzinfo=None)
    return parsed


def _snapshot_rows(departures: list[dict]) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple] = set()
    for departure in departures or []:
        scheduled = departure.get("theoretical_time") or departure.get("estimated_time")
        if not scheduled:
            continue
        key = (
            departure.get("route"),
            departure.get("headsign"),
            str(scheduled)[:16],
        )
        if key in seen:
            continue
        seen.add(key)
        row = {"time": scheduled}
        for field in _KEEP_FIELDS:
            if departure.get(field) not in (None, ""):
                row[field] = departure[field]
        rows.append(row)
        if len(rows) >= MAX_SNAPSHOT_DEPARTURES:
            break
    return rows


async def async_save_snapshot(
    hass,
    provider: str,
    stop_id: object,
    stop_name: str | None,
    departures: list[dict],
    now: datetime | None = None,
) -> bool:
    """Persist the last successful schedule for one provider stop."""
    rows = _snapshot_rows(departures)
    if not rows:
        return False
    payload = {
        "version": SNAPSHOT_VERSION,
        "provider": provider,
        "stop_id": str(stop_id),
        "stop_name": stop_name or "",
        "saved_at": (now or dt_util.now()).isoformat(),
        "departures": rows,
    }
    path = _snapshot_path(hass, provider, stop_id)

    def _write() -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            temporary.replace(path)
            return True
        except OSError as err:
            _LOGGER.debug("Offline snapshot write failed for %s: %s", path, err)
            return False

    return await hass.async_add_executor_job(_write)


async def async_load_snapshot(hass, provider: str, stop_id: object) -> dict | None:
    """Read a previously persisted schedule snapshot."""
    path = _snapshot_path(hass, provider, stop_id)

    def _read() -> dict | None:
        try:
            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict) or payload.get("version") != SNAPSHOT_VERSION:
            return None
        if not payload.get("departures"):
            return None
        return payload

    return await hass.async_add_executor_job(_read)


async def async_has_snapshot(hass, provider: str, stop_id: object) -> bool:
    """Return True when an offline schedule exists for the stop."""
    return await async_load_snapshot(hass, provider, stop_id) is not None


def replay_snapshot(snapshot: dict, now: datetime | None = None) -> dict:
    """Turn a stored schedule into today's offline departures."""
    current = now or dt_util.now()
    departures: list[dict] = []

    for row in snapshot.get("departures") or []:
        source = _parse_time(row.get("time"))
        if source is None:
            continue
        target = current.replace(
            hour=source.hour,
            minute=source.minute,
            second=source.second,
            microsecond=0,
        )
        if target < current - timedelta(minutes=1):
            target += timedelta(days=1)
        departure = {field: row[field] for field in _KEEP_FIELDS if field in row}
        departure.update(
            {
                "estimated_time": target.isoformat(),
                "theoretical_time": target.isoformat(),
                "delay_seconds": 0,
                "realtime": False,
                "offline": True,
            }
        )
        departures.append(departure)

    departures.sort(key=lambda item: item.get("estimated_time") or "")
    return {
        "provider": snapshot.get("provider", ""),
        "stop_id": snapshot.get("stop_id", ""),
        "stop_name": snapshot.get("stop_name", ""),
        "departures": departures[:MAX_SNAPSHOT_DEPARTURES],
        "last_update": snapshot.get("saved_at", ""),
        "offline": True,
        "offline_saved_at": snapshot.get("saved_at", ""),
    }
