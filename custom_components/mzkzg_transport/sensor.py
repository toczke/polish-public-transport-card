"""Sensor platform for Polish Transport."""


from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PROVIDER,
    DEVICE_MANUFACTURER,
    DOMAIN,
    ENTITY_UNIQUE_PREFIX,
    MAX_DEPARTURES,
    PROVIDER_LABELS,
    PROVIDER_PLK,
    provider_entity_slug,
)
from .coordinator import PolishTransportCoordinator
from .device_utils import async_link_device_to_parent


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Polish Transport sensor from a config entry."""
    coordinators = hass.data[DOMAIN]["_coordinators"][entry.entry_id]
    provider = entry.data[CONF_PROVIDER]

    entities = []
    for coordinator in coordinators:
        entities.append(PolishTransportSensor(coordinator, entry))
    if len(coordinators) > 1:
        # One hub-level sensor with the merged timeline; per-stop sensors remain
        # available for dashboards that need a single stop.
        entities.append(PolishAggregatedSensor(coordinators, entry))

    # Add the shared PLK API usage sensor once per Home Assistant instance. The usage
    # counters are global, so a sensor per PLK entry would only duplicate the same
    # unique id and make Home Assistant log "does not generate unique IDs" on startup.
    if provider == PROVIDER_PLK:
        marker = f"_plk_usage_sensor_{provider}"
        if not hass.data[DOMAIN].get(marker):
            hass.data[DOMAIN][marker] = entry.entry_id
            entities.append(PlkApiUsageSensor(hass, entry))

    async_add_entities(entities)


class PolishTransportSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing departures from a single stop."""

    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"departures", "last_update", "timetable", "alerts", "alerts_city", "offline", "offline_saved_at", "offline_missing"})

    def __init__(self, coordinator: PolishTransportCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        provider = coordinator.provider
        stop = coordinator.stop_id
        custom_name = coordinator.stop_name
        stop_label = custom_name or stop
        self._attr_unique_id = f"{ENTITY_UNIQUE_PREFIX}_{provider}_{stop}"
        self._attr_name = "Odjazdy"
        self._attr_icon = "mdi:bus-multiple"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{provider}_{stop}")},
            "name": stop_label,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": provider,
        }

    async def async_added_to_hass(self) -> None:
        """Link this stop device to its operator device."""
        await super().async_added_to_hass()
        async_link_device_to_parent(
            self.hass,
            {(DOMAIN, f"{self.coordinator.provider}_{self.coordinator.stop_id}")},
            {(DOMAIN, self.coordinator.provider)},
            self._entry.entry_id,
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
        }
        if data.get("offline"):
            attrs["offline"] = True
            attrs["offline_saved_at"] = data.get("offline_saved_at")
            if data.get("offline_missing"):
                attrs["offline_missing"] = True
        if data.get("resolved_stop_id"):
            attrs["resolved_stop_id"] = data["resolved_stop_id"]
        if data.get("timetable"):
            attrs["timetable"] = data["timetable"]
        if data.get("alerts"):
            attrs["alerts"] = data["alerts"]
        if data.get("alerts_city"):
            attrs["alerts_city"] = data["alerts_city"]
        if "walking_distance_m" in data:
            attrs["walking_distance_m"] = data["walking_distance_m"]
            attrs["walking_time_min"] = data["walking_time_min"]
            if hasattr(self.coordinator, "stop_lat") and self.coordinator.stop_lat is not None:
                attrs["latitude"] = self.coordinator.stop_lat
                attrs["longitude"] = self.coordinator.stop_lon

        attrs["departures"] = data.get("departures", [])
        return attrs


class PolishAggregatedSensor(SensorEntity):
    """Sensor that merges departures from multiple stops (węzeł przesiadkowy)."""

    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"departures", "last_update", "alerts", "alerts_city", "offline", "offline_saved_at", "offline_missing"})

    def __init__(self, coordinators: list, entry: ConfigEntry) -> None:
        self._coordinators = coordinators
        self._entry = entry
        provider = coordinators[0].provider if coordinators else entry.data.get(CONF_PROVIDER, "")
        provider_label = PROVIDER_LABELS.get(provider, provider)
        self._provider = provider
        self._attr_unique_id = f"{ENTITY_UNIQUE_PREFIX}_{provider}_hub"
        self._attr_name = "Odjazdy"
        self._attr_suggested_object_id = f"{provider_entity_slug(provider)}_odjazdy"
        self._attr_icon = "mdi:bus-multiple"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, provider)},
            "name": provider_label,
            "manufacturer": DEVICE_MANUFACTURER,
            "model": provider,
        }
        self._merged_cache = None

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
        attrs = {
            "stop_id": "|".join(c.stop_id for c in self._coordinators),
            "stop_name": data.get("stop_name", ""),
            "provider": data.get("provider", ""),
            "last_update": data.get("last_update", ""),
        }
        
        # Calculate min walking distance across all aggregated stops
        min_dist = min((c.data.get("walking_distance_m") for c in self._coordinators if c.data and "walking_distance_m" in c.data), default=None)
        if min_dist is not None:
            attrs["walking_distance_m"] = min_dist
            attrs["walking_time_min"] = min((c.data.get("walking_time_min") for c in self._coordinators if c.data and "walking_time_min" in c.data), default=0)

        alerts = []
        seen_alerts = set()
        for coordinator in self._coordinators:
            for alert in (coordinator.data or {}).get("alerts", []):
                alert_id = alert.get("id") or f"{alert.get('title')}|{alert.get('content')}"
                if alert_id not in seen_alerts:
                    seen_alerts.add(alert_id)
                    alerts.append(alert)
        if alerts:
            attrs["alerts"] = alerts

        alerts_city = []
        seen_city = set()
        for coordinator in self._coordinators:
            for alert in (coordinator.data or {}).get("alerts_city", []):
                alert_id = alert.get("id") or f"{alert.get('title')}|{alert.get('content')}"
                if alert_id not in seen_city:
                    seen_city.add(alert_id)
                    alerts_city.append(alert)
        if alerts_city:
            attrs["alerts_city"] = alerts_city

        attrs["departures"] = deps
        return attrs

    def _merged_departures(self) -> list:
        if self._merged_cache is not None:
            return self._merged_cache
        all_deps = []
        for c in self._coordinators:
            if c.data:
                all_deps.extend(c.data.get("departures", []))
        all_deps = PolishTransportCoordinator._deduplicate_prefer_rt(all_deps)
        all_deps.sort(key=lambda d: d.get("estimated_time") or "")
        self._merged_cache = all_deps[:MAX_DEPARTURES]
        return self._merged_cache

    @property
    def available(self) -> bool:
        return any(c.last_update_success for c in self._coordinators)

    async def async_update(self) -> None:
        for c in self._coordinators:
            await c.async_refresh()
        self._merged_cache = None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._entry.add_update_listener(self._async_update_from_coordinators)
        )

    async def _async_update_from_coordinators(self, hass, entry) -> None:
        self._merged_cache = None
        self.async_write_ha_state()


class PlkApiUsageSensor(SensorEntity, RestoreEntity):
    """Sensor tracking PLK API usage."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:api"
    _attr_native_unit_of_measurement = "requests"
    _attr_state_class = "total_increasing"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self._hass = hass
        # Kept exactly as before so the existing entity is adopted on upgrade.
        self._attr_unique_id = f"{ENTITY_UNIQUE_PREFIX}_plk_api_usage"
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
