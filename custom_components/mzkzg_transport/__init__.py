"""MZKZG Transport integration for Home Assistant."""

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

try:
    from homeassistant.components.frontend import add_extra_js_url
except ImportError:
    add_extra_js_url = None

from .const import CONF_API_KEY, CONF_NAME, CONF_PLK_TIER, CONF_PROVIDER, CONF_STOP_ID, DOMAIN
from .coordinator import MzkzgTransportCoordinator

PLATFORMS = ["sensor", "binary_sensor"]
CARD_URL = "/mzkzg_transport/mzkzg-transport-card.js"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MZKZG Transport from a config entry."""
    hass.data.setdefault(DOMAIN, {"_global": {}, "_coordinators": {}})

    if entry.data.get(CONF_API_KEY):
        hass.data[DOMAIN]["_global"][CONF_API_KEY] = entry.data[CONF_API_KEY]

    # Shared coordinator — one per entry, used by sensor + binary_sensor
    coordinator = MzkzgTransportCoordinator(
        hass,
        entry.data[CONF_STOP_ID],
        entry.data[CONF_PROVIDER],
        entry.data.get(CONF_NAME, ""),
        entry.data.get(CONF_API_KEY, ""),
        entry.data.get(CONF_PLK_TIER, "basic"),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN]["_coordinators"][entry.entry_id] = coordinator

    if not hass.data[DOMAIN].get("_card_registered"):
        await _register_card(hass)
        hass.data[DOMAIN]["_card_registered"] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN]["_coordinators"].pop(entry.entry_id, None)
    return unload_ok


async def _register_card(hass: HomeAssistant) -> None:
    """Serve and register the Lovelace card JS."""
    www_path = str(Path(__file__).parent / "www")
    try:
        from homeassistant.components.http import StaticPathConfig
        if hasattr(hass.http, "async_register_static_paths"):
            await hass.http.async_register_static_paths([
                StaticPathConfig("/mzkzg_transport", www_path, True)
            ])
        else:
            hass.http.register_static_path("/mzkzg_transport", www_path, True)
    except (ImportError, AttributeError):
        hass.http.register_static_path("/mzkzg_transport", www_path, True)

    if add_extra_js_url:
        add_extra_js_url(hass, CARD_URL)
