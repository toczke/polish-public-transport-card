#!/usr/bin/env python3
"""Validate every configured transport provider and emit a status report.

Designed for a weekly GitHub Actions schedule. No Home Assistant imports are
required; only the provider catalogue and URL constants are used.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components"))

from mzkzg_transport.const import (  # noqa: E402
    KIEDYPRZYJEDZIE_BASE_URLS,
    MZK_GTFS_URL,
    PLK_API_BASE,
    TIME4BUS_BYTOW_STOPS_URL,
    TIME4BUS_TCZEW_STOPS_URL,
    ZKM_GDYNIA_STOPS_URL,
    ZTM_GDANSK_STOPS_URL,
)
from mzkzg_transport.gtfsrt_cities import GTFSRT_CITIES  # noqa: E402

USER_AGENT = "polish-public-transport-card-provider-check/1.0"
TIMEOUT = 90
RETRIES = 3


@dataclass
class Result:
    name: str
    kind: str
    status: str
    details: str = ""
    extra: dict = field(default_factory=dict)


def _fetch(url: str, *, verify: bool = True, timeout: int = TIMEOUT) -> tuple[int, bytes, dict]:
    context = ssl.create_default_context() if verify else ssl._create_unverified_context()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() if exc.fp else b"", dict(exc.headers or {})


def _fetch_with_retry(url: str, *, verify: bool = True) -> tuple[int, bytes]:
    last: tuple[int, bytes] = (0, b"")
    for attempt in range(RETRIES):
        try:
            status, body, _headers = _fetch(url, verify=verify)
            last = (status, body)
            if status not in (429, 500, 502, 503, 504):
                return last
        except Exception:
            last = (0, b"")
        if attempt < RETRIES - 1:
            time.sleep(2 ** attempt)
    return last


def _gtfs_check(provider: str, cfg: dict) -> Result:
    if cfg.get("unavailable"):
        return Result(provider, "GTFS", "SKIP", "source removed from zbiorkom.live")

    gtfs_url = cfg.get("gtfs_url")
    if not gtfs_url and cfg.get("gtfs_package_id"):
        package_id = cfg["gtfs_package_id"]
        ckan = f"https://otwartedane.metropoliagzm.pl/api/3/action/package_show?id={package_id}"
        status, body = _fetch_with_retry(ckan)
        if status != 200:
            return Result(provider, "GTFS", "FAIL", f"CKAN HTTP {status}")
        try:
            payload = json.loads(body)
            resources = payload.get("result", {}).get("resources", [])
            if not payload.get("success") or not resources:
                return Result(provider, "GTFS", "FAIL", "CKAN package has no resources")
            first = resources[0].get("url", "")
            if not first:
                return Result(provider, "GTFS", "FAIL", "CKAN resource without URL")
            return Result(provider, "GTFS", "OK", f"CKAN package, {len(resources)} resources")
        except Exception as exc:
            return Result(provider, "GTFS", "FAIL", f"CKAN parse error: {exc}")

    if not gtfs_url:
        return Result(provider, "GTFS", "FAIL", "no GTFS URL configured")

    status, body = _fetch_with_retry(gtfs_url)
    if status != 200:
        return Result(provider, "GTFS", "FAIL", f"HTTP {status}")
    if not body:
        return Result(provider, "GTFS", "FAIL", "empty response")
    try:
        with zipfile.ZipFile(BytesIO(body)) as archive:
            if "stops.txt" not in archive.namelist():
                return Result(provider, "GTFS", "FAIL", "zip has no stops.txt")
            stops = archive.read("stops.txt").decode("utf-8-sig").splitlines()
            if len(stops) < 2:
                return Result(provider, "GTFS", "FAIL", "stops.txt is empty")
            feed_start = feed_end = None
            if "feed_info.txt" in archive.namelist():
                lines = archive.read("feed_info.txt").decode("utf-8-sig").splitlines()
                if len(lines) > 1:
                    header = lines[0].split(",")
                    values = lines[1].split(",")
                    row = dict(zip(header, values))
                    feed_start = row.get("feed_start_date")
                    feed_end = row.get("feed_end_date")
    except zipfile.BadZipFile:
        return Result(provider, "GTFS", "FAIL", "response is not a valid zip")
    except Exception as exc:
        return Result(provider, "GTFS", "FAIL", f"GTFS parse error: {exc}")

    detail = f"{len(stops) - 1} stops"
    if feed_end:
        try:
            end = datetime.strptime(feed_end, "%Y%m%d").date()
            today = date.today()
            if today > end:
                return Result(provider, "GTFS", "FAIL", f"{detail}, feed expired {feed_end}")
            if (end - today).days <= 3:
                return Result(provider, "GTFS", "WARN", f"{detail}, feed ends {feed_end}")
            detail += f", valid to {feed_end}"
        except ValueError:
            detail += f", invalid feed_end={feed_end}"
    return Result(provider, "GTFS", "OK", detail)


def _protobuf_count(body: bytes) -> int | None:
    try:
        from google.transit import gtfs_realtime_pb2

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(body)
        return len(feed.entity)
    except Exception:
        return None


def _feed_check(provider: str, kind: str, url: str | None) -> Result:
    if not url:
        return Result(provider, kind, "SKIP", "not configured")
    status, body = _fetch_with_retry(url)
    if status in (403, 429):
        return Result(provider, kind, "WARN", f"HTTP {status} (rate limited)")
    if status != 200:
        return Result(provider, kind, "FAIL", f"HTTP {status}")
    if not body:
        return Result(provider, kind, "FAIL", "empty response")
    entities = _protobuf_count(body) if kind.startswith("GTFS-RT") else None
    if entities is not None:
        if entities == 0:
            return Result(provider, kind, "WARN", f"{len(body)} bytes, 0 entities")
        return Result(provider, kind, "OK", f"{len(body)} bytes, {entities} entities")
    return Result(provider, kind, "OK", f"{len(body)} bytes")


def check_city(provider: str, cfg: dict) -> list[Result]:
    results = [_gtfs_check(provider, cfg)]
    if cfg.get("unavailable"):
        return results
    results.append(_feed_check(provider, "GTFS-RT", cfg.get("rt_url")))
    results.append(_feed_check(provider, "positions", cfg.get("positions_url")))
    return results


def check_misc() -> list[Result]:
    results: list[Result] = []

    for name, url, verify in (
        ("ztm_gdansk", ZTM_GDANSK_STOPS_URL, True),
        ("zkm_gdynia", ZKM_GDYNIA_STOPS_URL, False),
        ("mzk_wejherowo", MZK_GTFS_URL, True),
        ("time4bus_tczew", TIME4BUS_TCZEW_STOPS_URL, True),
        ("time4bus_bytow", TIME4BUS_BYTOW_STOPS_URL, True),
        ("zbiorkom_krakow", "https://api.zbiorkom.live/api6-open/krakow/stops", True),
    ):
        status, body = _fetch_with_retry(url, verify=verify)
        if status != 200 or not body:
            results.append(Result(name, "stops", "FAIL", f"HTTP {status}"))
        else:
            note = "ok"
            if name == "zkm_gdynia":
                note = "ok (TLS certificate bypass)"
            results.append(Result(name, "stops", "OK", f"{len(body)} bytes, {note}"))

    for name, url in KIEDYPRZYJEDZIE_BASE_URLS.items():
        status, body = _fetch_with_retry(url)
        if status != 200 or not body:
            results.append(Result(name, "website", "FAIL", f"HTTP {status}"))
        else:
            results.append(Result(name, "website", "OK", f"{len(body)} bytes"))

    try:
        status, _body, _headers = _fetch(PLK_API_BASE)
        if status in (401, 403):
            results.append(Result("plk_rail", "API", "SKIP", f"HTTP {status} (API key required)"))
        elif status == 200:
            results.append(Result("plk_rail", "API", "OK", "reachable"))
        else:
            results.append(Result("plk_rail", "API", "FAIL", f"HTTP {status}"))
    except Exception as exc:
        results.append(Result("plk_rail", "API", "FAIL", str(exc)))

    return results


def _markdown(results: list[Result]) -> str:
    order = {"FAIL": 0, "WARN": 1, "OK": 2, "SKIP": 3}
    results = sorted(results, key=lambda r: (order.get(r.status, 9), r.name, r.kind))
    counts = {key: sum(1 for r in results if r.status == key) for key in order}
    lines = [
        "# Provider status",
        "",
        f"Checked: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"**FAIL:** {counts['FAIL']}  **WARN:** {counts['WARN']}  "
        f"**OK:** {counts['OK']}  **SKIP:** {counts['SKIP']}",
        "",
        "| Provider | Check | Status | Details |",
        "|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| `{result.name}` | {result.kind} | **{result.status}** | "
            f"{result.details.replace('|', '/')} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", default="provider-status.md")
    parser.add_argument("--json", default="provider-status.json")
    parser.add_argument("--only", default="", help="comma-separated provider prefixes")
    args = parser.parse_args()

    only = tuple(p.strip() for p in args.only.split(",") if p.strip())
    cities = {
        name: cfg for name, cfg in GTFSRT_CITIES.items()
        if not only or name.startswith(only)
    }

    results: list[Result] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(check_city, name, cfg) for name, cfg in cities.items()]
        for future in futures:
            results.extend(future.result())
    if not only:
        results.extend(check_misc())

    markdown = _markdown(results)
    Path(args.markdown).write_text(markdown, encoding="utf-8")
    Path(args.json).write_text(
        json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(markdown)
    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
