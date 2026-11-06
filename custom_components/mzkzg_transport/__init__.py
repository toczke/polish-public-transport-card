"""MZKZG Transport integration for Home Assistant."""

import json
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_NAME, CONF_PLK_TIER, CONF_PROVIDER, CONF_STOP_ID, CONF_STOPS, DOMAIN
from .coordinator import MzkzgTransportCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]
_MANIFEST = json.loads((Path(__file__).parent / "manifest.json").read_text())
CARD_VERSION = _MANIFEST["version"]
CARD_URL = f"/polish_transport/polish-transport-card.js?v={CARD_VERSION}"


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
        manufacturer="MZKZG Transport",
        model=provider,
        entry_type=dr.DeviceEntryType.SERVICE,
    )

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
                        "_ztm_gps", "_gtfsrt_cache", "_gtfsrt_locks", "_gtfsrt_vehicles",
                        "_gtfsrt_positions", "_lodz_gtfs_data", "_krakow_meta",
                        "_krakow_vehicles"):
                hass.data[DOMAIN].pop(key, None)
            # Shared entity guards must be dropped with the entries that own them,
            # otherwise a re-added provider would never recreate those entities.
            for key in list(hass.data[DOMAIN]):
                if key.startswith("_health_") or key.startswith("_plk_usage_sensor_"):
                    hass.data[DOMAIN].pop(key, None)
    return unload_ok


async def _register_card(hass: HomeAssistant) -> None:
    """Serve and register the Lovelace card JS (supports both polish-transport-card and legacy mzkzg-transport-card)."""
    www_path = str(Path(__file__).parent / "www")
    static_paths = [
        ("/polish_transport", www_path),
        ("/mzkzg_transport", www_path),
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
                    if "/mzkzg_transport/" in (r.get("url") or "") or "/polish_transport/" in (r.get("url") or "")
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
