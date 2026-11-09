"""ZTM Gdańsk current-situation alerts (``bsk_rss.xml``).

The RSS feed publishes a JSON object in ``<description>`` with the affected
lines and a human readable message. Alerts are filtered per stop by line and/or
by stop name so the card only shows messages relevant to its sensors.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import unicodedata
import xml.etree.ElementTree as ET

from .const import DOMAIN
from .http_utils import fetch_with_retry

_LOGGER = logging.getLogger(__name__)

ZTM_ALERTS_RSS_URL = "https://www.gdansk.pl/subpages/rss/bsk_rss.xml"
ZTM_ALERTS_TTL = 120

_TAG_RE = re.compile(r"<[^>]+>")
_LINE_RE = re.compile(
    r"(?:linia|linie|linii)\s+"
    r"([0-9A-Za-z]+(?:\s*(?:,|\bi\b)\s*[0-9A-Za-z]+)*)",
    re.IGNORECASE,
)
_ROUTE_TOKEN_RE = re.compile(r"\b(?:N|T|M)?\d{1,3}[A-Z]?\b", re.IGNORECASE)


def _normalize(value: object) -> str:
    text = str(value or "").replace("ł", "l").replace("Ł", "L")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", value or "")).strip()


def _clean_lines(values) -> list[str]:
    lines: list[str] = []
    for value in values:
        token = str(value or "").strip().upper()
        if token and token not in lines:
            lines.append(token)
    return lines


def _extract_lines(title: str, content: str) -> list[str]:
    text = f"{title} {content}"
    found: list[str] = []
    for match in _LINE_RE.finditer(text):
        for token in re.split(r"\s*(?:,|\bi\b)\s*", match.group(1), flags=re.IGNORECASE):
            token = token.strip().upper()
            if token and token not in found:
                found.append(token)
    if found:
        return found
    # Some planned messages only mention the route in the title, e.g.
    # "Linia 195: ...". Keep only route-like tokens from the title to avoid
    # extracting stop/platform numbers from the body.
    if re.search(r"\b(?:linia|linie|linii)\b", title, re.IGNORECASE):
        for token in _ROUTE_TOKEN_RE.findall(title):
            token = token.upper()
            if token not in found:
                found.append(token)
    return found


def parse_alerts(xml_text: str) -> list[dict]:
    """Parse the ZTM Gdańsk RSS feed into alert dictionaries."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as err:
        _LOGGER.debug("ZTM alerts: RSS parse failed: %s", err)
        return []

    alerts: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        raw_description = (item.findtext("description") or "").strip()
        published = (item.findtext("pubDate") or "").strip()

        content = raw_description
        lines: list[str] = []
        try:
            payload = json.loads(raw_description)
        except (TypeError, ValueError):
            pass
        else:
            if isinstance(payload, dict):
                content = str(payload.get("content") or "")
                lines = _clean_lines(payload.get("lineNumbers") or [])

        content = _strip_html(content)
        lines = lines or _extract_lines(title, content)
        if not title and not content:
            continue
        alerts.append(
            {
                "id": link or _normalize(f"{title} {content}")[:80],
                "title": title,
                "content": content,
                "lines": lines,
                "url": link,
                "published": published,
            }
        )
    return alerts


def _stop_variants(stop_name: str) -> set[str]:
    normalized = _normalize(stop_name)
    if not normalized:
        return set()
    variants = {normalized}
    base = re.sub(r"\s+\d{1,2}[a-z]?$", "", normalized)
    if base:
        variants.add(base)
    return variants


def alerts_for_stop(alerts: list[dict], stop_name: str, routes) -> list[dict]:
    """Return alerts matching a stop by affected line or stop name."""
    route_set = {_normalize(route) for route in routes or [] if str(route).strip()}
    variants = _stop_variants(stop_name)
    result: list[dict] = []
    for alert in alerts:
        alert_lines = {_normalize(line) for line in alert.get("lines") or []}
        text = _normalize(f"{alert.get('title', '')} {alert.get('content', '')}")
        line_match = bool(alert_lines & route_set)
        stop_match = any(variant in text for variant in variants if variant)
        if line_match or stop_match:
            result.append(alert)
    return result


async def async_get_alerts(coord, session) -> list[dict]:
    """Fetch and cache the current ZTM Gdańsk alert feed."""
    domain_data = coord.hass.data.setdefault(DOMAIN, {})
    cache = domain_data.setdefault("_ztm_alerts", {})
    lock = domain_data.setdefault("_ztm_alerts_lock", asyncio.Lock())

    async with lock:
        if (
            cache.get("data") is not None
            and time.monotonic() - cache.get("_ts", 0) < ZTM_ALERTS_TTL
        ):
            return cache["data"]
        try:
            text = await fetch_with_retry(session, ZTM_ALERTS_RSS_URL, as_text=True)
            data = parse_alerts(text)
            cache.update(data=data, _ts=time.monotonic())
            return data
        except Exception as err:  # noqa: BLE001 - alerts must not break departures
            _LOGGER.debug("ZTM alerts: fetch failed: %s", err)
            return cache.get("data", [])
