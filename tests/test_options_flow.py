"""Tests for the hub options flow."""

from types import SimpleNamespace

import pytest

from mzkzg_transport.config_flow import PolishTransportOptionsFlow


class FakeConfigEntries:
    def __init__(self):
        self.updated = []
        self.reloaded = []

    def async_update_entry(self, entry, **kwargs):
        self.updated.append((entry, kwargs))
        if "data" in kwargs:
            entry.data = kwargs["data"]

    async def async_reload(self, entry_id):
        self.reloaded.append(entry_id)


def _entry(stops=None, options=None, provider="ztm_gdansk"):
    return SimpleNamespace(
        data={
            "provider": provider,
            "stops": stops
            if stops is not None
            else [
                {"stop_id": "1", "name": "Płocka 01"},
                {"stop_id": "2", "name": "Płocka 02"},
            ],
            "name": "ZTM Gdańsk",
        },
        options=options or {},
        entry_id="entry-1",
        version=2,
    )


def _flow(entry):
    flow = PolishTransportOptionsFlow()
    flow.hass = SimpleNamespace(config_entries=FakeConfigEntries())
    flow.flow_id = "flow-1"
    flow._config_entry = entry
    return flow


@pytest.mark.asyncio
async def test_menu_offers_all_actions_for_multi_stop_hub():
    result = await _flow(_entry()).async_step_init()
    assert result["type"] == "menu"
    assert result["menu_options"] == ["settings", "add_stop", "remove_stop"]


@pytest.mark.asyncio
async def test_menu_hides_remove_for_single_stop_hub():
    result = await _flow(_entry([{"stop_id": "1", "name": "Płocka 01"}])).async_step_init()
    assert result["menu_options"] == ["settings", "add_stop"]


@pytest.mark.asyncio
async def test_settings_merges_options():
    flow = _flow(_entry(options={"sleep_enabled": True}))
    result = await flow.async_step_settings({"sleep_enabled": False, "realtime_only": True})
    assert result["type"] == "create_entry"
    assert result["data"] == {"sleep_enabled": False, "realtime_only": True}


@pytest.mark.asyncio
async def test_settings_form_includes_provider_specific_fields():
    flow = _flow(_entry(provider="mpk_lodz"))
    result = await flow.async_step_settings()
    keys = {str(key) for key in result["data_schema"].schema}
    assert any("fallback_min" in key for key in keys)


@pytest.mark.asyncio
async def test_add_stop_appends_and_reloads():
    entry = _entry()
    flow = _flow(entry)
    flow._stops = []

    result = await flow.async_step_add_stop({"stop_id": "999", "name": "Nowy"})

    assert result["type"] == "create_entry"
    assert entry.data["stops"][-1] == {"stop_id": "999", "name": "Nowy"}
    assert flow.hass.config_entries.reloaded == ["entry-1"]
    assert flow.hass.config_entries.updated


@pytest.mark.asyncio
async def test_add_stop_rejects_duplicate():
    flow = _flow(_entry())
    flow._stops = []

    result = await flow.async_step_add_stop({"stop_id": "1", "name": "Płocka 01"})

    assert result["type"] == "form"
    assert result["errors"]["base"] == "already_configured"


@pytest.mark.asyncio
async def test_add_stop_rejects_invalid_id():
    flow = _flow(_entry())
    flow._stops = []

    result = await flow.async_step_add_stop({"stop_id": "bad id!", "name": ""})

    assert result["type"] == "form"
    assert result["errors"]["stop_id"] == "invalid_stop_id"


@pytest.mark.asyncio
async def test_add_stop_searches_large_provider_list():
    flow = _flow(_entry())
    flow._stops = [
        {"id": str(index), "name": f"Płocka {index:02d}"} for index in range(60)
    ]

    first = await flow.async_step_add_stop()
    assert first["type"] == "form"
    assert any(getattr(key, "schema", "") == "stop_query" for key in first["data_schema"].schema)

    second = await flow.async_step_add_stop({"stop_query": "Płocka 42"})
    assert second["type"] == "form"
    stop_key = next(
        key for key in second["data_schema"].schema if getattr(key, "schema", "") == "stop_id"
    )
    selector = second["data_schema"].schema[stop_key]
    values = [option["value"] for option in selector.config["options"]]
    assert values == ["42"]


@pytest.mark.asyncio
async def test_remove_stop_aborts_for_last_stop():
    flow = _flow(_entry([{"stop_id": "1", "name": "Płocka 01"}]))
    result = await flow.async_step_remove_stop()
    assert result["type"] == "abort"
    assert result["reason"] == "last_stop"


@pytest.mark.asyncio
async def test_remove_stop_updates_data_and_cleans_registry(monkeypatch):
    entry = _entry()
    flow = _flow(entry)
    removed = []
    hubs = []
    monkeypatch.setattr(
        "mzkzg_transport.migration.async_remove_stop_entities",
        lambda hass, entry, stop_id: removed.append((entry.entry_id, stop_id)),
    )
    monkeypatch.setattr(
        "mzkzg_transport.migration.async_remove_hub_entity",
        lambda hass, entry: hubs.append(entry.entry_id),
    )

    result = await flow.async_step_remove_stop({"stop_id": "1"})

    assert result["type"] == "create_entry"
    assert [stop["stop_id"] for stop in entry.data["stops"]] == ["2"]
    assert removed == [("entry-1", "1")]
    assert hubs == ["entry-1"]
    assert flow.hass.config_entries.reloaded == ["entry-1"]


@pytest.mark.asyncio
async def test_remove_stop_rejects_unknown_id():
    flow = _flow(_entry())
    result = await flow.async_step_remove_stop({"stop_id": "missing"})
    assert result["type"] == "form"
    assert result["errors"]["stop_id"] == "invalid_stop_id"
