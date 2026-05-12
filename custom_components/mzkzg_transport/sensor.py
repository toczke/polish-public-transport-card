"""Sensor platform for MZKZG Transport."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, CONF_PROVIDER, CONF_STOP_ID, DOMAIN
from .coordinator import MzkzgTransportCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MZKZG Transport sensor from a config entry."""
    coordinator = hass.data[DOMAIN]["_coordinators"][entry.entry_id]
    async_add_entities([MzkzgTransportSensor(coordinator, entry)])


class MzkzgTransportSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing departures from a single stop."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MzkzgTransportCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        provider_short = {"ztm_gdansk": "ztm", "zkm_gdynia": "zkm", "mzk_wejherowo": "mzk", "plk_rail": "plk"}
        prov = provider_short.get(entry.data[CONF_PROVIDER], entry.data[CONF_PROVIDER])
        stop = entry.data[CONF_STOP_ID]
        self._attr_unique_id = f"{DOMAIN}_{entry.data[CONF_PROVIDER]}_{stop}"
        self.entity_id = f"sensor.mzkzg_{prov}_{stop}"
        custom_name = entry.data.get(CONF_NAME, "")
        self._attr_name = custom_name or f"MZKZG {prov.upper()} {stop}"
        self._attr_icon = "mdi:bus-multiple"

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
