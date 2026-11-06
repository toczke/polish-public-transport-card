import csv
import logging
import struct
import zipfile
from datetime import date as dt_date
from io import BytesIO, StringIO

import aiohttp
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Bytes pulled from the end of a remote zip — enough for the central directory
# of a GTFS feed (~20 members), which is what zipfile needs to locate a member.
_ZIP_TAIL_BYTES = 65536


async def _fetch_range(session, url: str, start: int, end: int):
    """Fetch bytes [start, end] of a remote file. Returns (data, status) or (None, status)."""
    headers = {"Range": f"bytes={start}-{end}"}
    async with session.get(
        url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
    ) as resp:
        if resp.status not in (200, 206):
            return None, resp.status
        return await resp.read(), resp.status


async def _peek_zip_member(session, url: str, size: int, member: str) -> str | None:
    """Read a single small member out of a remote zip using HTTP range requests.

    Avoids downloading the whole archive (GZM ships ~10 MB per zip, 20+ zips) just to
    read a few hundred bytes of calendar.txt. Returns the decoded text, or None if the
    member is absent or the server does not honour range requests.
    """
    tail_len = min(_ZIP_TAIL_BYTES, size)
    data, status = await _fetch_range(session, url, size - tail_len, size - 1)
    if data is None:
        return None

    if status == 200:
        # Server ignored the Range header and sent the whole archive.
        with zipfile.ZipFile(BytesIO(data)) as zf:
            return zf.read(member).decode("utf-8-sig")

    # Rebuild a sparse copy of the archive: only the regions we actually fetch are
    # populated, which is all zipfile touches (end-of-central-directory, then the
    # member's local header + data at its recorded offset). Slice assignment must stay
    # length-exact or every recorded offset shifts.
    if len(data) != tail_len:
        return None
    buf = bytearray(size)
    buf[size - tail_len:] = data

    with zipfile.ZipFile(BytesIO(bytes(buf))) as zf:
        info = zf.getinfo(member)

    start = info.header_offset
    # local header (30 B) + filename + extra field (padded) + compressed payload
    end = min(start + 30 + len(info.filename) + 128 + info.compress_size + 32, size - 1)
    chunk, _ = await _fetch_range(session, url, start, end)
    if chunk is None:
        return None
    buf[start:start + len(chunk)] = chunk

    with zipfile.ZipFile(BytesIO(bytes(buf))) as zf:
        return zf.read(member).decode("utf-8-sig")


def _calendar_covers(text: str, target) -> bool:
    """True if calendar.txt declares a service running on the target date."""
    day_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][target.weekday()]
    target_str = target.strftime("%Y%m%d")
    for row in csv.DictReader(StringIO(text)):
        if row.get(day_name) != "1":
            continue
        if (row.get("start_date") or "") <= target_str <= (row.get("end_date") or ""):
            return True
    return False


async def _get_gzm_gtfs_url(session, package_id: str, target_date=None) -> str | None:
    """Fetch the GZM GTFS URL covering target_date (default: today) from the CKAN API.

    GZM publishes one archive per service day rather than a single rolling feed, and the
    CKAN resource list is not ordered by the day each archive covers — its names only
    carry the *publication* date. Picking an arbitrary resource yields an archive whose
    calendar.txt does not include today, so every trip is filtered out as inactive and
    the stop reports no departures (issue #13). Probe each candidate's calendar.txt and
    take the first one that actually covers the day we need.
    """
    try:
        ckan_url = f"https://otwartedane.metropoliagzm.pl/api/3/action/package_show?id={package_id}"
        async with session.get(ckan_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

        resources = [
            r
            for r in data.get("result", {}).get("resources", [])
            if "schedule" in (r.get("name") or "").lower()
            and (r.get("format") or "").lower() == "zip"
        ]
        if not resources:
            return None

        if target_date is None:
            target_date = dt_util.now().date()

        # Most recently published first, so a re-issued archive wins over a stale one.
        resources.sort(key=lambda r: r.get("last_modified") or r.get("created") or "", reverse=True)

        for r in resources:
            url, size = r.get("url"), r.get("size")
            if not url or not size:
                continue
            try:
                calendar = await _peek_zip_member(session, url, int(size), "calendar.txt")
            except (KeyError, zipfile.BadZipFile, aiohttp.ClientError, OSError) as e:
                _LOGGER.debug("GZM: could not inspect %s: %s", r.get("name"), e)
                continue
            if calendar and _calendar_covers(calendar, target_date):
                _LOGGER.debug("GZM: using %s for %s", r.get("name"), target_date)
                return url

        _LOGGER.warning(
            "GZM: no GTFS archive covers %s; falling back to most recent (%s)",
            target_date,
            resources[0].get("name"),
        )
        return resources[0].get("url")
    except Exception as e:
        _LOGGER.debug("GZM CKAN lookup failed: %s", e)
        return None

