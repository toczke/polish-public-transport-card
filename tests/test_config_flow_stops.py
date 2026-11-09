"""Tests for large stop-list search in the config flow."""

from types import SimpleNamespace

import pytest

from mzkzg_transport.config_flow import (
    MAX_STOP_RESULTS,
    STOP_QUERY,
    PolishTransportConfigFlow,
    _match_stops,
)


STOPS = [
    {"id": "1", "name": "Łódź Kaliska"},
    {"id": "2", "name": "Kraków Główny"},
    {"id": "3", "name": "Kraków Bronowice"},
    {"id": "4", "name": "Gdańsk Wrzeszcz"},
]


def test_empty_query_returns_no_results():
    assert _match_stops(STOPS, "") == []
    assert _match_stops(STOPS, "   ") == []


def test_search_is_case_and_accent_insensitive():
    assert [s["id"] for s in _match_stops(STOPS, "lodz")] == ["1"]
    assert [s["id"] for s in _match_stops(STOPS, "KRAKOW")] == ["2", "3"]


def test_search_matches_stop_id_too():
    assert [s["id"] for s in _match_stops(STOPS, "3")] == ["3"]


def test_every_query_word_must_match():
    assert [s["id"] for s in _match_stops(STOPS, "krakow glowny")] == ["2"]
    assert _match_stops(STOPS, "krakow wrzeszcz") == []


def test_results_are_capped():
    stops = [{"id": str(i), "name": f"Stop {i}"} for i in range(MAX_STOP_RESULTS + 50)]
    result = _match_stops(stops, "stop")
    assert len(result) == MAX_STOP_RESULTS


def _form_keys(result: dict) -> list[str]:
    return [getattr(key, "schema", key) for key in result["data_schema"].schema]


def _large_flow() -> PolishTransportConfigFlow:
    flow = PolishTransportConfigFlow()
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda domain: [])
    )
    flow._provider = "zbiorkom_krakow"
    flow._stops = [
        {"id": "XYZ", "name": "Kraków Unikat"},
        *[
            {"id": str(1000 + i), "name": f"Kraków {i}"}
            for i in range(3807)
        ],
    ]
    flow.async_show_form = lambda **kwargs: {"type": "form", **kwargs}
    return flow


@pytest.mark.asyncio
async def test_large_list_first_step_offers_search_not_a_giant_dropdown():
    flow = _large_flow()
    result = await flow.async_step_stop()
    keys = _form_keys(result)
    assert STOP_QUERY in keys
    assert "stop_id" in keys
    # No query yet, so the stop_id field is plain text rather than 3808 options.
    selector = result["data_schema"].schema[
        next(key for key in result["data_schema"].schema if getattr(key, "schema", key) == "stop_id")
    ]
    assert selector is str


@pytest.mark.asyncio
async def test_large_list_search_narrows_to_selectable_matches():
    flow = _large_flow()
    result = await flow.async_step_stop({STOP_QUERY: "unikat"})
    keys = _form_keys(result)
    assert STOP_QUERY in keys
    assert "stop_id" in keys
    selector = result["data_schema"].schema[
        next(key for key in result["data_schema"].schema if getattr(key, "schema", key) == "stop_id")
    ]
    options = selector.config["options"]
    assert len(options) == 1
    assert options[0]["value"] == "XYZ"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_large_list_search_reports_no_matches():
    flow = _large_flow()
    result = await flow.async_step_stop({STOP_QUERY: "does-not-exist"})
    assert result["errors"][STOP_QUERY] == "no_stops_found"
