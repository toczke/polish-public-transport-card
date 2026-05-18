"""Sensor platform for MZKZG Transport."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PROVIDER, DOMAIN, PROVIDER_LABELS
from .coordinator import MzkzgTransportCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MZKZG Transport sensor from a config entry."""
    from homeassistant.helpers import device_registry as dr

    coordinators = hass.data[DOMAIN]["_coordinators"][entry.entry_id]
    provider = entry.data[CONF_PROVIDER]
    provider_label = PROVIDER_LABELS.get(provider, provider)

    # Register parent operator device
    dev_reg = dr.async_get(hass)
    dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, provider)},
        name=provider_label,
        manufacturer="MZKZG Transport",
        model=provider,
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    entities = []
    for coordinator in coordinators:
        entities.append(MzkzgTransportSensor(coordinator, entry))

    # Add API usage sensor for PLK (once per entry)
    if entry.data.get(CONF_PROVIDER) == "plk_rail":
        entities.append(MzkzgPlkApiUsageSensor(hass, entry))

    async_add_entities(entities)


class MzkzgTransportSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing departures from a single stop."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MzkzgTransportCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        provider = coordinator.provider
        provider_label = PROVIDER_LABELS.get(provider, provider)
        stop = coordinator.stop_id
        custom_name = coordinator.stop_name
        stop_label = custom_name or stop
        self._attr_unique_id = f"{DOMAIN}_{provider}_{stop}"
        self._attr_name = "Odjazdy"
        self._attr_icon = "mdi:bus-multiple"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{provider}_{stop}")},
            "name": stop_label,
            "manufacturer": provider_label,
            "model": provider,
            "via_device": (DOMAIN, provider),
        }

    @property
    def native_value(self) -> str | None:
        """Return the next departure time as state."""
        data = self.coordinator.data
        if not data:
            return None
        if not data.get("departures"):
            return "brak"
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
            "identifiers": {(DOMAIN, entry.data[CONF_PROVIDER])},
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
