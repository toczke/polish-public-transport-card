"""Additional stop loader coverage for provider-specific flows."""

import io
import zipfile
from types import SimpleNamespace

import pytest

from mzkzg_transport import config_flow_stops, provider_gtfsrt
from mzkzg_transport.config_flow_stops import (
    _load_gtfs_stops,
    _load_gtfsrt_stops,
    _load_krakow_stops,
    _load_mzk_stops,
    _load_plk_stations,
    _load_stops,
    _load_time4bus_stops,
    _load_zkm_stops,
)
from mzkzg_transport.const import PROVIDER_LODZ, PROVIDER_TCZEW


class FakeResponse:
    def __init__(self, data=None, raw=None, status=200):
        self._data = data
        self._raw = raw
        self.status = status
        self.content_length = len(raw) if raw is not None else None
        self.content = self

    def raise_for_status(self):
        return None

    async def json(self):
        return self._data

    async def text(self):
        return self._data

    async def read(self):
        return self._raw

    async def iter_chunked(self, size):
        for index in range(0, len(self._raw), size):
            yield self._raw[index : index + size]


class FakeGet:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeGet(self.responses.pop(0))


def _install(monkeypatch, responses):
    session = FakeSession(responses)
    monkeypatch.setattr(config_flow_stops, "async_get_clientsession", lambda hass: session)
    return session


def _zip_bytes(rows, filename="stops.txt"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(filename, rows)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_load_zkm_stops_accepts_list_and_dict(monkeypatch):
    session = _install(
        monkeypatch,
        [
            FakeResponse(
                [
                    {"stopId": "2", "stopName": "B"},
                    {"stopId": "1", "stopDesc": "A"},
                ]
            )
        ],
    )

    stops = await _load_zkm_stops(SimpleNamespace(hass=SimpleNamespace()))

    assert stops == [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
    assert "ssl" in session.calls[0][1]

    _install(monkeypatch, [FakeResponse({"stops": [{"stopId": "3", "stopName": "C"}]})])
    assert await _load_zkm_stops(SimpleNamespace(hass=SimpleNamespace())) == [
        {"id": "3", "name": "C"}
    ]


@pytest.mark.asyncio
async def test_load_time4bus_stops_formats_code_and_skips_bad_rows(monkeypatch):
    _install(
        monkeypatch,
        [
            FakeResponse(
                {
                    "items": [
                        {"fullcode": "2", "name": "Rynek", "code": "02"},
                        {"id": 1, "groupName": "Dworzec"},
                        {"id": None, "name": "bad"},
                        "not-a-dict",
                    ]
                }
            )
        ],
    )

    stops = await _load_time4bus_stops(
        SimpleNamespace(hass=SimpleNamespace()), PROVIDER_TCZEW
    )

    assert stops == [
        {"id": "1", "name": "Dworzec"},
        {"id": "2", "name": "Rynek (02)"},
    ]


@pytest.mark.asyncio
async def test_load_plk_stations_paginates_marks_pkp_and_sends_key(monkeypatch):
    session = _install(
        monkeypatch,
        [
            FakeResponse(
                {
                    "stations": [
                        {"id": 1, "name": "Gdańsk"},
                        {"id": 2, "name": "Zabierzów PKP"},
                    ],
                    "totalPages": 2,
                }
            ),
            FakeResponse({"stations": [{"id": 3, "name": "Sopot"}], "totalPages": 2}),
        ],
    )

    stops = await _load_plk_stations(
        SimpleNamespace(hass=SimpleNamespace(), _api_key="secret")
    )

    assert stops == [
        {"id": "1", "name": "Gdańsk PKP"},
        {"id": "3", "name": "Sopot PKP"},
        {"id": "2", "name": "Zabierzów PKP"},
    ]
    assert session.calls[0][1]["headers"]["X-API-Key"] == "secret"
    assert len(session.calls) == 2


@pytest.mark.asyncio
async def test_load_krakow_stops_filters_malformed_rows(monkeypatch):
    _install(
        monkeypatch,
        [
            FakeResponse(
                {
                    "stops": [
                        ["1", 100, "Kraków", "Główny"],
                        ["2", 200, "Kraków", "Bronowice"],
                        ["bad"],
                        [None, 1, "No id", "x"],
                    ]
                }
            )
        ],
    )

    stops = await _load_krakow_stops(SimpleNamespace(hass=SimpleNamespace()))

    assert stops == [
        {"id": "2", "name": "Kraków Bronowice"},
        {"id": "1", "name": "Kraków Główny"},
    ]


@pytest.mark.asyncio
async def test_load_krakow_stops_returns_empty_on_error(monkeypatch):
    _install(monkeypatch, [RuntimeError("boom")])

    assert await _load_krakow_stops(SimpleNamespace(hass=SimpleNamespace())) == []


@pytest.mark.asyncio
async def test_load_gtfs_stops_parses_zip_and_deduplicates(monkeypatch):
    raw = _zip_bytes(
        "stop_id,stop_code,stop_name\n"
        "1,101,Alpha\n"
        "2,102,Beta\n"
        "2,102,Beta duplicate\n"
        "3,103,\n"
    )
    _install(monkeypatch, [FakeResponse(raw=raw)])

    stops = await _load_gtfs_stops(
        SimpleNamespace(hass=SimpleNamespace()), "https://example.test/gtfs.zip"
    )

    assert stops == [{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Beta"}]


@pytest.mark.asyncio
async def test_load_gtfs_stops_supports_stop_code_column(monkeypatch):
    raw = _zip_bytes("stop_code,stop_name\n205,Łódź\n")
    _install(monkeypatch, [FakeResponse(raw=raw)])

    stops = await _load_gtfs_stops(
        SimpleNamespace(hass=SimpleNamespace()),
        "https://example.test/gtfs.zip",
        id_column="stop_code",
    )

    assert stops == [{"id": "205", "name": "Łódź"}]


@pytest.mark.asyncio
async def test_load_gtfs_stops_returns_empty_without_stops_file(monkeypatch):
    raw = _zip_bytes("x", filename="other.txt")
    _install(monkeypatch, [FakeResponse(raw=raw)])

    assert await _load_gtfs_stops(
        SimpleNamespace(hass=SimpleNamespace()), "https://example.test/gtfs.zip"
    ) == []


@pytest.mark.asyncio
async def test_load_gtfs_stops_rejects_oversized_archive(monkeypatch):
    _install(
        monkeypatch,
        [FakeResponse(raw=b"x", status=200)],
    )
    session = config_flow_stops.async_get_clientsession(SimpleNamespace())
    session.responses[0].content_length = 300 * 1024 * 1024

    assert await _load_gtfs_stops(
        SimpleNamespace(hass=SimpleNamespace()), "https://example.test/gtfs.zip"
    ) == []


@pytest.mark.asyncio
async def test_load_mzk_stops_reads_gtfs_cache(monkeypatch):
    async def fake_gtfs():
        return SimpleNamespace(
            stops={"2": {"name": "B"}, "1": {"name": "A"}},
        )

    monkeypatch.setattr(
        "mzkzg_transport.gtfs_provider.get_gtfs_data", fake_gtfs
    )

    stops = await _load_mzk_stops(SimpleNamespace(hass=SimpleNamespace()))

    assert stops == [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]


@pytest.mark.asyncio
async def test_load_gtfsrt_stops_dispatches_and_merges_tram(monkeypatch):
    async def fake_gtfs(self, url, id_column="stop_id"):
        if url == "tram":
            return [{"id": "2", "name": "Tram B"}, {"id": "3", "name": "Tram C"}]
        return [{"id": "1", "name": "Bus A"}, {"id": "2", "name": "Bus B"}]

    monkeypatch.setattr(config_flow_stops, "_load_gtfs_stops", fake_gtfs)
    monkeypatch.setattr(
        provider_gtfsrt,
        "GTFSRT_CITIES",
        {
            "city": {
                "gtfs_url": "bus",
                "gtfs_url_tram": "tram",
            }
        },
    )

    stops = await _load_gtfsrt_stops(SimpleNamespace(hass=SimpleNamespace()), "city")

    assert stops == [
        {"id": "1", "name": "Bus A"},
        {"id": "2", "name": "Bus B"},
        {"id": "3", "name": "Tram C"},
    ]


@pytest.mark.asyncio
async def test_load_gtfsrt_stops_handles_missing_unavailable_and_krakow(monkeypatch):
    ctx = SimpleNamespace(hass=SimpleNamespace())
    monkeypatch.setattr(provider_gtfsrt, "GTFSRT_CITIES", {})
    assert await _load_gtfsrt_stops(ctx, "missing") == []

    monkeypatch.setattr(
        provider_gtfsrt, "GTFSRT_CITIES", {"gone": {"unavailable": True}}
    )
    assert await _load_gtfsrt_stops(ctx, "gone") == []

    async def fake_krakow(self):
        return [{"id": "k", "name": "Kraków"}]

    monkeypatch.setattr(config_flow_stops, "_load_krakow_stops", fake_krakow)
    monkeypatch.setattr(
        provider_gtfsrt,
        "GTFSRT_CITIES",
        {"zbiorkom_krakow": {"label": "Kraków"}},
    )
    assert await _load_gtfsrt_stops(ctx, "zbiorkom_krakow") == [
        {"id": "k", "name": "Kraków"}
    ]


@pytest.mark.asyncio
async def test_load_gtfsrt_stops_gzm_dynamic_url(monkeypatch):
    calls = []

    async def fake_url(session, package_id):
        calls.append(package_id)
        return "gzm"

    async def fake_gtfs(self, url, id_column="stop_id"):
        calls.append(url)
        return [{"id": "1", "name": "GZM"}]

    monkeypatch.setattr(provider_gtfsrt, "_get_gzm_gtfs_url", fake_url)
    monkeypatch.setattr(config_flow_stops, "_load_gtfs_stops", fake_gtfs)
    monkeypatch.setattr(
        config_flow_stops, "async_get_clientsession", lambda hass: object()
    )
    monkeypatch.setattr(
        provider_gtfsrt,
        "GTFSRT_CITIES",
        {"gzm": {"gtfs_package_id": "pkg"}},
    )

    assert await _load_gtfsrt_stops(
        SimpleNamespace(hass=SimpleNamespace()), "gzm"
    ) == [{"id": "1", "name": "GZM"}]
    assert calls == ["pkg", "gzm"]


@pytest.mark.asyncio
async def test_load_stops_lodz_uses_stop_code(monkeypatch):
    calls = []

    async def fake_gtfs(self, url, id_column="stop_id"):
        calls.append((url, id_column))
        return []

    monkeypatch.setattr(config_flow_stops, "_load_gtfs_stops", fake_gtfs)

    await _load_stops(SimpleNamespace(hass=SimpleNamespace()), PROVIDER_LODZ)

    assert calls == [("https://cdn.zbiorkom.live/gtfs/lodz.zip", "stop_code")]
