"""MZKZG Transport integration for Home Assistant."""

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_NAME, CONF_PLK_TIER, CONF_PROVIDER, CONF_STOP_ID, CONF_STOPS, DOMAIN
from .coordinator import MzkzgTransportCoordinator

PLATFORMS = ["sensor", "binary_sensor"]
CARD_URL = "/mzkzg_transport/mzkzg-transport-card.js"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MZKZG Transport from a config entry."""
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
        coordinator = MzkzgTransportCoordinator(
            hass,
            stop_id,
            provider,
            name,
            entry.data.get(CONF_API_KEY, ""),
            entry.data.get(CONF_PLK_TIER, "basic"),
        )
        coordinator._options = dict(entry.options)
        await coordinator.async_config_entry_first_refresh()
        coordinators.append(coordinator)

    domain_data["_coordinators"][entry.entry_id] = coordinators

    # Update options on change
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    if not domain_data.get("_card_registered"):
        await _register_card(hass)
        domain_data["_card_registered"] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinators = hass.data[DOMAIN]["_coordinators"].get(entry.entry_id, [])
    for coordinator in coordinators:
        coordinator._options = dict(entry.options)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN]["_coordinators"].pop(entry.entry_id, None)
        # Clean up shared caches if no more entries
        if not hass.data[DOMAIN].get("_coordinators"):
            for key in ("_plk_cache", "_plk_lock", "_ztm_fleet", "_gtfsrt_cache",
                        "_gtfsrt_vehicles", "_krakow_meta", "_krakow_vehicles"):
                hass.data[DOMAIN].pop(key, None)
    return unload_ok


async def _register_card(hass: HomeAssistant) -> None:
    """Serve and register the Lovelace card JS."""
    www_path = str(Path(__file__).parent / "www")
    try:
        from homeassistant.components.http import StaticPathConfig
        if hasattr(hass.http, "async_register_static_paths"):
            await hass.http.async_register_static_paths([
                StaticPathConfig("/mzkzg_transport", www_path, False)
            ])
        else:
            hass.http.register_static_path("/mzkzg_transport", www_path, False)
    except (ImportError, AttributeError):
        hass.http.register_static_path("/mzkzg_transport", www_path, False)

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
                # Remove old versions and check for current
                existing = [
                    r for r in resources.async_items()
                    if "/mzkzg_transport/" in (r.get("url") or "")
                ]
                has_current = any(r.get("url") == CARD_URL for r in existing)
                # Remove stale versions
                for r in existing:
                    if r.get("url") != CARD_URL:
                        await resources.async_delete_item(r["id"])
                # Add current if missing
                if not has_current:
                    await resources.async_create_item({"res_type": "module", "url": CARD_URL})
    except (ImportError, AttributeError, TypeError, KeyError):
        pass
