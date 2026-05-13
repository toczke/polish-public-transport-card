"""Sensor platform for MZKZG Transport."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, CONF_PROVIDER, CONF_STOP_ID, DOMAIN, PROVIDER_SHORT_NAMES
from .coordinator import MzkzgTransportCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MZKZG Transport sensor from a config entry."""
    coordinator = hass.data[DOMAIN]["_coordinators"][entry.entry_id]
    entities = [MzkzgTransportSensor(coordinator, entry)]

    # Add API usage sensor for PLK (one per PLK entry)
    if entry.data.get(CONF_PROVIDER) == "plk_rail":
        entities.append(MzkzgPlkApiUsageSensor(hass, entry))

    async_add_entities(entities)


class MzkzgTransportSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing departures from a single stop."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MzkzgTransportCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        prov = PROVIDER_SHORT_NAMES.get(entry.data[CONF_PROVIDER], entry.data[CONF_PROVIDER])
        stop = entry.data[CONF_STOP_ID]
        self._attr_unique_id = f"{DOMAIN}_{entry.data[CONF_PROVIDER]}_{stop}"
        custom_name = entry.data.get(CONF_NAME, "")
        self._attr_name = custom_name or f"MZKZG {prov.upper()} {stop}"
        self._attr_icon = "mdi:bus-multiple"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.data[CONF_PROVIDER]}_{stop}")},
            "name": custom_name or f"{prov.upper()} {stop}",
            "manufacturer": "MZKZG Transport",
            "model": entry.data[CONF_PROVIDER],
            "entry_type": "service",
        }

    @property
    def native_value(self) -> str | None:
        """Return the next departure time as state."""
        data = self.coordinator.data
        if not data or not data.get("departures"):
            return None
        return data["departures"][0].get("estimated_time")

    @property
    def extra_state_attributes(self) -> dict:
        """Return departure list and metadata as attributes."""
        data = self.coordinator.data
        if not data:
            return {}
        return {
            "stop_id": data.get("stop_id"),
            "stop_name": data.get("stop_name"),
            "provider": data.get("provider"),
            "last_update": data.get("last_update"),
            "departures": data.get("departures", []),
        }


class MzkzgPlkApiUsageSensor(SensorEntity):
    """Sensor tracking PLK API usage."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:api"
    _attr_native_unit_of_measurement = "requests"
    _attr_state_class = "total_increasing"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self._hass = hass
        self._attr_unique_id = f"{DOMAIN}_plk_api_usage"
        self._attr_name = "PLK API Usage"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.data[CONF_PROVIDER]}_{entry.data[CONF_STOP_ID]}")},
        }

    @property
    def native_value(self) -> int:
        """Return total requests made."""
        cache = self._hass.data.get(DOMAIN, {}).get("_plk_cache", {})
        return cache.get("_req_count", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return API usage details."""
        cache = self._hass.data.get(DOMAIN, {}).get("_plk_cache", {})
        return {
            "requests_total": cache.get("_req_count", 0),
            "rate_limit_hits": cache.get("_429_count", 0),
            "last_success": cache.get("_ts", None),
        }
