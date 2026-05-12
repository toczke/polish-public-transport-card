"""Binary sensor platform for MZKZG Transport — delay alerts."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, CONF_PROVIDER, CONF_STOP_ID, DOMAIN

DELAY_THRESHOLD_SECONDS = 180  # 3 minutes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up delay binary sensor from a config entry."""
    coordinator = hass.data[DOMAIN]["_coordinators"][entry.entry_id]
    async_add_entities([MzkzgDelayBinarySensor(coordinator, entry)])


class MzkzgDelayBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that turns on when any departure is significantly delayed."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        provider_short = {"ztm_gdansk": "ztm", "zkm_gdynia": "zkm", "mzk_wejherowo": "mzk", "plk_rail": "plk"}
        prov = provider_short.get(entry.data[CONF_PROVIDER], "")
        stop = entry.data[CONF_STOP_ID]
        self._attr_unique_id = f"{DOMAIN}_{entry.data[CONF_PROVIDER]}_{stop}_delay"
        custom_name = entry.data.get(CONF_NAME, "")
        self._attr_name = f"{custom_name or f'{prov.upper()} {stop}'} Delay"
        self._attr_icon = "mdi:clock-alert"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.data[CONF_PROVIDER]}_{stop}")},
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
            {"route": d["route"], "headsign": d["headsign"], "delay_minutes": round(d["delay_seconds"] / 60)}
            for d in data.get("departures", [])
            if d.get("delay_seconds", 0) >= DELAY_THRESHOLD_SECONDS
        ]
        return {"delayed_departures": delayed, "threshold_minutes": DELAY_THRESHOLD_SECONDS // 60}
