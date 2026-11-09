"""Tests for GTFS-Realtime service alerts."""

import time

from google.transit import gtfs_realtime_pb2

from mzkzg_transport.gtfsrt_alerts import (
    alerts_for_stop,
    derive_alerts_url,
    parse_alerts,
)


def _feed(*, route="195", stop="2231", start=None, end=None):
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add()
    entity.id = "alert-1"
    alert = entity.alert
    alert.header_text.translation.add().text = "Awaryjna zmiana trasy"
    alert.description_text.translation.add().text = "Objazd dla linii 195"
    informed = alert.informed_entity.add()
    informed.route_id = route
    informed.stop_id = stop
    period = alert.active_period.add()
    period.start = start if start is not None else int(time.time() * 1000) - 1000
    period.end = end or 0
    return feed


def test_parse_alert():
    alerts = parse_alerts(_feed())
    assert alerts == [
        {
            "id": "alert-1",
            "title": "Awaryjna zmiana trasy",
            "content": "Objazd dla linii 195",
            "lines": ["195"],
            "stops": ["2231"],
            "url": "",
            "published": "",
        }
    ]


def test_expired_alert_is_skipped():
    now = int(time.time() * 1000)
    assert parse_alerts(_feed(start=now - 100_000, end=now - 50_000)) == []


def test_alert_matches_line_or_stop():
    alerts = parse_alerts(_feed())

    assert alerts_for_stop(alerts, "2231", {"1"})
    assert alerts_for_stop(alerts, "9999", {"195"})
    assert alerts_for_stop(alerts, "9999", {"1"}) == []


def test_general_alert_matches_every_stop():
    alerts = parse_alerts(_feed(route="", stop=""))
    assert alerts_for_stop(alerts, "9999", {"1"})


def test_derive_alert_url():
    api6 = {
        "rt_url": "https://api.zbiorkom.live/api6-open/lublin/gtfsRealtime/default/tripUpdates"
    }
    assert derive_alerts_url(api6).endswith("/serviceAlerts")
    assert derive_alerts_url({"alerts_url": "https://example.test/alerts.pb"}) == (
        "https://example.test/alerts.pb"
    )
    assert derive_alerts_url({"rt_url": "https://example.test/trip_updates.pb"}) is None
