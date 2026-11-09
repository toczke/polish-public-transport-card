"""GTFS-Realtime service alerts shared by GTFS-RT providers."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time

from google.transit import gtfs_realtime_pb2

from .const import DOMAIN
from .http_utils import fetch_with_retry

_LOGGER = logging.getLogger(__name__)

ALERTS_TTL = 120


def derive_alerts_url(city_cfg: dict) -> str | None:
    """Return an explicit alert endpoint or derive one from an api6 feed."""
    explicit = city_cfg.get("alerts_url")
    if explicit:
        return explicit
    rt_url = str(city_cfg.get("rt_url") or "")
    if "/gtfsRealtime/" in rt_url and rt_url.endswith("/tripUpdates"):
        return rt_url[: -len("tripUpdates")] + "serviceAlerts"
    return None


def _translation(value) -> str:
    if value is None or not getattr(value, "translation", None):
        return ""
    for item in value.translation:
        if item.language in ("pl", ""):
            return str(item.text or "").strip()
    return str(value.translation[0].text or "").strip()


def _normalize(value: object) -> str:
    return str(value or "").strip().lower()


def parse_alerts(feed: gtfs_realtime_pb2.FeedMessage) -> list[dict]:
    """Parse a GTFS-RT FeedMessage into alert dictionaries."""
    now_ms = time.time() * 1000
    alerts: list[dict] = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        alert = entity.alert
        header = _translation(alert.header_text)
        description = _translation(alert.description_text)
        if not header and not description:
            continue
        if alert.active_period:
            active = False
            for period in alert.active_period:
                start = period.start or 0
                end = period.end or 0
                if start <= now_ms and (not end or now_ms <= end):
                    active = True
                    break
            if not active:
                continue

        lines: list[str] = []
        stops: list[str] = []
        for informed in alert.informed_entity:
            if informed.route_id and informed.route_id not in lines:
                lines.append(str(informed.route_id))
            if informed.stop_id and informed.stop_id not in stops:
                stops.append(str(informed.stop_id))
            if informed.trip.route_id and informed.trip.route_id not in lines:
                lines.append(str(informed.trip.route_id))

        alert_id = entity.id or hashlib.sha1(
            f"{header}|{description}".encode("utf-8")
        ).hexdigest()[:16]
        alerts.append(
            {
                "id": str(alert_id),
                "title": header or "Komunikat",
                "content": description,
                "lines": lines,
                "stops": stops,
                "url": _translation(alert.url),
                "published": "",
            }
        )
    return alerts


def _id_matches(configured: str, candidates: list[str]) -> bool:
    wanted = _normalize(configured)
    if not wanted:
        return False
    for candidate in candidates:
        value = _normalize(candidate)
        if not value:
            continue
        if value == wanted or value.endswith(f"_{wanted}") or wanted.endswith(f"_{value}"):
            return True
    return False


def alerts_for_stop(alerts: list[dict], stop_id: str, routes) -> list[dict]:
    """Filter GTFS-RT alerts by stop id, route id or general scope."""
    route_set = {_normalize(route) for route in routes or [] if str(route).strip()}
    result: list[dict] = []
    for alert in alerts:
        alert_lines = {_normalize(line) for line in alert.get("lines") or []}
        stop_match = _id_matches(stop_id, alert.get("stops") or [])
        line_match = any(_id_matches(route, list(alert_lines)) for route in route_set)
        general = not alert_lines and not alert.get("stops")
        if stop_match or line_match or general:
            result.append(alert)
    return result


async def async_get_alerts(coord, session, url: str) -> list[dict]:
    """Fetch and cache GTFS-RT service alerts for one provider."""
    domain_data = coord.hass.data.setdefault(DOMAIN, {})
    cache = domain_data.setdefault("_gtfsrt_alerts", {})
    locks = domain_data.setdefault("_gtfsrt_alert_locks", {})
    lock = locks.setdefault(url, asyncio.Lock())

    async with lock:
        entry = cache.get(url)
        if entry and time.monotonic() - entry.get("_ts", 0) < ALERTS_TTL:
            return entry["data"]
        try:
            raw = await fetch_with_retry(session, url, as_bytes=True)
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(raw)
            data = parse_alerts(feed)
            cache[url] = {"data": data, "_ts": time.monotonic()}
            return data
        except Exception as err:  # noqa: BLE001 - alerts must not break departures
            _LOGGER.debug("GTFS-RT alerts: fetch failed for %s: %s", url, err)
            return (entry or {}).get("data", [])
