"""Lovelace card resource registration."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.lovelace.resources import ResourceStorageCollection

import mzkzg_transport
from mzkzg_transport import CARD_URL, _register_card

OLD_URL = "/polish_transport/polish-transport-card.js?v=2.0.3-abc"


class FakeResources(ResourceStorageCollection):
    """Loads lazily like Home Assistant's: async_items() is empty before a load."""

    def __init__(self, stored):
        self._stored = stored
        self.data = {}
        self.loaded = False
        self.created = []
        self.deleted = []

    async def async_get_info(self):
        if not self.loaded:
            self.data = {r["id"]: r for r in self._stored}
            self.loaded = True
        return {"resources": len(self.data)}

    def async_items(self):
        return list(self.data.values())

    async def async_create_item(self, data):
        await self.async_get_info()
        item = {"id": f"new{len(self.created)}", "type": data["res_type"], "url": data["url"]}
        self.data[item["id"]] = item
        self.created.append(item)
        return item

    async def async_delete_item(self, item_id):
        await self.async_get_info()
        del self.data[item_id]
        self.deleted.append(item_id)


def _hass(resources):
    hass = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    hass.data = {"lovelace": SimpleNamespace(resources=resources)}
    return hass


def _urls(resources):
    return sorted(r["url"] for r in resources.async_items())


@pytest.mark.common
async def test_stored_card_not_added_again_before_load():
    resources = FakeResources([{"id": "a", "type": "module", "url": CARD_URL}])
    await _register_card(_hass(resources))
    assert resources.created == []
    assert _urls(resources) == [CARD_URL]


@pytest.mark.common
async def test_duplicates_and_old_versions_removed():
    resources = FakeResources([
        {"id": "a", "type": "module", "url": CARD_URL},
        {"id": "b", "type": "module", "url": CARD_URL},
        {"id": "c", "type": "module", "url": OLD_URL},
        {"id": "d", "type": "module", "url": "/local/other-card.js"},
    ])
    await _register_card(_hass(resources))
    assert resources.created == []
    assert sorted(resources.deleted) == ["b", "c"]
    assert _urls(resources) == sorted([CARD_URL, "/local/other-card.js"])


@pytest.mark.common
async def test_card_added_when_missing():
    resources = FakeResources([{"id": "c", "type": "module", "url": OLD_URL}])
    await _register_card(_hass(resources))
    assert [r["url"] for r in resources.created] == [CARD_URL]
    assert resources.deleted == ["c"]
    assert _urls(resources) == [CARD_URL]


def test_card_url_is_versioned():
    assert CARD_URL.startswith(f"/polish_transport/polish-transport-card.js?v={mzkzg_transport.CARD_VERSION}")
