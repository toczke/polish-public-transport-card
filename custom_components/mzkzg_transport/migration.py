"""2.0 config-entry and entity migration.

The integration keeps the legacy technical domain ``mzkzg_transport`` so Home
Assistant can load existing config entries and migrate them in place. All user
visible and entity identifiers use the ``polish_transport`` prefix.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from collections import defaultdict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_API_KEY,
    CONF_NAME,
    CONF_PLK_TIER,
    CONF_PROVIDER,
    CONF_STOP_ID,
    CONF_STOPS,
    CONFIG_ENTRY_VERSION,
    DEVICE_MANUFACTURER,
    DOMAIN,
    ENTITY_UNIQUE_PREFIX,
    PROVIDER_LABELS,
)

_LOGGER = logging.getLogger(__name__)


def slugify(value: object) -> str:
    """Create a stable Home Assistant object-id fragment."""
    text = str(value or "").replace("ł", "l").replace("Ł", "L")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "odjazdy"


def entry_stops(entry: ConfigEntry) -> list[dict]:
    """Return a normalized stop list for legacy and multi-stop entries."""
    raw = entry.data.get(CONF_STOPS)
    if raw:
        stops = []
        for item in raw:
            stop_id = str(item.get("stop_id") or item.get("id") or "").strip()
            if stop_id:
                stops.append({"stop_id": stop_id, "name": str(item.get("name") or "")})
        return stops
    stop_id = str(entry.data.get(CONF_STOP_ID) or "").strip()
    if stop_id:
        return [{"stop_id": stop_id, "name": str(entry.data.get(CONF_NAME) or "")}]
    return []


def _merge_options(entries: list[ConfigEntry]) -> dict:
    merged: dict = {}
    for entry in entries:
        for key, value in entry.options.items():
            merged.setdefault(key, value)
    return merged


def _unique_entity_id(registry: er.EntityRegistry, domain: str, wanted: str, current: str) -> str:
    candidate = f"{domain}.{wanted}"
    existing = registry.async_get(candidate)
    if existing is None or existing.entity_id == current:
        return candidate
    suffix = 2
    while registry.async_get(f"{candidate}_{suffix}") is not None:
        suffix += 1
    return f"{candidate}_{suffix}"


async def _migrate_group(
    hass: HomeAssistant,
    provider: str,
    group: list[ConfigEntry],
) -> None:
    """Merge every entry of one provider into a single hub entry."""
    hub = group[0]
    stops: list[dict] = []
    seen: set[str] = set()
    for entry in group:
        for stop in entry_stops(entry):
            if stop["stop_id"] in seen:
                continue
            seen.add(stop["stop_id"])
            stops.append(stop)

    if not stops:
        _LOGGER.warning("2.0 migration: %s has no stops; skipping", provider)
        return

    provider_label = PROVIDER_LABELS.get(provider, provider)
    data = dict(hub.data)
    data.pop(CONF_STOP_ID, None)
    data[CONF_PROVIDER] = provider
    data[CONF_STOPS] = stops
    data[CONF_NAME] = provider_label
    for entry in group:
        if not data.get(CONF_API_KEY) and entry.data.get(CONF_API_KEY):
            data[CONF_API_KEY] = entry.data[CONF_API_KEY]
        if not data.get(CONF_PLK_TIER) and entry.data.get(CONF_PLK_TIER):
            data[CONF_PLK_TIER] = entry.data[CONF_PLK_TIER]

    await hass.config_entries.async_update_entry(
        hub,
        data=data,
        options=_merge_options(group),
        title=provider_label,
        unique_id=f"{ENTITY_UNIQUE_PREFIX}_{provider}",
        version=CONFIG_ENTRY_VERSION,
    )

    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)

    hub_device = dev_reg.async_get_or_create(
        config_entry_id=hub.entry_id,
        identifiers={(DOMAIN, provider)},
        name=provider_label,
        manufacturer=DEVICE_MANUFACTURER,
        model=provider,
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    stop_devices: dict[str, str] = {}
    stop_names = {stop["stop_id"]: stop["name"] for stop in stops}
    for stop in stops:
        stop_id = stop["stop_id"]
        device = dev_reg.async_get_or_create(
            config_entry_id=hub.entry_id,
            identifiers={(DOMAIN, f"{provider}_{stop_id}")},
            name=stop["name"] or stop_id,
            manufacturer=DEVICE_MANUFACTURER,
            model=provider,
            via_device_id=hub_device.id,
        )
        if device:
            stop_devices[stop_id] = device.id

    for entry in group:
        for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            unique_id = entity.unique_id or ""
            new_unique = None
            new_entity = None
            device_id = hub_device.id

            if unique_id == f"{DOMAIN}_plk_api_usage":
                new_unique = f"{ENTITY_UNIQUE_PREFIX}_plk_api_usage"
                new_entity = _unique_entity_id(ent_reg, "sensor", "plk_api_usage", entity.entity_id)
            elif "_multi_" in unique_id:
                new_unique = f"{ENTITY_UNIQUE_PREFIX}_{provider}_hub"
                new_entity = _unique_entity_id(
                    ent_reg, "sensor", f"{slugify(provider_label)}_odjazdy", entity.entity_id
                )
            elif unique_id.startswith(f"{DOMAIN}_{provider}_") and unique_id.endswith("_delay"):
                stop_id = unique_id[len(f"{DOMAIN}_{provider}_") : -len("_delay")]
                new_unique = f"{ENTITY_UNIQUE_PREFIX}_{provider}_{stop_id}_delay"
                new_entity = _unique_entity_id(
                    ent_reg,
                    "binary_sensor",
                    f"{slugify(stop_names.get(stop_id, stop_id))}_opoznienie",
                    entity.entity_id,
                )
                device_id = stop_devices.get(stop_id, hub_device.id)
            elif unique_id.startswith(f"{DOMAIN}_{provider}_"):
                stop_id = unique_id[len(f"{DOMAIN}_{provider}_") :]
                new_unique = f"{ENTITY_UNIQUE_PREFIX}_{provider}_{stop_id}"
                new_entity = _unique_entity_id(
                    ent_reg,
                    "sensor",
                    f"{slugify(stop_names.get(stop_id, stop_id))}_odjazdy",
                    entity.entity_id,
                )
                device_id = stop_devices.get(stop_id, hub_device.id)
            elif unique_id.endswith("_health") or unique_id.endswith("_delay"):
                # Old health sensors and non-PLK delay sensors were removed in 1.7.
                ent_reg.async_remove(entity.entity_id)
                continue

            if not new_unique or not new_entity:
                continue

            try:
                ent_reg.async_update_entity(
                    entity.entity_id,
                    new_unique_id=new_unique,
                    new_entity_id=new_entity,
                    config_entry_id=hub.entry_id,
                    device_id=device_id,
                )
            except Exception as err:  # noqa: BLE001 - migration must not abort setup
                _LOGGER.warning(
                    "2.0 migration: could not migrate entity %s (%s): %s",
                    entity.entity_id,
                    unique_id,
                    err,
                )

    for entry in group:
        if entry.entry_id != hub.entry_id:
            try:
                await hass.config_entries.async_remove(entry.entry_id)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("2.0 migration: could not remove %s: %s", entry.title, err)


async def async_migrate_entries(hass: HomeAssistant) -> None:
    """Consolidate legacy single-stop entries into one hub per provider."""
    lock = hass.data.setdefault(DOMAIN, {}).setdefault("_migration_lock", asyncio.Lock())
    async with lock:
        if hass.data[DOMAIN].get("_migrated_2_0"):
            return
        entries = list(hass.config_entries.async_entries(DOMAIN))
        legacy_entries = [entry for entry in entries if entry.version < CONFIG_ENTRY_VERSION]
        if not legacy_entries:
            hass.data[DOMAIN]["_migrated_2_0"] = True
            return

        groups: dict[str, list[ConfigEntry]] = defaultdict(list)
        for entry in entries:
            provider = entry.data.get(CONF_PROVIDER)
            if provider:
                groups[provider].append(entry)

        for provider, group in groups.items():
            if not any(entry.version < CONFIG_ENTRY_VERSION for entry in group):
                continue
            _LOGGER.info(
                "2.0 migration: merging %d entry/entries for %s into one hub",
                len(group),
                PROVIDER_LABELS.get(provider, provider),
            )
            try:
                await _migrate_group(hass, provider, group)
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("2.0 migration failed for %s: %s", provider, err)

        hass.data[DOMAIN]["_migrated_2_0"] = True
