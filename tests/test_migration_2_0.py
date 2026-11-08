"""Tests for the 2.0 entity and hub migration helpers."""

from types import SimpleNamespace

from mzkzg_transport.const import provider_entity_slug
from mzkzg_transport.migration import (
    entry_stops,
    is_legacy_hub_entity_id,
    slugify,
)


def test_slugify_handles_polish_names():
    assert slugify("Gdańsk Śródmieście") == "gdansk_srodmiescie"
    assert slugify("Płocka 01") == "plocka_01"
    assert slugify("") == "odjazdy"


def test_provider_entity_slugs_are_short():
    assert provider_entity_slug("plk_rail") == "plk"
    assert provider_entity_slug("gtfsrt_lublin") == "lublin"
    assert provider_entity_slug("zbiorkom_krakow") == "krakow"
    assert provider_entity_slug("ztm_gdansk") == "ztm_gdansk"


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


def test_legacy_hub_entity_id_detection():
    label = "Polskie Linie Kolejowe (PKP, SKM, PR, IC)"
    assert is_legacy_hub_entity_id(
        label, "sensor.polskie_linie_kolejowe_pkp_skm_pr_ic_odjazdy"
    )
    assert is_legacy_hub_entity_id(
        label, "sensor.polskie_linie_kolejowe_pkp_skm_pr_ic_odjazdy_2"
    )
    assert not is_legacy_hub_entity_id(label, "sensor.plk_odjazdy")
    assert not is_legacy_hub_entity_id(label, "sensor.moj_wlasny_hub")
