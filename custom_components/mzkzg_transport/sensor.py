"""Sensor platform for MZKZG Transport."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, CONF_PROVIDER, CONF_STOP_ID, DOMAIN, PROVIDER_LABELS
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
        provider = entry.data[CONF_PROVIDER]
        provider_label = PROVIDER_LABELS.get(provider, provider)
        stop = entry.data[CONF_STOP_ID]
        self._attr_unique_id = f"{DOMAIN}_{provider}_{stop}"
        custom_name = entry.data.get(CONF_NAME, "")
        self._attr_name = "Odjazdy"
        self._attr_icon = "mdi:bus-multiple"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{provider}_{stop}")},
            "name": custom_name or f"{provider_label} {stop}",
            "manufacturer": "MZKZG Transport",
            "model": provider,
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


class MzkzgPlkApiUsageSensor(SensorEntity, RestoreEntity):
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

    async def async_added_to_hass(self) -> None:
        """Restore persisted usage counters after HA restart."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if not last_state:
            return

        domain_data = self._hass.data.setdefault(DOMAIN, {})
        cache = domain_data.setdefault("_plk_cache", {})

        if "_req_count" not in cache:
            try:
                cache["_req_count"] = int(last_state.state)
            except (TypeError, ValueError):
                cache["_req_count"] = 0

        attrs = last_state.attributes or {}
        if "_429_count" not in cache:
            try:
                cache["_429_count"] = int(attrs.get("rate_limit_hits", 0))
            except (TypeError, ValueError):
                cache["_429_count"] = 0

        if "_ts" not in cache and attrs.get("last_success") is not None:
            cache["_ts"] = attrs.get("last_success")

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
