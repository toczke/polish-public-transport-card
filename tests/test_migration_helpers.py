"""Focused tests for the 2.0 registry migration helpers."""

from types import SimpleNamespace

import pytest

from mzkzg_transport import migration
from mzkzg_transport.const import DOMAIN, ENTITY_UNIQUE_PREFIX


class FakeEntity:
    def __init__(self, entity_id, unique_id, config_entry_id="entry-1"):
        self.entity_id = entity_id
        self.unique_id = unique_id
        self.config_entry_id = config_entry_id
        self.domain = entity_id.split(".", 1)[0]
        self.platform = DOMAIN


class FakeEntityRegistry:
    def __init__(self, entities):
        self.entities = {entity.entity_id: entity for entity in entities}

    def async_get(self, entity_id):
        return self.entities.get(entity_id)

    def async_get_entity_id(self, domain, platform, unique_id):
        for entity in self.entities.values():
            if (
                entity.domain == domain
                and entity.platform == platform
                and entity.unique_id == unique_id
            ):
                return entity.entity_id
        return None

    def async_entries_for_config_entry(self, config_entry_id):
        return [
            entity
            for entity in self.entities.values()
            if entity.config_entry_id == config_entry_id
        ]

    def async_entries_for_device(self, device_id, include_disabled_entities=False):
        return [
            entity
            for entity in self.entities.values()
            if getattr(entity, "device_id", None) == device_id
        ]

    def async_remove(self, entity_id):
        self.entities.pop(entity_id, None)

    def async_update_entity(self, entity_id, **kwargs):
        entity = self.entities.pop(entity_id)
        if "new_entity_id" in kwargs:
            entity.entity_id = kwargs["new_entity_id"]
            entity.domain = entity.entity_id.split(".", 1)[0]
        if "new_unique_id" in kwargs:
            entity.unique_id = kwargs["new_unique_id"]
        self.entities[entity.entity_id] = entity


class FakeDevice:
    def __init__(self, device_id):
        self.id = device_id
        self.via_device_id = None


class FakeDeviceRegistry:
    def __init__(self, devices):
        self.devices = devices
        self.removed = []
        self._next_id = 1

    def async_get_device(self, identifiers=None, connections=None):
        for identifier in identifiers or ():
            if identifier in self.devices:
                return self.devices[identifier]
        return None

    def async_get_or_create(
        self,
        *,
        config_entry_id,
        identifiers,
        name,
        manufacturer,
        model,
        entry_type=None,
        via_device_id=None,
    ):
        key = next(iter(identifiers))
        if key in self.devices:
            return self.devices[key]
        device = FakeDevice(f"device-{self._next_id}")
        self._next_id += 1
        device.name = name
        device.identifiers = identifiers
        device.via_device_id = via_device_id
        self.devices[key] = device
        return device

    def async_remove_device(self, device_id):
        self.removed.append(device_id)


class FakeConfigEntries:
    def __init__(self):
        self.updated = []
        self.removed = []

    def async_update_entry(self, entry, **kwargs):
        self.updated.append((entry, kwargs))
        for key, value in kwargs.items():
            setattr(entry, key, value)

    async def async_remove(self, entry_id):
        self.removed.append(entry_id)


def test_remove_stop_entities_removes_only_our_entities(monkeypatch):
    entities = [
        FakeEntity("sensor.stop", "polish_transport_ztm_1", "entry-1"),
        FakeEntity("sensor.other", "other", "entry-2"),
    ]
    for entity in entities:
        entity.device_id = "device-1"
    entity_registry = FakeEntityRegistry(entities)
    device_registry = FakeDeviceRegistry({(DOMAIN, "ztm_gdansk_1"): FakeDevice("device-1")})
    monkeypatch.setattr(migration.dr, "async_get", lambda hass: device_registry)
    monkeypatch.setattr(migration.er, "async_get", lambda hass: entity_registry)
    monkeypatch.setattr(
        migration.er,
        "async_entries_for_device",
        lambda registry, device_id, include_disabled_entities=False: registry.async_entries_for_device(device_id),
    )
    entry = SimpleNamespace(data={"provider": "ztm_gdansk"}, entry_id="entry-1")

    migration.async_remove_stop_entities(SimpleNamespace(), entry, "1")

    assert "sensor.stop" not in entity_registry.entities
    assert "sensor.other" in entity_registry.entities
    assert device_registry.removed == ["device-1"]


def test_remove_hub_entity_removes_merged_sensor(monkeypatch):
    entity_registry = FakeEntityRegistry(
        [FakeEntity("sensor.plk_odjazdy", f"{ENTITY_UNIQUE_PREFIX}_plk_rail_hub")]
    )
    monkeypatch.setattr(migration.er, "async_get", lambda hass: entity_registry)
    entry = SimpleNamespace(data={"provider": "plk_rail"}, entry_id="entry-1")

    migration.async_remove_hub_entity(SimpleNamespace(), entry)

    assert entity_registry.entities == {}


@pytest.mark.asyncio
async def test_normalize_hub_entity_id_renames_legacy_long_id(monkeypatch):
    entity_registry = FakeEntityRegistry(
        [
            FakeEntity(
                "sensor.polskie_linie_kolejowe_pkp_skm_pr_ic_odjazdy",
                f"{ENTITY_UNIQUE_PREFIX}_plk_rail_hub",
            )
        ]
    )
    monkeypatch.setattr(migration.er, "async_get", lambda hass: entity_registry)
    entry = SimpleNamespace(
        data={
            "provider": "plk_rail",
            "stops": [
                {"stop_id": "1", "name": "A"},
                {"stop_id": "2", "name": "B"},
            ],
        },
        entry_id="entry-1",
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda domain: [entry])
    )

    await migration.async_normalize_hub_entity_ids(hass)

    assert "sensor.plk_odjazdy" in entity_registry.entities


@pytest.mark.asyncio
async def test_normalize_hub_entity_id_keeps_user_renamed_entity(monkeypatch):
    entity_registry = FakeEntityRegistry(
        [FakeEntity("sensor.moj_hub", f"{ENTITY_UNIQUE_PREFIX}_plk_rail_hub")]
    )
    monkeypatch.setattr(migration.er, "async_get", lambda hass: entity_registry)
    entry = SimpleNamespace(
        data={
            "provider": "plk_rail",
            "stops": [{"stop_id": str(index), "name": "A"} for index in range(2)],
        },
        entry_id="entry-1",
    )
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda domain: [entry])
    )

    await migration.async_normalize_hub_entity_ids(hass)

    assert "sensor.moj_hub" in entity_registry.entities


@pytest.mark.asyncio
async def test_migrate_group_merges_entries_and_entities(monkeypatch):
    entry_a = SimpleNamespace(
        entry_id="entry-a",
        data={"provider": "ztm_gdansk", "stop_id": "1", "name": "Płocka 01"},
        options={},
        title="ZTM Gdańsk",
        unique_id="ztm_gdansk_1",
        version=1,
    )
    entry_b = SimpleNamespace(
        entry_id="entry-b",
        data={"provider": "ztm_gdansk", "stop_id": "2", "name": "Płocka 02"},
        options={"realtime_only": True},
        title="ZTM Gdańsk",
        unique_id="ztm_gdansk_2",
        version=1,
    )
    entities = [
        FakeEntity("sensor.mzkzg_ztm_1", "mzkzg_transport_ztm_gdansk_1", "entry-a"),
        FakeEntity("sensor.mzkzg_ztm_2", "mzkzg_transport_ztm_gdansk_2", "entry-b"),
    ]
    entity_registry = FakeEntityRegistry(entities)
    device_registry = FakeDeviceRegistry({})
    config_entries = FakeConfigEntries()
    monkeypatch.setattr(migration.dr, "async_get", lambda hass: device_registry)
    monkeypatch.setattr(migration.er, "async_get", lambda hass: entity_registry)
    monkeypatch.setattr(
        migration.er,
        "async_entries_for_config_entry",
        lambda registry, entry_id: registry.async_entries_for_config_entry(entry_id),
    )
    hass = SimpleNamespace(config_entries=config_entries)

    await migration._migrate_group(hass, "ztm_gdansk", [entry_a, entry_b])

    assert entry_a.version == 2
    assert entry_a.unique_id == "polish_transport_ztm_gdansk"
    assert entry_a.title == "ZTM Gdańsk"
    assert [stop["stop_id"] for stop in entry_a.data["stops"]] == ["1", "2"]
    assert entry_a.options == {"realtime_only": True}
    assert config_entries.removed == ["entry-b"]
    assert (DOMAIN, "ztm_gdansk") in device_registry.devices
    assert (DOMAIN, "ztm_gdansk_1") in device_registry.devices
    assert (DOMAIN, "ztm_gdansk_2") in device_registry.devices
    assert entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{ENTITY_UNIQUE_PREFIX}_ztm_gdansk_1"
    ) == "sensor.plocka_01_odjazdy"
    assert entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{ENTITY_UNIQUE_PREFIX}_ztm_gdansk_2"
    ) == "sensor.plocka_02_odjazdy"


@pytest.mark.asyncio
async def test_migrate_entries_groups_legacy_entries_by_provider(monkeypatch):
    calls = []

    async def fake_migrate_group(hass, provider, group):
        calls.append((provider, [entry.entry_id for entry in group]))

    monkeypatch.setattr(migration, "_migrate_group", fake_migrate_group)
    entries = [
        SimpleNamespace(data={"provider": "ztm_gdansk"}, version=1, entry_id="a", title="ZTM"),
        SimpleNamespace(data={"provider": "ztm_gdansk"}, version=1, entry_id="b", title="ZTM"),
        SimpleNamespace(data={"provider": "plk_rail"}, version=1, entry_id="c", title="PLK"),
    ]
    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(async_entries=lambda domain: entries),
    )

    await migration.async_migrate_entries(hass)

    assert sorted(calls) == [
        ("plk_rail", ["c"]),
        ("ztm_gdansk", ["a", "b"]),
    ]
    assert hass.data[DOMAIN]["_migrated_2_0"] is True


@pytest.mark.asyncio
async def test_migrate_entries_skips_when_everything_is_current(monkeypatch):
    called = []

    async def fake_migrate_group(*args):
        called.append(args)

    monkeypatch.setattr(migration, "_migrate_group", fake_migrate_group)
    entries = [
        SimpleNamespace(data={"provider": "ztm_gdansk"}, version=2, entry_id="a", title="ZTM")
    ]
    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(async_entries=lambda domain: entries),
    )

    await migration.async_migrate_entries(hass)

    assert called == []
    assert hass.data[DOMAIN]["_migrated_2_0"] is True
