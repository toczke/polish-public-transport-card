"""Binary sensor platform for MZKZG Transport — delay alerts."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROVIDER_LABELS

DELAY_THRESHOLD_SECONDS = 180  # 3 minutes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up delay binary sensor from a config entry."""
    coordinators = hass.data[DOMAIN]["_coordinators"][entry.entry_id]
    provider = entry.data.get("provider", "")
    
    entities = [MzkzgDelayBinarySensor(coordinator, entry) for coordinator in coordinators]
    
    # Add health sensor once per provider (skip if another entry already created it)
    health_key = f"_health_{provider}"
    if not hass.data[DOMAIN].get(health_key):
        hass.data[DOMAIN][health_key] = True
        entities.append(MzkzgHealthBinarySensor(coordinators, entry))
    
    async_add_entities(entities)


class MzkzgDelayBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that turns on when any departure is significantly delayed."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        provider = coordinator.provider
        provider_label = PROVIDER_LABELS.get(provider, provider)
        stop = coordinator.stop_id
        stop_label = coordinator.stop_name or stop
        self._attr_unique_id = f"{DOMAIN}_{provider}_{stop}_delay"
        self._attr_name = "Opóźnienie"
        self._attr_icon = "mdi:clock-alert"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{provider}_{stop}")},
            "name": stop_label,
            "manufacturer": provider_label,
            "model": provider,
            "via_device": (DOMAIN, provider),
        }

    @property
    def is_on(self) -> bool | None:
        """Return True if any departure has delay >= threshold."""
        data = self.coordinator.data
        if not data or not data.get("departures"):
            return False
        return any(
            d.get("delay_seconds", 0) >= DELAY_THRESHOLD_SECONDS
            for d in data["departures"]
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return delayed departures details."""
        data = self.coordinator.data
        if not data:
            return {}
        delayed = [
            {"route": d.get("route", "?"), "headsign": d.get("headsign", "—"), "delay_minutes": round(d.get("delay_seconds", 0) / 60)}
            for d in data.get("departures", [])
            if d.get("delay_seconds", 0) >= DELAY_THRESHOLD_SECONDS
        ]
        return {"delayed_departures": delayed, "threshold_minutes": DELAY_THRESHOLD_SECONDS // 60}


class MzkzgHealthBinarySensor(BinarySensorEntity):
    """Binary sensor showing provider API health (on = healthy)."""

    _attr_has_entity_name = True

    def __init__(self, coordinators: list, entry: ConfigEntry) -> None:
        """Initialize."""
        provider = entry.data.get("provider", "")
        provider_label = PROVIDER_LABELS.get(provider, provider)
        self._coordinators = coordinators
        self._attr_unique_id = f"{DOMAIN}_{provider}_health"
        self._attr_name = "API Health"
        self._attr_icon = "mdi:heart-pulse"
        self._attr_device_class = "connectivity"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, provider)},
            "name": provider_label,
        }

    @property
    def is_on(self) -> bool | None:
        """Return True if at least one coordinator fetched successfully."""
        if not self._coordinators:
            return None
        return any(c.last_update_success for c in self._coordinators)

    @property
    def available(self) -> bool:
        """Always available so we can show offline state."""
        return True

    @property
    def extra_state_attributes(self) -> dict:
        """Return health details."""
        total = len(self._coordinators)
        healthy = sum(1 for c in self._coordinators if c.last_update_success)
        last_err = None
        for c in self._coordinators:
            if c.last_exception:
                last_err = str(c.last_exception)
                break
        attrs = {
            "healthy_stops": healthy,
            "total_stops": total,
        }
        if last_err:
            attrs["last_error"] = last_err
        return attrs

    async def async_added_to_hass(self) -> None:
        """Register coordinator listeners."""
        for c in self._coordinators:
            self.async_on_remove(c.async_add_listener(self.async_write_ha_state))
