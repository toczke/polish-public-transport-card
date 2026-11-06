"""Sensor platform for MZKZG Transport."""


from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PROVIDER, CONF_STOPS, DOMAIN, MAX_DEPARTURES, PROVIDER_LABELS, PROVIDER_PLK
from .coordinator import MzkzgTransportCoordinator
from .device_utils import async_link_device_to_parent


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MZKZG Transport sensor from a config entry."""
    coordinators = hass.data[DOMAIN]["_coordinators"][entry.entry_id]
    provider = entry.data[CONF_PROVIDER]

    entities = []
    is_multi = bool(entry.data.get(CONF_STOPS)) and len(coordinators) > 1
    if is_multi:
        # Single aggregated sensor for multi-stop entries
        entities.append(MzkzgAggregatedSensor(coordinators, entry))
    else:
        for coordinator in coordinators:
            entities.append(MzkzgTransportSensor(coordinator, entry))

    # Add the shared PLK API usage sensor once per Home Assistant instance. The usage
    # counters are global, so a sensor per PLK entry would only duplicate the same
    # unique id and make Home Assistant log "does not generate unique IDs" on startup.
    if provider == PROVIDER_PLK:
        from homeassistant.helpers import entity_registry as er

        unique_id = f"{DOMAIN}_plk_api_usage"
        already_registered = er.async_get(hass).async_get_entity_id(
            "sensor", DOMAIN, unique_id
        )
        marker = f"_plk_usage_sensor_{provider}"
        if not already_registered and not hass.data[DOMAIN].get(marker):
            hass.data[DOMAIN][marker] = True
            entities.append(MzkzgPlkApiUsageSensor(hass, entry))

    async_add_entities(entities)


class MzkzgTransportSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing departures from a single stop."""

    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"departures", "last_update", "timetable"})

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
        attrs = {
            "stop_id": data.get("stop_id"),
            "stop_name": data.get("stop_name"),
            "provider": data.get("provider"),
            "last_update": data.get("last_update"),
            "departures": data.get("departures", []),
        }
        if data.get("timetable"):
            attrs["timetable"] = data["timetable"]
        return attrs


class MzkzgAggregatedSensor(SensorEntity):
    """Sensor that merges departures from multiple stops (węzeł przesiadkowy)."""

    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"departures", "last_update"})

    def __init__(self, coordinators: list, entry: ConfigEntry) -> None:
        self._coordinators = coordinators
        self._entry = entry
        provider = coordinators[0].provider if coordinators else entry.data.get(CONF_PROVIDER, "")
        provider_label = PROVIDER_LABELS.get(provider, provider)
        name = entry.data.get("name", "")
        self._provider = provider
        self._attr_unique_id = f"{DOMAIN}_{provider}_multi_{entry.entry_id}"
        self._attr_name = "Odjazdy"
        self._attr_icon = "mdi:bus-multiple"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{provider}_multi_{entry.entry_id}")},
            "name": name or "Węzeł",
            "manufacturer": provider_label,
            "model": provider,
        }

    @property
    def native_value(self) -> str | None:
        deps = self._merged_departures()
        if not deps:
            return None
        return deps[0].get("estimated_time")

    @property
    def extra_state_attributes(self) -> dict:
        deps = self._merged_departures()
        data = self._coordinators[0].data if self._coordinators else {}
        return {
            "stop_id": "|".join(c.stop_id for c in self._coordinators),
            "stop_name": data.get("stop_name", ""),
            "provider": data.get("provider", ""),
            "last_update": data.get("last_update", ""),
            "departures": deps,
        }

    def _merged_departures(self) -> list:
        all_deps = []
        seen = set()
        for c in self._coordinators:
            if c.data:
                for d in c.data.get("departures", []):
                    key = (d.get("route"), d.get("headsign", ""), (d.get("estimated_time") or "")[:16])
                    if key not in seen:
                        seen.add(key)
                        all_deps.append(d)
        all_deps.sort(key=lambda d: d.get("estimated_time") or "")
        return all_deps[:MAX_DEPARTURES]

    @property
    def available(self) -> bool:
        return any(c.last_update_success for c in self._coordinators)

    async def async_update(self) -> None:
        for c in self._coordinators:
            await c.async_refresh()

    async def async_added_to_hass(self) -> None:
        async_link_device_to_parent(
            self.hass,
            {(DOMAIN, f"{self._provider}_multi_{self._entry.entry_id}")},
            {(DOMAIN, self._provider)},
        )
        self.async_on_remove(
            self._entry.add_update_listener(self._async_update_from_coordinators)
        )

    async def _async_update_from_coordinators(self, hass, entry) -> None:
        self.async_write_ha_state()


class MzkzgPlkApiUsageSensor(SensorEntity, RestoreEntity):
    """Sensor tracking PLK API usage."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:api"
    _attr_native_unit_of_measurement = "requests"
    _attr_state_class = "total_increasing"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self._hass = hass
        # Kept exactly as before so the existing entity is adopted on upgrade.
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
