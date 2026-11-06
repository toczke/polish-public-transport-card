"""Binary sensor platform for MZKZG Transport."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PROVIDER, DOMAIN, PROVIDER_PLK
from .device_utils import async_link_device_to_parent


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MZKZG Transport binary sensors from a config entry."""
    coordinators = hass.data[DOMAIN]["_coordinators"][entry.entry_id]
    provider = entry.data[CONF_PROVIDER]

    entities = []

    # Delay alerts are train-specific (PLK provides reliable delays for every
    # departure); other providers already expose the delay on the sensor rows.
    if provider == PROVIDER_PLK:
        for coordinator in coordinators:
            entities.append(MzkzgPlkDelayBinarySensor(coordinator, entry))

    async_add_entities(entities)


class MzkzgPlkDelayBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that turns on if any train is delayed."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:train-alert"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        provider = coordinator.provider
        stop = coordinator.stop_id

        self._attr_unique_id = f"{DOMAIN}_{provider}_{stop}_delay"
        self._attr_name = "Opóźnienia Pociągów"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{provider}_{stop}")},
        }

    async def async_added_to_hass(self) -> None:
        """Link this stop device to its operator device."""
        await super().async_added_to_hass()
        async_link_device_to_parent(
            self.hass,
            {(DOMAIN, f"{self.coordinator.provider}_{self.coordinator.stop_id}")},
            {(DOMAIN, self.coordinator.provider)},
        )

    @property
    def is_on(self) -> bool:
        """Return True if there is at least one train delayed by 5+ minutes."""
        data = self.coordinator.data
        if not data or not data.get("departures"):
            return False

        for dep in data["departures"]:
            if dep.get("delay_seconds", 0) >= 300:
                return True

        return False

    @property
    def extra_state_attributes(self) -> dict:
        """Return details about delayed trains."""
        data = self.coordinator.data
        if not data or not data.get("departures"):
            return {}

        delayed = []
        for dep in data["departures"]:
            delay_sec = dep.get("delay_seconds", 0)
            if delay_sec >= 300:
                delayed.append(
                    {
                        "route": dep.get("route", ""),
                        "headsign": dep.get("headsign", ""),
                        "delay_minutes": delay_sec // 60,
                        "estimated_time": dep.get("estimated_time", ""),
                    }
                )

        return {
            "delayed_trains_count": len(delayed),
            "delayed_trains": delayed,
        }
