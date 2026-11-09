"""Tests for ZTM Gdańsk alert parsing and filtering."""

from types import SimpleNamespace

import pytest

from mzkzg_transport import ztm_alerts
from mzkzg_transport.ztm_alerts import (
    alerts_for_stop,
    async_get_alerts,
    parse_alert_page,
    parse_alerts,
    parse_page_alert_links,
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

URL_115 = (
    "https://ztm.gda.pl/komunikaty/"
    "9-50-brak-przejazdu-na-ul-smoluchowskiego-zmiana-trasy-linii-115-183-184-283,a,11995"
)
URL_195 = "https://ztm.gda.pl/komunikaty/awaryjna-zmiana-trasy-linii-195,a,11936"

PAGE = f"""
<html><body>
<div class="breaking-news-ticker" id="newsTicker11">
  <div class="bn-label">UWAGA</div>
  <div class="bn-news" style="margin-left: 20px;">
    <ul>
      <li><a href="{URL_115}"><div class="center"><span>9:50 Brak przejazdu na ul. Smoluchowskiego, zmiana trasy linii 115, 183, 184, 283</span></div></a></li>
      <li><a href="{URL_195}"><div class="center"><span>Awaryjna zmiana trasy linii 195</span></div></a></li>
    </ul>
  </div>
  <div class="bn-controls d-none d-lg-block"><button>prev</button><button>next</button></div>
</div>
</body></html>
"""

DETAIL_115 = """
<div class="article">
  <div class="row"><div class="col-lg-9">
    <h2 class="article-title">9:50 Brak przejazdu na ul. Smoluchowskiego, zmiana trasy linii 115, 183, 184, 283</h2>
    <div class="article-content mt-3">
      <p>9:50 Brak przejazdu na ul. Smoluchowskiego, zmiana trasy linii 115, 183, 184, 283</p>
      <p>W związku z brakiem przejazdu na ul. Smoluchowskiego, linie 115, 183, 184 i 283 kierowane są ulicami Sobieskiego i Traugutta.</p>
    </div>
    <div class="row"><div class="list"></div></div>
  </div>
  <div class="col-lg-3"><div class="menu-right"><ul><li><a href="other">Nie pokazuj tego komunikatu</a></li></ul></div></div>
</div>
</div>
"""

DETAIL_195 = """
<div class="article">
  <h2 class="article-title">Awaryjna zmiana trasy linii 195</h2>
  <div class="article-content mt-3">
    <p>Z powodu zamknięcia ruchu drogowego na ul. Wawelskiej objazd dla linii 195.</p>
    <p>Nieobsługiwane są przystanki Świętokrzyska 01, Platynowa 04 oraz Wawelska 01.</p>
  </div>
</div>
"""


def test_parse_alerts_reads_json_description_and_fallback_lines():
    alerts = parse_alerts(RSS)

    assert len(alerts) == 2
    assert alerts[0]["lines"] == ["195"]
    assert "Wawelskiej" in alerts[0]["content"]
    assert alerts[1]["lines"] == ["117", "122", "143"]
    assert alerts[1]["content"] == "Objazd w Sopocie w dniu 11 listopada."


def test_parse_page_alert_links_reads_ticker_only():
    assert parse_page_alert_links(PAGE) == [URL_115, URL_195]
    assert parse_page_alert_links("<html><body>no ticker</body></html>") == []


def test_parse_alert_page_extracts_title_content_and_lines():
    alert = parse_alert_page(DETAIL_115, URL_115)

    assert alert is not None
    assert alert["title"].startswith("9:50 Brak przejazdu")
    assert alert["lines"] == ["115", "183", "184", "283"]
    assert "Sobieskiego i Traugutta" in alert["content"]
    assert "Nie pokazuj tego komunikatu" not in alert["content"]


def test_parse_alert_page_removes_duplicated_title_paragraph():
    alert = parse_alert_page(DETAIL_115, URL_115)

    assert alert is not None
    assert not alert["content"].startswith("9:50 Brak przejazdu")


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


def test_alerts_for_stop_matches_scraped_ticker_alert():
    alert = parse_alert_page(DETAIL_115, URL_115)

    assert alert is not None
    assert alerts_for_stop([alert], "Płocka 01", {"115"}) == [alert]
    assert alerts_for_stop([alert], "Płocka 01", {"195"}) == []


def test_parse_alerts_handles_broken_xml():
    assert parse_alerts("<rss><channel>") == []


@pytest.mark.asyncio
async def test_alert_cache_merges_ticker_and_rss(monkeypatch):
    calls = []

    async def fake_fetch(session, url, **kwargs):
        calls.append(url)
        if url == ztm_alerts.ZTM_ALERTS_PAGE_URL:
            return PAGE
        if url == URL_115:
            return DETAIL_115
        if url == URL_195:
            return DETAIL_195
        return RSS

    monkeypatch.setattr(ztm_alerts, "fetch_with_retry", fake_fetch)
    hass = SimpleNamespace(data={})
    coord = SimpleNamespace(hass=hass)
    session = object()

    first = await async_get_alerts(coord, session)
    second = await async_get_alerts(coord, session)

    assert [alert["title"] for alert in first] == [
        "9:50 Brak przejazdu na ul. Smoluchowskiego, zmiana trasy linii 115, 183, 184, 283",
        "Awaryjna zmiana trasy linii 195",
        "Linie 117, 122, 143: zmiany na trasie w Sopocie",
    ]
    assert second == first
    assert calls == [
        ztm_alerts.ZTM_ALERTS_PAGE_URL,
        URL_115,
        URL_195,
        ztm_alerts.ZTM_ALERTS_RSS_URL,
    ]
