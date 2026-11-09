"""Tests for ZTM Gdańsk alert parsing and filtering."""

from types import SimpleNamespace

import pytest

from mzkzg_transport import ztm_alerts
from mzkzg_transport.ztm_alerts import (
    alerts_for_stop,
    async_get_alerts,
    parse_alerts,
)

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Bieżąca sytuacja komunikacyjna</title>
    <item>
      <title>Awaryjna zmiana trasy linii 195</title>
      <link>https://ztm.gda.pl/komunikaty/awaryjna-zmiana-trasy-linii-195,a,11936</link>
      <description>{"lineNumbers":["195"],"content":"Z powodu zamknięcia ruchu na ul. Wawelskiej objazd dla linii 195. Nieobsługiwane są przystanki Świętokrzyska 01, Platynowa 04 oraz Wawelska 01."}</description>
      <pubDate>Mon, 09 Nov 2026 08:10:00 +0100</pubDate>
    </item>
    <item>
      <title>Linie 117, 122, 143: zmiany na trasie w Sopocie</title>
      <link>https://ztm.gda.pl/komunikaty/linie-117-122-143,a,11994</link>
      <description>Objazd w Sopocie w dniu 11 listopada.</description>
      <pubDate>Fri, 06 Nov 2026 10:00:00 +0100</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_alerts_reads_json_description_and_fallback_lines():
    alerts = parse_alerts(RSS)

    assert len(alerts) == 2
    assert alerts[0]["lines"] == ["195"]
    assert "Wawelskiej" in alerts[0]["content"]
    assert alerts[1]["lines"] == ["117", "122", "143"]
    assert alerts[1]["content"] == "Objazd w Sopocie w dniu 11 listopada."


def test_alerts_for_stop_matches_line():
    alerts = parse_alerts(RSS)

    matched = alerts_for_stop(alerts, "Płocka 01", {"195"})

    assert [alert["lines"] for alert in matched] == [["195"]]


def test_alerts_for_stop_matches_stop_name_without_platform():
    alerts = parse_alerts(RSS)

    matched = alerts_for_stop(alerts, "Wawelska 01", {"175"})

    assert len(matched) == 1
    assert matched[0]["lines"] == ["195"]


def test_alerts_for_stop_ignores_unrelated_route_and_stop():
    alerts = parse_alerts(RSS)

    assert alerts_for_stop(alerts, "Płocka 01", {"175"}) == []


def test_parse_alerts_handles_broken_xml():
    assert parse_alerts("<rss><channel>") == []


@pytest.mark.asyncio
async def test_alert_cache_avoids_repeated_fetches(monkeypatch):
    calls = []

    async def fake_fetch(session, url, **kwargs):
        calls.append(url)
        return RSS

    monkeypatch.setattr(ztm_alerts, "fetch_with_retry", fake_fetch)
    hass = SimpleNamespace(data={})
    coord = SimpleNamespace(hass=hass)
    session = object()

    first = await async_get_alerts(coord, session)
    second = await async_get_alerts(coord, session)

    assert len(first) == 2
    assert second == first
    assert calls == [ztm_alerts.ZTM_ALERTS_RSS_URL]
