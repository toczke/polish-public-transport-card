"""Tests for the 2.0 entity and hub migration helpers."""

from types import SimpleNamespace

from mzkzg_transport.migration import entry_stops, slugify


def test_slugify_handles_polish_names():
    assert slugify("Gdańsk Śródmieście") == "gdansk_srodmiescie"
    assert slugify("Płocka 01") == "plocka_01"
    assert slugify("") == "odjazdy"


def test_entry_stops_from_legacy_single_stop():
    entry = SimpleNamespace(data={"stop_id": "3142", "name": "Majdanek - pomnik NŻ"})
    assert entry_stops(entry) == [{"stop_id": "3142", "name": "Majdanek - pomnik NŻ"}]


def test_entry_stops_from_hub_list():
    entry = SimpleNamespace(
        data={
            "stops": [
                {"stop_id": "3142", "name": "Majdanek - pomnik 02"},
                {"stop_id": "3151", "name": "Majdanek 01"},
            ]
        }
    )
    assert entry_stops(entry) == [
        {"stop_id": "3142", "name": "Majdanek - pomnik 02"},
        {"stop_id": "3151", "name": "Majdanek 01"},
    ]
