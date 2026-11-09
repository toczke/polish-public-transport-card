"""Polish Transport integration for Home Assistant."""

import hashlib
import json
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_NAME, CONF_PLK_TIER, CONF_PROVIDER, CONF_STOP_ID, CONF_STOPS, CONFIG_ENTRY_VERSION, DEVICE_MANUFACTURER, DOMAIN
from .coordinator import PolishTransportCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]
_MANIFEST = json.loads((Path(__file__).parent / "manifest.json").read_text())
CARD_VERSION = _MANIFEST["version"]


def _card_build_hash() -> str:
    """Return a short content hash of the served card bundle."""
    try:
        data = (Path(__file__).parent / "www" / "polish-transport-card.js").read_bytes()
    except OSError:
        return ""
    return hashlib.sha1(data).hexdigest()[:10]


_CARD_BUILD = _card_build_hash()
CARD_URL = f"/polish_transport/polish-transport-card.js?v={CARD_VERSION}"
if _CARD_BUILD:
    CARD_URL = f"{CARD_URL}-{_CARD_BUILD}"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Run domain-wide 2.0 migration before config entries are set up."""
    hass.data.setdefault(DOMAIN, {})
    from .migration import (
        async_heal_entity_ids,
        async_migrate_entries,
        async_normalize_hub_entity_ids,
    )

    await async_migrate_entries(hass)
    await async_heal_entity_ids(hass)
    await async_normalize_hub_entity_ids(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a legacy entry to the 2.0 hub format."""
    if entry.version >= CONFIG_ENTRY_VERSION:
        return True
    from .migration import (
        async_heal_entity_ids,
        async_migrate_entries,
        async_normalize_hub_entity_ids,
    )

    await async_migrate_entries(hass)
    await async_heal_entity_ids(hass)
    await async_normalize_hub_entity_ids(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Polish Transport from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    domain_data = hass.data[DOMAIN]
    domain_data.setdefault("_global", {})
    domain_data.setdefault("_coordinators", {})

    if entry.data.get(CONF_API_KEY):
        domain_data["_global"][CONF_API_KEY] = entry.data[CONF_API_KEY]

    provider = entry.data[CONF_PROVIDER]
    
    # Support both old (single stop) and new (multi-stop) format
    stops = entry.data.get(CONF_STOPS)
    if stops is None:
        # Legacy single-stop entry
        stops = [{"stop_id": entry.data[CONF_STOP_ID], "name": entry.data.get(CONF_NAME, "")}]

    # Create one coordinator per stop
    coordinators = []
    for stop_cfg in stops:
        stop_id = stop_cfg["stop_id"]
        name = stop_cfg.get("name", "")
        coordinator = PolishTransportCoordinator(
            hass,
            stop_id,
            provider,
            name,
            entry.data.get(CONF_API_KEY, ""),
            entry.data.get(CONF_PLK_TIER, "basic"),
        )
        coordinator._options = {**entry.data, **entry.options}
        coordinator.config_entry = entry
        try:
            await coordinator.async_config_entry_first_refresh()
        except Exception:
            _LOGGER.warning("First refresh failed for %s/%s", provider, stop_id, exc_info=True)
        coordinators.append(coordinator)

    domain_data["_coordinators"][entry.entry_id] = coordinators

    # Register the parent operator device once here, so every platform can link its
    # stop devices to it regardless of platform setup order.
    from homeassistant.helpers import device_registry as dr

    from .const import PROVIDER_LABELS

    provider_label = PROVIDER_LABELS.get(provider, provider)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, provider)},
        name=provider_label,
        manufacturer=DEVICE_MANUFACTURER,
        model=provider,
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    # Update options on change
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    if not domain_data.get("_card_registered"):
        await _register_card(hass)
        domain_data["_card_registered"] = True

    if not hass.services.has_service(DOMAIN, "refresh_gtfs"):
        async def handle_refresh_gtfs(call):
            provider = call.data.get("provider")
            gtfs_cache = hass.data[DOMAIN].get("_gtfsrt_cache", {})
            if provider:
                keys_to_remove = [k for k in gtfs_cache if k.startswith(provider)]
                for k in keys_to_remove:
                    gtfs_cache.pop(k, None)
            else:
                gtfs_cache.clear()
            _LOGGER.info("GTFS cache cleared%s", f" for {provider}" if provider else "")
        
        hass.services.async_register(DOMAIN, "refresh_gtfs", handle_refresh_gtfs)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinators = hass.data[DOMAIN]["_coordinators"].get(entry.entry_id, [])
    for coordinator in coordinators:
        coordinator._options = {**entry.data, **entry.options}


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN]["_coordinators"].pop(entry.entry_id, None)
        # A PLK entry owns the shared usage sensor while it is loaded. Drop the
        # guard so a reload of the owning entry recreates the sensor (unloading
        # a different PLK entry must not create a duplicate).
        marker = "_plk_usage_sensor_plk_rail"
        if (
            entry.data.get(CONF_PROVIDER) == "plk_rail"
            and hass.data[DOMAIN].get(marker) == entry.entry_id
        ):
            hass.data[DOMAIN].pop(marker, None)
        # Clean up shared caches if no more entries
        if not hass.data[DOMAIN].get("_coordinators"):
            for key in ("_plk_cache", "_plk_lock", "_ztm_fleet", "_ztm_gtfs_cache",
                        "_ztm_gps", "_ztm_alerts", "_ztm_alerts_lock",
                        "_gtfsrt_cache", "_gtfsrt_locks", "_gtfsrt_vehicles",
                        "_gtfsrt_positions", "_gtfsrt_alerts", "_gtfsrt_alert_locks",
                        "_lodz_gtfs_data", "_krakow_meta",
                        "_krakow_vehicles"):
                hass.data[DOMAIN].pop(key, None)
            # Shared entity guards must be dropped with the entries that own them,
            # otherwise a re-added provider would never recreate those entities.
            for key in list(hass.data[DOMAIN]):
                if key.startswith("_health_") or key.startswith("_plk_usage_sensor_"):
                    hass.data[DOMAIN].pop(key, None)
    return unload_ok


async def _register_card(hass: HomeAssistant) -> None:
    """Serve and register the Lovelace card JS."""
    www_path = str(Path(__file__).parent / "www")
    static_paths = [
        ("/polish_transport", www_path),
    ]
    try:
        from homeassistant.components.http import StaticPathConfig
        if hasattr(hass.http, "async_register_static_paths"):
            await hass.http.async_register_static_paths([
                StaticPathConfig(url, path, False) for url, path in static_paths
            ])
        else:
            for url, path in static_paths:
                hass.http.register_static_path(url, path, False)
    except (ImportError, AttributeError):
        for url, path in static_paths:
            hass.http.register_static_path(url, path, False)

    # Register as module resource so card appears in picker automatically
    try:
        from homeassistant.components.lovelace.resources import (
            ResourceStorageCollection,
        )
        from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN

        lovelace = hass.data.get(LOVELACE_DOMAIN)
        if lovelace and hasattr(lovelace, "resources"):
            resources = lovelace.resources
            if hasattr(resources, "async_items") and isinstance(resources, ResourceStorageCollection):
                existing = [
                    r for r in resources.async_items()
                    if f"/{DOMAIN}/" in (r.get("url") or "") or "/polish_transport/" in (r.get("url") or "")
                ]
                # Create the current entry first — deleting first would leave the
                # dashboard with no card resource at all if creation then fails.
                if not any(r.get("url") == CARD_URL for r in existing):
                    await resources.async_create_item({"res_type": "module", "url": CARD_URL})
                for r in existing:
                    if r.get("url") != CARD_URL:
                        await resources.async_delete_item(r["id"])
            else:
                _LOGGER.warning(
                    "Lovelace is in YAML mode; add %s manually as a JavaScript module resource",
                    CARD_URL,
                )
        else:
            _LOGGER.warning(
                "Lovelace resources unavailable; add %s manually as a JavaScript module resource",
                CARD_URL,
            )
    except (ImportError, AttributeError, TypeError, KeyError) as err:
        _LOGGER.warning("Failed to register Lovelace card resource: %s", err)
