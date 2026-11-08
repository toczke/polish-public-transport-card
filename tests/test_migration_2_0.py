"""Tests for the 2.0 entity and hub migration helpers."""

from types import SimpleNamespace

from mzkzg_transport.const import DOMAIN, provider_entity_slug
from mzkzg_transport.migration import (
    _reconcile_entity,
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


class _FakeRegistry:
    """Minimal entity registry used by the reconciliation helper."""

    def __init__(self, entities):
        self.entities = {entity.entity_id: entity for entity in entities}

    def async_get(self, entity_id):
        return self.entities.get(entity_id)

    def async_get_entity_id(self, domain, platform, unique_id):
        for entity in self.entities.values():
            if (
                entity.entity_id.split(".", 1)[0] == domain
                and entity.platform == platform
                and entity.unique_id == unique_id
            ):
                return entity.entity_id
        return None

    def async_remove(self, entity_id):
        self.entities.pop(entity_id, None)

    def async_update_entity(self, entity_id, **kwargs):
        entity = self.entities.pop(entity_id)
        for key in ("entity_id", "unique_id", "config_entry_id", "device_id"):
            if key in kwargs:
                setattr(entity, key, kwargs[key])
        if "new_entity_id" in kwargs:
            entity.entity_id = kwargs["new_entity_id"]
        if "new_unique_id" in kwargs:
            entity.unique_id = kwargs["new_unique_id"]
        self.entities[entity.entity_id] = entity
        return entity


def _entity(entity_id, unique_id, platform=DOMAIN, config_entry_id="entry"):
    return SimpleNamespace(
        entity_id=entity_id,
        unique_id=unique_id,
        platform=platform,
        config_entry_id=config_entry_id,
        device_id=None,
    )


def test_reconcile_migrates_legacy_plk_sensor():
    registry = _FakeRegistry(
        [_entity("sensor.mzkzg_plk_258458", "mzkzg_transport_plk_rail_258458")]
    )
    _reconcile_entity(
        registry,
        domain="sensor",
        platform=DOMAIN,
        new_unique="polish_transport_plk_rail_258458",
        old_uniques=["mzkzg_transport_plk_rail_258458"],
        desired_entity_id="sensor.gdansk_srodmiescie_odjazdy",
        hub_entry_id="entry",
        device_id="device",
    )
    assert (
        registry.async_get_entity_id(
            "sensor", DOMAIN, "polish_transport_plk_rail_258458"
        )
        == "sensor.gdansk_srodmiescie_odjazdy"
    )


def test_heal_renames_new_unique_with_legacy_entity_id():
    registry = _FakeRegistry(
        [_entity("sensor.mzkzg_plk_258458", "polish_transport_plk_rail_258458")]
    )
    _reconcile_entity(
        registry,
        domain="sensor",
        platform=DOMAIN,
        new_unique="polish_transport_plk_rail_258458",
        old_uniques=["mzkzg_transport_plk_rail_258458"],
        desired_entity_id="sensor.gdansk_srodmiescie_odjazdy",
        hub_entry_id="entry",
        device_id="device",
        rename_existing=None,
    )
    assert registry.async_get("sensor.gdansk_srodmiescie_odjazdy") is not None


def test_heal_keeps_user_renamed_entity():
    registry = _FakeRegistry(
        [_entity("sensor.moj_plk", "polish_transport_plk_rail_258458")]
    )
    _reconcile_entity(
        registry,
        domain="sensor",
        platform=DOMAIN,
        new_unique="polish_transport_plk_rail_258458",
        old_uniques=["mzkzg_transport_plk_rail_258458"],
        desired_entity_id="sensor.gdansk_srodmiescie_odjazdy",
        hub_entry_id="entry",
        device_id="device",
        rename_existing=None,
    )
    assert registry.async_get("sensor.moj_plk") is not None
    assert registry.async_get("sensor.gdansk_srodmiescie_odjazdy") is None


def test_reconcile_removes_legacy_duplicate():
    registry = _FakeRegistry(
        [
            _entity("sensor.gdansk_srodmiescie_odjazdy", "polish_transport_plk_rail_258458"),
            _entity("sensor.mzkzg_plk_258458", "mzkzg_transport_plk_rail_258458"),
        ]
    )
    _reconcile_entity(
        registry,
        domain="sensor",
        platform=DOMAIN,
        new_unique="polish_transport_plk_rail_258458",
        old_uniques=["mzkzg_transport_plk_rail_258458"],
        desired_entity_id="sensor.gdansk_srodmiescie_odjazdy",
        hub_entry_id="entry",
        device_id="device",
        rename_existing=None,
    )
    assert registry.async_get("sensor.mzkzg_plk_258458") is None
    assert registry.async_get("sensor.gdansk_srodmiescie_odjazdy") is not None
