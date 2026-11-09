"""Coverage for the initial config-flow steps and Łódź groups."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mzkzg_transport import config_flow
from mzkzg_transport.config_flow import PolishTransportConfigFlow
from mzkzg_transport.const import (
    CONF_API_KEY,
    CONF_OFFLINE_ONLY,
    CONF_PLK_TIER,
    DOMAIN,
    PROVIDER_LODZ,
    PROVIDER_PLK,
    PROVIDER_ZTM,
)

def _flow(provider=None, lodz_stops=None, mock_steps=True):
    flow = PolishTransportConfigFlow()
    flow.hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(async_entries=lambda domain: []),
    )
    flow._provider = provider
    flow._lodz_stops = lodz_stops or []
    flow.async_show_form = lambda **kwargs: {"type": "form", **kwargs}
    flow.async_create_entry = lambda **kwargs: {"type": "create_entry", **kwargs}
    flow.async_abort = lambda **kwargs: {"type": "abort", **kwargs}
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = lambda: None
    if mock_steps:
        flow.async_step_stop = AsyncMock(return_value={"type": "stop"})
        flow.async_step_api_key = AsyncMock(return_value={"type": "api_key"})
        flow.async_step_lodz_mode = AsyncMock(return_value={"type": "lodz_mode"})
        flow.async_step_lodz_group = AsyncMock(return_value={"type": "lodz_group"})
    return flow


@pytest.mark.asyncio
async def test_user_step_form_lists_providers():
    flow = _flow()

    result = await flow.async_step_user()

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    provider_key = next(
        key for key in result["data_schema"].schema if getattr(key, "schema", "") == "provider"
    )
    assert PROVIDER_ZTM in result["data_schema"].schema[provider_key].container


@pytest.mark.asyncio
async def test_user_step_loads_stops_for_regular_provider(monkeypatch):
    calls = []

    async def fake_load(self, provider):
        calls.append(provider)
        return [{"id": "1", "name": "Stop"}]

    monkeypatch.setattr(config_flow, "_load_stops", fake_load)
    flow = _flow()

    result = await flow.async_step_user({"provider": PROVIDER_ZTM})

    assert result == {"type": "stop"}
    assert calls == [PROVIDER_ZTM]
    assert flow._stops == [{"id": "1", "name": "Stop"}]


@pytest.mark.asyncio
async def test_user_step_routes_lodz_to_mode_step():
    flow = _flow()

    result = await flow.async_step_user({"provider": PROVIDER_LODZ})

    assert result == {"type": "lodz_mode"}
    flow.async_step_lodz_mode.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_step_reuses_plk_key_from_memory(monkeypatch):
    async def fake_load(self, provider):
        return []

    monkeypatch.setattr(config_flow, "_load_stops", fake_load)
    flow = _flow()
    flow.hass.data[DOMAIN] = {"_global": {CONF_API_KEY: "stored"}}

    result = await flow.async_step_user({"provider": PROVIDER_PLK})

    assert result == {"type": "stop"}
    assert flow._api_key == "stored"


@pytest.mark.asyncio
async def test_user_step_reuses_plk_key_from_entry(monkeypatch):
    async def fake_load(self, provider):
        return []

    monkeypatch.setattr(config_flow, "_load_stops", fake_load)
    flow = _flow()
    flow.hass.config_entries.async_entries = lambda domain: [
        SimpleNamespace(data={"provider": PROVIDER_PLK, "api_key": "entry-key"})
    ]

    result = await flow.async_step_user({"provider": PROVIDER_PLK})

    assert result == {"type": "stop"}
    assert flow._api_key == "entry-key"


@pytest.mark.asyncio
async def test_user_step_asks_for_plk_key_when_missing():
    flow = _flow()

    result = await flow.async_step_user({"provider": PROVIDER_PLK})

    assert result == {"type": "api_key"}
    flow.async_step_api_key.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_key_step_requires_key():
    flow = _flow(PROVIDER_PLK, mock_steps=False)

    result = await flow.async_step_api_key({CONF_API_KEY: "  "})

    assert result["type"] == "form"
    assert result["errors"][CONF_API_KEY] == "api_key_required"


@pytest.mark.asyncio
async def test_api_key_step_saves_key_and_loads_stops(monkeypatch):
    async def fake_load(self, provider):
        return [{"id": "1", "name": "Station"}]

    monkeypatch.setattr(config_flow, "_load_stops", fake_load)
    flow = _flow(PROVIDER_PLK, mock_steps=False)
    flow.async_step_stop = AsyncMock(return_value={"type": "stop"})

    result = await flow.async_step_api_key(
        {CONF_API_KEY: " secret ", CONF_PLK_TIER: "premium"}
    )

    assert result == {"type": "stop"}
    assert flow.hass.data[DOMAIN]["_global"][CONF_API_KEY] == "secret"
    assert flow.hass.data[DOMAIN]["_global"][CONF_PLK_TIER] == "premium"


@pytest.mark.asyncio
async def test_lodz_mode_form_and_group_branch(monkeypatch):
    flow = _flow(PROVIDER_LODZ, mock_steps=False)
    flow.async_step_lodz_group = AsyncMock(return_value={"type": "lodz_group"})

    form = await flow.async_step_lodz_mode()
    assert form["step_id"] == "lodz_mode"

    loaded = [{"id": "g1", "name": "Group", "stops": []}]
    flow._load_lodz_groups = AsyncMock(return_value=loaded)
    result = await flow.async_step_lodz_mode({"mode": "group"})

    assert result == {"type": "lodz_group"}
    assert flow._lodz_stops == loaded


@pytest.mark.asyncio
async def test_lodz_mode_single_loads_stops(monkeypatch):
    async def fake_load(self, provider):
        return [{"id": "1", "name": "Stop"}]

    monkeypatch.setattr(config_flow, "_load_stops", fake_load)
    flow = _flow(PROVIDER_LODZ, mock_steps=False)
    flow.async_step_stop = AsyncMock(return_value={"type": "stop"})

    result = await flow.async_step_lodz_mode({"mode": "single"})

    assert result == {"type": "stop"}
    assert flow._stops == [{"id": "1", "name": "Stop"}]


@pytest.mark.asyncio
async def test_lodz_group_creates_entry():
    flow = _flow(
        PROVIDER_LODZ,
        [
            {
                "id": "g1",
                "name": "Piotrkowska",
                "stops": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
            }
        ],
        mock_steps=False,
    )

    result = await flow.async_step_lodz_group({"group_id": "g1"})

    assert result["type"] == "create_entry"
    assert result["title"] == "Łódź: Piotrkowska (2 przyst.)"
    assert result["data"]["stops"] == [
        {"stop_id": "1", "name": "A"},
        {"stop_id": "2", "name": "B"},
    ]


@pytest.mark.asyncio
async def test_lodz_group_rejects_unknown_and_empty():
    flow = _flow(PROVIDER_LODZ, [{"id": "g1", "name": "A", "stops": []}], mock_steps=False)

    form = await flow.async_step_lodz_group({"group_id": "missing"})
    assert form["errors"]["group_id"] == "invalid_group"

    empty = _flow(PROVIDER_LODZ, [], mock_steps=False)
    assert await empty.async_step_lodz_group() == {
        "type": "abort",
        "reason": "lodz_groups_failed",
    }


@pytest.mark.asyncio
async def test_stop_step_exposes_offline_toggle():
    flow = _flow(mock_steps=False)
    flow._provider = PROVIDER_ZTM
    flow._stops = [{"id": "123", "name": "Test"}]

    result = await flow.async_step_stop()

    keys = {str(key) for key in result["data_schema"].schema}
    assert any("offline_only" in key for key in keys)


@pytest.mark.asyncio
async def test_stop_step_saves_offline_option_on_new_entry(monkeypatch):
    flow = _flow(mock_steps=False)
    flow._provider = PROVIDER_ZTM
    flow._stops = [{"id": "123", "name": "Test"}]
    monkeypatch.setattr(
        "mzkzg_transport.offline.async_has_snapshot", AsyncMock(return_value=True)
    )

    result = await flow.async_step_stop(
        {"stop_id": "123", "name": "Test", "offline_only": True}
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_OFFLINE_ONLY] is True
    assert result["data"]["stops"] == [{"stop_id": "123", "name": "Test"}]


@pytest.mark.asyncio
async def test_stop_step_rejects_offline_mode_without_snapshot(monkeypatch):
    flow = _flow(mock_steps=False)
    flow._provider = PROVIDER_ZTM
    flow._stops = [{"id": "123", "name": "Test"}]
    monkeypatch.setattr(
        "mzkzg_transport.offline.async_has_snapshot", AsyncMock(return_value=False)
    )

    result = await flow.async_step_stop(
        {"stop_id": "123", "name": "Test", "offline_only": True}
    )

    assert result["type"] == "form"
    assert result["errors"][CONF_OFFLINE_ONLY] == "offline_cache_missing"


class _GroupResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status = status

    async def text(self):
        return self._data


class _GroupGet:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _GroupSession:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, **kwargs):
        return _GroupGet(self.response)


@pytest.mark.asyncio
async def test_load_lodz_groups_parses_and_sorts(monkeypatch):
    import json

    payload = [
        ["2", "B", "", "", [["2", "B stop"], ["bad"]]],
        ["1", "a", "", "", [["1", "A stop"]]],
        ["bad"],
    ]
    monkeypatch.setattr(
        "aiohttp.ClientSession", lambda: _GroupSession(_GroupResponse(json.dumps(payload)))
    )
    flow = _flow(PROVIDER_LODZ)

    groups = await flow._load_lodz_groups()

    assert [group["name"] for group in groups] == ["a", "B"]
    assert groups[0]["stops"] == [{"id": "1", "name": "A stop"}]


@pytest.mark.asyncio
async def test_load_lodz_groups_returns_empty_on_bad_status_and_error(monkeypatch):
    monkeypatch.setattr(
        "aiohttp.ClientSession", lambda: _GroupSession(_GroupResponse("", status=503))
    )
    flow = _flow(PROVIDER_LODZ)
    assert await flow._load_lodz_groups() == []

    class BrokenSession(_GroupSession):
        def get(self, url, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr("aiohttp.ClientSession", lambda: BrokenSession(None))
    assert await flow._load_lodz_groups() == []
